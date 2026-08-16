"""Archive retrieved literature under data/<topic>_<timestamp>/."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from materials_agent.config import AppConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.tools.fs_safe import safe_fs_name
from materials_agent.tools.oa_download import download_oa_pdf, enrich_from_unpaywall


def slugify_topic(topic: str, *, max_len: int = 60) -> str:
    """Build a filesystem-safe folder name from the search topic."""
    text = (topic or "").strip()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff\-]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("._-")
    if not text:
        text = "topic"
    return text[:max_len].rstrip("_")


def make_run_dir(topic: str, root: Path, *, when: datetime | None = None) -> Path:
    """Create data/<topic>_<YYYYMMDD_HHMMSS>/ for one search run."""
    stamp = (when or datetime.now()).strftime("%Y%m%d_%H%M%S")
    name = f"{slugify_topic(topic)}_{stamp}"
    path = root / name
    path.mkdir(parents=True, exist_ok=False)
    (path / "pdfs").mkdir(parents=True, exist_ok=True)
    (path / "abstracts").mkdir(parents=True, exist_ok=True)
    return path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_root(cfg: AppConfig) -> Path:
    raw = getattr(cfg.retrieval, "archive_root", None) or "data"
    root = Path(raw)
    return root if root.is_absolute() else _project_root() / root


def archive_retrieved_literature(
    papers: list[Paper],
    cfg: AppConfig,
    audit: list[AuditEvent],
    *,
    queries: list[str] | None = None,
    run_dir: Path | None = None,
) -> Path | None:
    """
    Save retrieved papers under data/<topic>_<time>/.

    Always writes metadata. Downloads or copies OA PDFs into pdfs/ when possible.
    Abstracts are written to abstracts/ for papers without PDF.
    """
    if not getattr(cfg.retrieval, "archive_literature", True):
        return None

    root = _resolve_root(cfg)
    root.mkdir(parents=True, exist_ok=True)
    out = run_dir or make_run_dir(cfg.topic, root)
    pdf_dir = out / "pdfs"
    abs_dir = out / "abstracts"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    abs_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    n_pdf = 0
    n_abs = 0
    n_fail = 0

    shared_pdf_cache = _project_root() / cfg.fulltext.pdf_cache_dir
    if not shared_pdf_cache.is_absolute():
        shared_pdf_cache = _project_root() / shared_pdf_cache

    for paper in papers:
        record = {
            "id": paper.id,
            "title": paper.title,
            "year": paper.year,
            "doi": paper.doi,
            "venue": paper.venue,
            "cited_by": paper.cited_by,
            "url": paper.url,
            "oa_url": paper.oa_url,
            "fulltext_url": paper.fulltext_url,
            "oa_status": paper.oa_status,
            "fulltext_source": paper.fulltext_source,
            "pdf_saved": None,
            "abstract_saved": None,
        }

        dest_pdf = pdf_dir / f"{safe_fs_name(paper.id)}.pdf"
        copied = False

        # Prefer already downloaded/parsed PDF path.
        sources: list[Path] = []
        if paper.pdf_path:
            sources.append(Path(paper.pdf_path))
        sources.append(shared_pdf_cache / f"{safe_fs_name(paper.id)}.pdf")

        for src in sources:
            if src.is_file() and src.stat().st_size > 0:
                if src.resolve() != dest_pdf.resolve():
                    shutil.copy2(src, dest_pdf)
                copied = True
                break

        if not copied:
            # Archive downloads are independent of parse-time download_oa:
            # always try legal OA PDF into this run folder when a URL exists.
            enrich_from_unpaywall(paper, cfg, audit)
            got = download_oa_pdf(paper, cfg, pdf_dir, audit)
            if got and got.is_file():
                copied = True
                if not paper.pdf_path:
                    paper.pdf_path = str(got)
                if not paper.pdf_hash:
                    paper.pdf_hash = hashlib.sha256(got.read_bytes()).hexdigest()

        if copied and dest_pdf.is_file():
            record["pdf_saved"] = str(dest_pdf.relative_to(out)).replace("\\", "/")
            record["pdf_sha256"] = hashlib.sha256(dest_pdf.read_bytes()).hexdigest()
            n_pdf += 1
        else:
            n_fail += 1

        abstract = (paper.abstract or "").strip()
        if abstract:
            abs_path = abs_dir / f"{safe_fs_name(paper.id)}.txt"
            header = (
                f"Title: {paper.title}\n"
                f"Year: {paper.year}\n"
                f"DOI: {paper.doi or ''}\n"
                f"Venue: {paper.venue or ''}\n\n"
            )
            abs_path.write_text(header + abstract, encoding="utf-8")
            record["abstract_saved"] = str(abs_path.relative_to(out)).replace("\\", "/")
            n_abs += 1

        rows.append(record)

    manifest = {
        "topic": cfg.topic,
        "subfield": cfg.subfield,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "archive_dir": str(out),
        "queries": queries or [],
        "paper_count": len(papers),
        "pdf_saved": n_pdf,
        "abstract_saved": n_abs,
        "pdf_missing": n_fail,
        "backend": cfg.retrieval.backend,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out / "papers.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# Literature archive: {cfg.topic}",
        "",
        f"- Created: `{manifest['created_at']}`",
        f"- Backend: `{cfg.retrieval.backend}`",
        f"- Papers: **{len(papers)}** · PDFs saved: **{n_pdf}** · abstracts: **{n_abs}**",
        "",
        "## Queries",
        "",
    ]
    for q in queries or [cfg.topic]:
        lines.append(f"- {q}")
    lines += ["", "## Papers", ""]
    for row in rows:
        pdf_flag = "PDF" if row.get("pdf_saved") else "no-PDF"
        lines.append(
            f"- `{row['id']}` ({row.get('year')}) [{pdf_flag}] "
            f"{row.get('title') or ''} · DOI: {row.get('doi') or '—'}"
        )
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    audit.append(
        AuditEvent(
            step="archive_literature",
            tool="literature_archive",
            input_summary=cfg.topic,
            output_summary=f"dir={out.name}; pdfs={n_pdf}/{len(papers)}; abstracts={n_abs}",
            meta=manifest,
        )
    )
    return out
