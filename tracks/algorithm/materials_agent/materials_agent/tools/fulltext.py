"""Full-text evidence attachment (MinerU / local cache / OA PDF text)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from materials_agent.config import AppConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.tools.fs_safe import safe_fs_name
from materials_agent.tools.fulltext_labels import canonical_fulltext_source
from materials_agent.tools.oa_download import download_oa_pdf, enrich_from_unpaywall
from materials_agent.tools.paper_titles import backfill_paper_title
from materials_agent.tools.parsers import parse_with_grobid, parse_with_mineru


def _cache_dir(cfg: AppConfig) -> Path:
    root = Path(__file__).resolve().parents[2]
    rel = Path(cfg.retrieval.fulltext_cache_dir)
    return rel if rel.is_absolute() else root / rel


def _project_path(path: str, cfg: AppConfig) -> Path:
    root = Path(__file__).resolve().parents[2]
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _paper_fs_id(paper: Paper) -> str:
    return safe_fs_name(paper.id)


def _load_cached_text(paper: Paper, cache: Path) -> str | None:
    fs_id = _paper_fs_id(paper)
    for name in (f"{fs_id}.txt", f"{fs_id}.md", f"{(paper.doi or '').replace('/', '_')}.txt"):
        if not name or name in {".txt", ".md"}:
            continue
        p = cache / name
        if p.is_file():
            text = p.read_text(encoding="utf-8").strip()
            if len(text) >= 80:
                return text
    return None


def _reuse_parsed_artifacts(
    paper: Paper, pdf_path: Path, parse_dir: Path, pdf_hash: str
) -> tuple[str, str, dict[str, str]] | None:
    """Reuse MinerU/GROBID outputs when the PDF hash is unchanged."""
    marker = parse_dir / ".pdf_hash"
    if not marker.is_file() or marker.read_text(encoding="utf-8").strip() != pdf_hash:
        return None
    outputs: dict[str, str] = {}
    mineru_dir = parse_dir / "mineru"
    grobid_tei = parse_dir / "grobid" / "grobid.tei.xml"
    text = ""
    source = "oa_pdf"
    if mineru_dir.is_dir():
        md_choices = sorted(mineru_dir.rglob("*.md")) + sorted(mineru_dir.rglob("*.txt"))
        md = next((p for p in md_choices if p.stat().st_size > 80), None)
        if md:
            text = md.read_text(encoding="utf-8", errors="ignore").strip()
            outputs["markdown"] = str(md)
            source = "mineru"
    if grobid_tei.is_file():
        outputs["tei"] = str(grobid_tei)
        if not text:
            # Prefer TEI plaintext only when MinerU cache is missing.
            raw = grobid_tei.read_text(encoding="utf-8", errors="ignore")
            # Cheap tag strip for reuse path; full parse still runs when marker misses.
            plain = re.sub(r"<[^>]+>", " ", raw)
            plain = re.sub(r"\s+", " ", plain).strip()
            if len(plain) >= 80:
                text = plain
                source = "grobid"
    if text:
        paper.pdf_path = str(pdf_path)
        paper.pdf_hash = pdf_hash
        return text, canonical_fulltext_source(source), outputs
    return None


def _parse_pdf(
    paper: Paper, pdf_path: Path, cfg: AppConfig, audit: list[AuditEvent]
) -> tuple[str, str, dict[str, str], list[str]]:
    """Run optional parsers; prefer MinerU text and retain GROBID TEI metadata."""
    parse_dir = _project_path(cfg.fulltext.parse_cache_dir, cfg) / _paper_fs_id(paper)
    pdf_hash = paper.pdf_hash or hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    paper.pdf_hash = pdf_hash
    reused = _reuse_parsed_artifacts(paper, pdf_path, parse_dir, pdf_hash)
    if reused:
        text, source, outputs = reused
        audit.append(
            AuditEvent(
                step="parse_fulltext",
                tool="parse_cache",
                input_summary=paper.id,
                output_summary=f"reused source={source}",
                meta={"outputs": outputs, "pdf_hash": pdf_hash},
            )
        )
        return text, source, outputs, []

    outputs: dict[str, str] = {}
    errors: list[str] = []
    primary = cfg.fulltext.parsers.primary.lower()
    secondary = cfg.fulltext.parsers.secondary.lower()
    primary_result = None
    grobid = None

    if primary == "mineru":
        primary_result = parse_with_mineru(pdf_path, parse_dir / "mineru", cfg.fulltext.parsers)
        outputs.update(primary_result.output_paths)
        if primary_result.error:
            errors.append(primary_result.error)
    elif primary == "grobid":
        primary_result = parse_with_grobid(pdf_path, parse_dir / "grobid", cfg.fulltext.parsers)
        outputs.update(primary_result.output_paths)
        if primary_result.error:
            errors.append(primary_result.error)
        grobid = primary_result

    if secondary == "grobid" and primary != "grobid":
        grobid = parse_with_grobid(pdf_path, parse_dir / "grobid", cfg.fulltext.parsers)
        outputs.update(grobid.output_paths)
        if grobid.error:
            errors.append(grobid.error)
    elif secondary == "mineru" and primary != "mineru":
        mineru = parse_with_mineru(pdf_path, parse_dir / "mineru", cfg.fulltext.parsers)
        outputs.update(mineru.output_paths)
        if mineru.error:
            errors.append(mineru.error)
        if not primary_result or not primary_result.text:
            primary_result = mineru

    text = ""
    source = "oa_pdf"
    if primary_result and primary_result.text and primary_result.parser == "mineru":
        text = primary_result.text
        source = "mineru"
    elif primary_result and primary_result.text and primary_result.parser == "grobid":
        text = primary_result.text
        source = "grobid"
    elif grobid and grobid.text:
        text = grobid.text
        source = "grobid"
    elif primary_result and primary_result.text:
        text = primary_result.text
        source = primary_result.parser or "oa_pdf"
    source = canonical_fulltext_source(source)
    if text:
        parse_dir.mkdir(parents=True, exist_ok=True)
        (parse_dir / ".pdf_hash").write_text(pdf_hash, encoding="utf-8")
    if errors:
        audit.append(
            AuditEvent(
                step="parse_fulltext",
                tool="pdf_parsers",
                input_summary=paper.id,
                output_summary=f"source={source}; errors={len(errors)}",
                meta={
                    "errors": errors,
                    "outputs": outputs,
                    "primary": primary,
                    "secondary": secondary,
                },
            )
        )
    return text, source, outputs, errors


def attach_fulltext(
    papers: list[Paper],
    cfg: AppConfig,
    audit: list[AuditEvent],
) -> list[Paper]:
    """
    Prefer preloaded/cache text. Production profile enriches OA metadata, downloads
    legal OA PDFs, and runs configured MinerU/GROBID parsers.
    """
    if not cfg.retrieval.fetch_fulltext:
        audit.append(
            AuditEvent(
                step="fulltext",
                tool="skip",
                input_summary=f"{len(papers)} papers",
                output_summary="fetch_fulltext=false",
            )
        )
        return papers

    cache = _cache_dir(cfg)
    cache.mkdir(parents=True, exist_ok=True)
    pdf_dir = _project_path(cfg.fulltext.pdf_cache_dir, cfg)
    n_local = n_cache = n_mineru = n_grobid = n_oa_pdf = n_none = 0

    allow_text_cache = cfg.fulltext.allow_text_cache
    for idx, paper in enumerate(papers, start=1):
        print(f"[fulltext] {idx}/{len(papers)} {paper.id}", flush=True)
        # Sci-Base rows already carry MinerU-parsed content_list text — keep it even
        # when production disables generic text-cache reuse.
        if (
            (paper.source or "").lower() == "scibase"
            and paper.full_text
            and len(paper.full_text.strip()) >= 80
        ):
            paper.fulltext_source = paper.fulltext_source or "scibase_content_list"
            n_local += 1
            (cache / f"{_paper_fs_id(paper)}.txt").write_text(paper.full_text, encoding="utf-8")
            continue

        if allow_text_cache and paper.full_text and len(paper.full_text.strip()) >= 80:
            paper.fulltext_source = paper.fulltext_source or "local_cache"
            n_local += 1
            # persist for reuse
            (cache / f"{_paper_fs_id(paper)}.txt").write_text(paper.full_text, encoding="utf-8")
            continue

        if allow_text_cache:
            cached = _load_cached_text(paper, cache)
            if cached:
                paper.full_text = cached
                paper.fulltext_source = "local_cache"
                n_cache += 1
                continue

        pdf = pdf_dir / f"{_paper_fs_id(paper)}.pdf"
        if not pdf.is_file() and cfg.fulltext.download_oa:
            enrich_from_unpaywall(paper, cfg, audit)
            pdf = download_oa_pdf(paper, cfg, pdf_dir, audit) or pdf
        if pdf.is_file():
            if not paper.pdf_hash:
                data = pdf.read_bytes()
                paper.pdf_hash = hashlib.sha256(data).hexdigest()
            paper.pdf_path = str(pdf)
            text, source, outputs, errors = _parse_pdf(paper, pdf, cfg, audit)
            if text:
                paper.full_text = text
                paper.fulltext_source = canonical_fulltext_source(source)
                tei = outputs.get("tei")
                backfill_paper_title(paper, Path(tei) if tei else None)
                (cache / f"{_paper_fs_id(paper)}.txt").write_text(text, encoding="utf-8")
                paper.parse_manifest_id = f"{paper.id}:{paper.pdf_hash[:12]}"
                paper.raw["parse_manifest"] = {
                    "manifest_id": paper.parse_manifest_id,
                    "pdf_path": str(pdf),
                    "pdf_hash": paper.pdf_hash,
                    "parser_outputs": outputs,
                    "errors": errors,
                }
                if paper.fulltext_source == "mineru":
                    n_mineru += 1
                else:
                    n_grobid += 1
                continue
            n_oa_pdf += 1

        paper.fulltext_source = "none"
        n_none += 1

    audit.append(
        AuditEvent(
            step="fulltext",
            tool="fulltext_attach",
            input_summary=f"{len(papers)} papers",
            output_summary=(
                f"with_fulltext={n_local + n_cache + n_mineru + n_grobid}; "
                f"local={n_local} cache={n_cache} mineru={n_mineru} grobid={n_grobid} "
                f"oa_pdf_unparsed={n_oa_pdf} none={n_none}"
            ),
            meta={
                "cache_dir": str(cache),
                "pdf_dir": str(pdf_dir),
                "primary_parser": cfg.fulltext.parsers.primary,
                "secondary_parser": cfg.fulltext.parsers.secondary,
            },
        )
    )
    return papers


def paper_source_text(paper: Paper) -> tuple[str, str]:
    """Return (text, evidence_location) preferring fulltext over abstract."""
    if paper.full_text and len(paper.full_text.strip()) >= 80:
        return paper.full_text.strip(), "fulltext"
    if paper.abstract:
        return f"{paper.title}. {paper.abstract}", "abstract"
    return paper.title or "", "title"


def dump_fulltext_index(papers: list[Paper], output_dir: Path) -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "paper_id": p.id,
            "fulltext_source": p.fulltext_source,
            "fulltext_chars": len(p.full_text or ""),
            "has_fulltext": bool(p.full_text and len(p.full_text) >= 80),
            "source_url": p.fulltext_url or p.oa_url,
            "pdf_path": p.pdf_path,
            "pdf_hash": p.pdf_hash,
            "oa_status": p.oa_status,
            "license": p.oa_license,
            "parse_manifest": p.raw.get("parse_manifest", {}),
        }
        for p in papers
    ]
    path = out / "fulltext_index.json"
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
