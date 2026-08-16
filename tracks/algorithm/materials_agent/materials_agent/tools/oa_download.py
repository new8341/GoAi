"""Legal open-access PDF resolution and cached download helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from materials_agent.config import AppConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.tools.fs_safe import safe_fs_name


def _safe_doi(doi: str) -> str:
    return doi.replace("/", "%2F").strip()


_OSTI_BIBLIO = re.compile(
    r"^https?://(?:www\.)?osti\.gov/biblio/(\d+)", re.IGNORECASE
)
_ARXIV_ABS = re.compile(
    r"^https?://(?:www\.)?arxiv\.org/abs/([0-9]+\.[0-9]+)(v\d+)?", re.IGNORECASE
)
_PMC_ARTICLE = re.compile(
    r"^https?://(?:www\.)?(?:ncbi\.nlm\.nih\.gov/pmc/articles|europepmc\.org/articles)/"
    r"(?:PMC)?(\d+)",
    re.IGNORECASE,
)


def normalize_oa_url(url: str) -> str | None:
    """Rewrite known legal OA landing URLs into direct PDF endpoints when possible."""
    raw = (url or "").strip()
    if not raw:
        return None
    osti = _OSTI_BIBLIO.match(raw)
    if osti:
        return f"https://www.osti.gov/servlets/purl/{osti.group(1)}"
    arxiv = _ARXIV_ABS.match(raw)
    if arxiv:
        return f"https://arxiv.org/pdf/{arxiv.group(1)}"
    pmc = _PMC_ARTICLE.match(raw)
    if pmc:
        return f"https://europepmc.org/articles/pmc{pmc.group(1)}?pdf=render"
    if raw.lower().endswith(".pdf") or "/pdf" in raw.lower() or "servlets/purl" in raw.lower():
        return raw
    return raw


def url_rejection_reason(url: str) -> str | None:
    """Return a skip reason for URLs that are not usable OA PDF endpoints."""
    lower = url.lower()
    host = urlparse(url).netloc.lower()
    if "/science/article/abs/" in lower:
        return "sciencedirect_abstract_landing"
    if "doaj.org/article/" in lower:
        return "doaj_landing_not_pdf"
    if host in {"doi.org", "dx.doi.org"}:
        return "doi_resolver_landing"
    if "sciencedirect.com" in host and "/pdf" not in lower:
        return "sciencedirect_non_pdf"
    return None


def _candidate_urls(paper: Paper) -> list[str]:
    """Collect unique normalized OA URL candidates, preferring PDF-like links."""
    raw_candidates: list[str] = []
    unpaywall = paper.raw.get("unpaywall") or {}
    for key in ("url_for_pdf", "url_for_landing_page"):
        value = unpaywall.get(key)
        if isinstance(value, str) and value.strip():
            raw_candidates.append(value.strip())
    for value in unpaywall.get("pdf_candidates") or []:
        if isinstance(value, str) and value.strip():
            raw_candidates.append(value.strip())
    for value in (paper.fulltext_url, paper.oa_url):
        if value and value.strip():
            raw_candidates.append(value.strip())

    ordered: list[str] = []
    seen: set[str] = set()
    for raw in raw_candidates:
        normalized = normalize_oa_url(raw)
        if not normalized:
            continue
        if normalized in seen:
            continue
        reason = url_rejection_reason(normalized)
        # Keep rejected URLs out of the attempt list entirely.
        if reason:
            continue
        seen.add(normalized)
        ordered.append(normalized)

    def _pdf_rank(item: str) -> tuple[int, int]:
        lower = item.lower()
        score = 0
        if lower.endswith(".pdf") or "pdf=render" in lower or "/pdf/" in lower:
            score -= 10
        if "europepmc.org" in lower or "arxiv.org/pdf" in lower or "osti.gov/servlets" in lower:
            score -= 5
        if "nature.com" in lower and lower.endswith(".pdf"):
            score -= 4
        return (score, len(item))

    return sorted(ordered, key=_pdf_rank)


def enrich_from_unpaywall(
    paper: Paper, cfg: AppConfig, audit: list[AuditEvent]
) -> None:
    """Attach legal OA metadata from Unpaywall without downloading content."""
    settings = cfg.fulltext.unpaywall
    if not settings.enabled or not paper.doi or not settings.email.strip():
        return

    url = f"{settings.api_base.rstrip('/')}/{_safe_doi(paper.doi)}"
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, params={"email": settings.email})
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        audit.append(
            AuditEvent(
                step="enrich_unpaywall",
                tool="unpaywall",
                input_summary=paper.doi,
                output_summary=f"failed: {exc}",
            )
        )
        return

    best = payload.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf")
    landing_url = best.get("url_for_landing_page")
    pdf_candidates: list[str] = []
    for location in payload.get("oa_locations") or []:
        if not isinstance(location, dict):
            continue
        for key in ("url_for_pdf", "url"):
            value = location.get(key)
            if isinstance(value, str) and value.strip():
                pdf_candidates.append(value.strip())
        landing = location.get("url_for_landing_page")
        if isinstance(landing, str) and landing.strip():
            pdf_candidates.append(landing.strip())

    paper.oa_status = payload.get("oa_status") or paper.oa_status
    paper.oa_license = best.get("license") or paper.oa_license
    paper.oa_version = best.get("version") or paper.oa_version
    preferred = normalize_oa_url(pdf_url or "") or pdf_url
    if preferred and not url_rejection_reason(preferred):
        paper.fulltext_url = preferred
    elif paper.fulltext_url:
        paper.fulltext_url = normalize_oa_url(paper.fulltext_url) or paper.fulltext_url
    else:
        # Prefer a normalized repository landing (e.g. PMC → Europe PMC PDF) over DOI.
        for candidate in pdf_candidates:
            normalized = normalize_oa_url(candidate)
            if normalized and not url_rejection_reason(normalized):
                paper.fulltext_url = normalized
                break
        if not paper.fulltext_url:
            paper.fulltext_url = landing_url or paper.oa_url

    paper.raw["unpaywall"] = {
        "is_oa": payload.get("is_oa"),
        "oa_status": paper.oa_status,
        "url_for_pdf": pdf_url,
        "url_for_landing_page": landing_url,
        "license": paper.oa_license,
        "version": paper.oa_version,
        "pdf_candidates": list(dict.fromkeys(pdf_candidates)),
    }
    audit.append(
        AuditEvent(
            step="enrich_unpaywall",
            tool="unpaywall",
            input_summary=paper.doi,
            output_summary=(
                "pdf URL found"
                if pdf_url or paper.fulltext_url
                else "no direct PDF URL"
            ),
            meta={
                "oa_status": paper.oa_status,
                "license": paper.oa_license,
                "candidates": len(pdf_candidates),
            },
        )
    )


def resolve_oa_url(paper: Paper) -> str | None:
    """Choose a known legal OA fulltext URL; no publisher scraping occurs."""
    candidates = _candidate_urls(paper)
    return candidates[0] if candidates else None


def download_oa_pdf(
    paper: Paper, cfg: AppConfig, pdf_dir: Path, audit: list[AuditEvent]
) -> Path | None:
    """Download an OA PDF under a size limit and record a content hash."""
    candidates = _candidate_urls(paper)
    if not candidates:
        rejected = []
        for raw in (paper.fulltext_url, paper.oa_url):
            if raw:
                reason = url_rejection_reason(raw) or "no_normalized_pdf_candidate"
                rejected.append(f"{reason}:{raw[:120]}")
        audit.append(
            AuditEvent(
                step="download_pdf",
                tool="oa_download",
                input_summary=paper.id,
                output_summary="skipped: no usable OA PDF candidate",
                meta={"rejected": rejected[:5]},
            )
        )
        return None

    pdf_dir.mkdir(parents=True, exist_ok=True)
    destination = pdf_dir / f"{safe_fs_name(paper.id)}.pdf"
    if destination.is_file() and destination.stat().st_size > 0:
        data = destination.read_bytes()
        paper.pdf_path = str(destination)
        paper.pdf_hash = hashlib.sha256(data).hexdigest()
        paper.fulltext_url = paper.fulltext_url or candidates[0]
        paper.fulltext_source = "oa_pdf"
        return destination

    max_bytes = cfg.fulltext.max_pdf_mb * 1024 * 1024
    headers = {
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "User-Agent": (
            f"materials-agent/0.1 (research; mailto:{cfg.retrieval.mailto or 'team@example.com'})"
        ),
    }
    # Windows can hang on half-closed sockets; keep connect/read budgets tight.
    timeout = httpx.Timeout(45.0, connect=10.0, read=45.0, write=30.0, pool=10.0)

    last_error = ""
    for source_url in candidates[:3]:
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                with client.stream("GET", source_url, headers=headers) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > max_bytes:
                            raise ValueError(
                                f"PDF exceeds {cfg.fulltext.max_pdf_mb} MB limit"
                            )
                        chunks.append(chunk)
        except (httpx.HTTPError, OSError, ValueError) as exc:
            last_error = str(exc)
            audit.append(
                AuditEvent(
                    step="download_pdf",
                    tool="oa_download",
                    input_summary=source_url[:300],
                    output_summary=f"failed: {exc}",
                    meta={"reason_code": "http_or_io_error"},
                )
            )
            continue

        data = b"".join(chunks)
        if not data.startswith(b"%PDF"):
            audit.append(
                AuditEvent(
                    step="download_pdf",
                    tool="oa_download",
                    input_summary=source_url[:300],
                    output_summary=f"rejected non-PDF content_type={content_type}",
                    meta={"reason_code": "non_pdf_body"},
                )
            )
            last_error = f"non-PDF content_type={content_type}"
            continue

        destination.write_bytes(data)
        paper.pdf_path = str(destination)
        paper.pdf_hash = hashlib.sha256(data).hexdigest()
        paper.fulltext_url = source_url
        paper.fulltext_source = "oa_pdf"
        paper.raw["downloaded_at"] = datetime.now(timezone.utc).isoformat()
        audit.append(
            AuditEvent(
                step="download_pdf",
                tool="oa_download",
                input_summary=source_url[:300],
                output_summary=f"saved {destination.name} ({len(data)} bytes)",
                meta={
                    "sha256": paper.pdf_hash,
                    "content_type": content_type,
                    "reason_code": "ok",
                    "candidates_tried": candidates.index(source_url) + 1,
                },
            )
        )
        return destination

    audit.append(
        AuditEvent(
            step="download_pdf",
            tool="oa_download",
            input_summary=paper.id,
            output_summary=f"exhausted candidates: {last_error or 'unknown'}",
            meta={"candidates": candidates[:5]},
        )
    )
    return None
