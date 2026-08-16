"""Semantic Scholar Academic Graph HTTP helpers."""

from __future__ import annotations

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from materials_agent.config import AppConfig
from materials_agent.models import Paper

SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
DEFAULT_FIELDS = (
    "paperId,externalIds,title,year,abstract,authors,citationCount,"
    "venue,url,openAccessPdf,fieldsOfStudy,publicationDate"
)


def resolve_semantic_scholar_api_key(cfg: AppConfig) -> str:
    """Prefer config, then S2_API_KEY / SEMANTIC_SCHOLAR_API_KEY."""
    for value in (
        getattr(cfg.retrieval, "semantic_scholar_api_key", "") or "",
        os.environ.get("S2_API_KEY", ""),
        os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
    ):
        if value and str(value).strip():
            return str(value).strip()
    return ""


def _paper_from_hit(item: dict[str, Any], *, query: str) -> Paper | None:
    paper_id = str(item.get("paperId") or "").strip()
    title = (item.get("title") or "").strip()
    if not paper_id or not title:
        return None

    external = item.get("externalIds") or {}
    doi = external.get("DOI") or external.get("doi")
    if isinstance(doi, str):
        doi = doi.replace("https://doi.org/", "").strip() or None
    else:
        doi = None

    authors = [
        a.get("name", "")
        for a in (item.get("authors") or [])
        if isinstance(a, dict) and a.get("name")
    ]
    oa = item.get("openAccessPdf") or {}
    oa_url = oa.get("url") if isinstance(oa, dict) else None
    concepts = [
        str(x)
        for x in (item.get("fieldsOfStudy") or [])
        if x
    ][:8]
    year = item.get("year")
    try:
        year_i = int(year) if year is not None else None
    except (TypeError, ValueError):
        year_i = None

    return Paper(
        id=f"S2-{paper_id}",
        title=title,
        year=year_i,
        doi=doi,
        abstract=item.get("abstract"),
        authors=authors,
        cited_by=int(item.get("citationCount") or 0),
        venue=item.get("venue"),
        url=item.get("url") or f"https://www.semanticscholar.org/paper/{paper_id}",
        oa_url=oa_url,
        fulltext_url=oa_url,
        oa_status="oa" if oa_url else None,
        concepts=concepts,
        source="semantic_scholar",
        query_tag=query,
        raw={
            "semantic_scholar_paper_id": paper_id,
            "external_ids": external,
            "open_access_pdf": oa,
        },
    )


class SemanticScholarClient:
    def __init__(self, api_key: str = "") -> None:
        self.api_key = (api_key or "").strip()

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        year_from: int | None = None,
        open_access_only: bool = False,
    ) -> list[Paper]:
        params: dict[str, Any] = {
            "query": query,
            "limit": max(1, min(int(limit), 100)),
            "fields": DEFAULT_FIELDS,
        }
        if year_from:
            params["year"] = f"{int(year_from)}-"
        if open_access_only:
            # Flag-style filter: papers that have a public PDF.
            params["openAccessPdf"] = ""

        headers = {"User-Agent": "materials-agent/0.1 (research)"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        )
        def _get() -> dict[str, Any]:
            with httpx.Client(timeout=60.0, headers=headers) as client:
                r = client.get(SEARCH_URL, params=params)
                if r.status_code == 429:
                    raise httpx.HTTPStatusError(
                        "Semantic Scholar rate limited (429)",
                        request=r.request,
                        response=r,
                    )
                r.raise_for_status()
                return r.json()

        payload = _get()
        papers: list[Paper] = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            paper = _paper_from_hit(item, query=query)
            if paper:
                papers.append(paper)
        return papers
