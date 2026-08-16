"""Sciverse (绌瑰畤) HTTP client for literature retrieval."""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from materials_agent.config import AppConfig
from materials_agent.models import Paper
from materials_agent.tools.fs_safe import safe_fs_name


def resolve_sciverse_token(cfg: AppConfig) -> str:
    """Prefer config, then SCIVERSE_API_TOKEN / SCIVERSE_API_KEY env vars."""
    for value in (
        getattr(cfg.retrieval, "sciverse_api_token", "") or "",
        os.environ.get("SCIVERSE_API_TOKEN", ""),
        os.environ.get("SCIVERSE_API_KEY", ""),
    ):
        if value and value.strip():
            return value.strip()
    return ""


def resolve_sciverse_base(cfg: AppConfig) -> str:
    raw = (
        getattr(cfg.retrieval, "sciverse_base_url", "") or ""
    ).strip() or os.environ.get("SCIVERSE_BASE_URL", "").strip()
    return (raw or "https://api.sciverse.space").rstrip("/")


def _paper_from_meta(item: dict[str, Any], *, source: str = "sciverse") -> Paper | None:
    title = (item.get("title") or "").strip()
    if not title:
        return None
    unique_id = str(item.get("unique_id") or item.get("doi") or title)[:120]
    authors_raw = item.get("author") or []
    authors: list[str] = []
    if isinstance(authors_raw, list):
        for a in authors_raw:
            if isinstance(a, dict) and a.get("name"):
                authors.append(str(a["name"]))
            elif isinstance(a, str) and a.strip():
                authors.append(a.strip())
    doi = item.get("doi")
    year = item.get("publication_published_year")
    try:
        year_i = int(year) if year is not None else None
    except (TypeError, ValueError):
        year_i = None
    concepts = [str(x) for x in (item.get("subjects") or item.get("keywords") or [])[:8]]
    doc_id = item.get("doc_id")
    return Paper(
        id=safe_fs_name(f"SV-{unique_id}", max_len=80),
        title=title,
        year=year_i,
        doi=str(doi) if doi else None,
        abstract=(item.get("abstract") or None),
        authors=authors,
        venue=str(item.get("publication_venue_name_unified") or "") or None,
        concepts=concepts,
        source=source,
        raw={
            "sciverse_unique_id": unique_id,
            "sciverse_doc_id": doc_id,
            "sciverse_is_content_accessible": item.get("is_content_accessible"),
            "sciverse": item,
        },
    )


def _paper_from_chunk(hit: dict[str, Any]) -> Paper | None:
    title = (hit.get("title") or "").strip()
    if not title:
        return None
    doc_id = str(hit.get("doc_id") or hit.get("chunk_id") or title)[:120]
    abstract = hit.get("abstract") or hit.get("chunk") or ""
    return Paper(
        id=safe_fs_name(f"SVC-{doc_id}", max_len=80),
        title=title,
        abstract=str(abstract)[:4000] if abstract else None,
        source="sciverse",
        raw={
            "sciverse_doc_id": hit.get("doc_id"),
            "sciverse_chunk_id": hit.get("chunk_id"),
            "sciverse_offset": hit.get("offset"),
            "sciverse_score": hit.get("score"),
            "sciverse_hit": hit,
        },
    )


class SciverseClient:
    """Minimal Sciverse Agent Tools HTTP client (Bearer token)."""

    def __init__(self, token: str, base_url: str = "https://api.sciverse.space"):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "materials-agent/0.1 (GOAI materials literature agent)",
        }

    def meta_search(
        self,
        query: str,
        *,
        year_from: int | None = None,
        page_size: int = 20,
    ) -> list[Paper]:
        # Live API currently accepts a minimal body (query/page/page_size).
        # Extra OpenAPI-ish fields (year_from, sort_by_year, collection) return 400.
        payload: dict[str, Any] = {
            "query": query,
            "page": 1,
            "page_size": min(max(page_size, 1), 50),
        }

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        )
        def _post() -> dict:
            with httpx.Client(timeout=60.0, headers=self._headers()) as client:
                response = client.post(f"{self.base_url}/meta-search", json=payload)
                response.raise_for_status()
                return response.json()

        data = _post()
        papers: list[Paper] = []
        for item in data.get("results") or []:
            if not isinstance(item, dict):
                continue
            paper = _paper_from_meta(item)
            if not paper:
                continue
            if year_from and paper.year is not None and paper.year < int(year_from):
                continue
            papers.append(paper)
        return papers

    def semantic_search(self, query: str, *, top_k: int = 10) -> list[Paper]:
        # Keep payload minimal; optional mode may be rejected on some deployments.
        payload = {
            "query": query,
            "top_k": min(max(top_k, 1), 30),
        }

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
        def _post() -> dict:
            with httpx.Client(timeout=90.0, headers=self._headers()) as client:
                response = client.post(f"{self.base_url}/agentic-search", json=payload)
                response.raise_for_status()
                return response.json()

        data = _post()
        papers: list[Paper] = []
        seen: set[str] = set()
        for hit in data.get("hits") or []:
            if not isinstance(hit, dict):
                continue
            paper = _paper_from_chunk(hit)
            if not paper or paper.id in seen:
                continue
            seen.add(paper.id)
            papers.append(paper)
        return papers
