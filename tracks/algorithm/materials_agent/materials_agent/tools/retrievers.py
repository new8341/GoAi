from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Protocol

import httpx
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from materials_agent.config import AppConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.topic_focus import (
    extract_topic_materials,
    paper_mentions_materials,
    paper_property_hits,
    topic_property_tokens,
)


def resolve_openalex_api_key(cfg: AppConfig) -> str:
    """Prefer config, then OPENALEX_API_KEY env."""
    return (
        (getattr(cfg.retrieval, "openalex_api_key", "") or "").strip()
        or os.environ.get("OPENALEX_API_KEY", "").strip()
    )


def _format_http_exc(exc: BaseException) -> str:
    """Unwrap tenacity RetryError and summarize httpx status for UI/audit."""
    cur: BaseException | None = exc
    if isinstance(exc, RetryError):
        try:
            cur = exc.last_attempt.exception()
        except Exception:  # noqa: BLE001
            cur = exc
    if isinstance(cur, httpx.HTTPStatusError):
        code = cur.response.status_code if cur.response is not None else "?"
        url = str(cur.request.url) if cur.request is not None else ""
        return f"HTTP {code} {url}".strip()
    return f"{type(cur).__name__}: {cur}"


_RETRIEVE_ERRORS = (httpx.HTTPError, RetryError, OSError, ValueError, TimeoutError)


class Retriever(Protocol):
    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
    ) -> list[Paper]: ...


def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str | None:
    if not inverted:
        return None
    pairs: list[tuple[int, str]] = []
    for word, positions in inverted.items():
        for pos in positions:
            pairs.append((pos, word))
    pairs.sort(key=lambda x: x[0])
    return " ".join(w for _, w in pairs)


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 2}


def score_relevance(paper: Paper, topic: str, ontology: dict | None = None) -> float:
    ontology = ontology or {}
    q_tokens = _tokenize(topic)
    for kw in ontology.get("search_keywords") or []:
        q_tokens |= _tokenize(str(kw))
    for prop in ontology.get("properties") or []:
        q_tokens |= _tokenize(str(prop))
    doc = _tokenize(
        f"{paper.title} {paper.abstract or ''} {' '.join(paper.concepts)}"
    )
    if not q_tokens or not doc:
        return 0.0
    overlap = len(q_tokens & doc) / len(q_tokens)
    cite_boost = min(0.2, (paper.cited_by or 0) / 500.0)
    oa_boost = 0.05 if paper.oa_url else 0.0
    year_boost = 0.05 if paper.year and paper.year >= 2020 else 0.0
    score = overlap + cite_boost + oa_boost + year_boost

    topic_mats = extract_topic_materials(topic, ontology)
    props = topic_property_tokens(topic)
    if topic_mats:
        if paper_mentions_materials(paper, topic_mats):
            score += 0.28
            score += 0.06 * min(3, paper_property_hits(paper, props))
        else:
            # Sibling TE systems (Bi2Te3/GeTe/…) often share ontology keywords;
            # keep them discoverable but out of the top-k unless topic-named.
            score *= 0.22
    return round(min(1.0, score), 4)


def _dedupe_rank(
    papers: list[Paper],
    topic: str,
    cfg: AppConfig,
    ontology: dict | None,
) -> list[Paper]:
    best: dict[str, Paper] = {}
    for p in papers:
        p.relevance_score = score_relevance(p, topic, ontology)
        prev = best.get(p.id)
        if prev is None or p.relevance_score > prev.relevance_score:
            best[p.id] = p
    ranked = sorted(best.values(), key=lambda x: (x.relevance_score, x.cited_by), reverse=True)
    if cfg.retrieval.prefer_oa:
        ranked.sort(
            key=lambda x: (x.relevance_score, 1 if x.oa_url else 0, x.cited_by),
            reverse=True,
        )
    filtered = [p for p in ranked if p.relevance_score >= cfg.retrieval.min_relevance]
    if not filtered:
        filtered = ranked

    # Hard OA gate: open_access_only without a resolvable oa_url rarely yields PDFs.
    if cfg.open_access_only:
        with_url = [p for p in filtered if p.oa_url]
        if with_url:
            filtered = with_url

    topic_mats = extract_topic_materials(topic, ontology)
    if topic_mats:
        hits = [p for p in filtered if paper_mentions_materials(p, topic_mats)]
        # Prefer a topic-hit majority when the pool is large enough.
        need = max(3, min(cfg.max_papers, max(1, cfg.max_papers // 2)))
        if len(hits) >= need:
            filtered = hits
        elif hits:
            rest = [p for p in filtered if p.id not in {h.id for h in hits}]
            filtered = hits + rest

    # Small UI batches: among topic-filtered candidates, prefer OA so fulltext
    # grounding (R5) remains feasible without hard open_access_only filtering.
    if cfg.retrieval.prefer_oa and cfg.max_papers <= 10:
        oa = [p for p in filtered if p.oa_url]
        non = [p for p in filtered if not p.oa_url]
        if oa:
            filtered = oa + non

    return filtered[: cfg.max_papers]


class OpenAlexRetriever:
    BASE = "https://api.openalex.org/works"

    def _fetch_one(self, query: str, cfg: AppConfig, per_page: int) -> list[Paper]:
        filters = [f"from_publication_date:{cfg.year_from}-01-01"]
        if cfg.open_access_only:
            filters.append("is_oa:true")
        if cfg.retrieval.min_cited_by > 0:
            filters.append(f"cited_by_count:>{cfg.retrieval.min_cited_by}")

        params: dict[str, str | int] = {
            "search": query,
            "filter": ",".join(filters),
            "per_page": min(per_page, 50),
            "sort": "relevance_score:desc",
            "mailto": cfg.retrieval.mailto,
        }
        api_key = resolve_openalex_api_key(cfg)
        if api_key:
            params["api_key"] = api_key
        headers = {"User-Agent": f"materials-agent/0.1 (mailto:{cfg.retrieval.mailto})"}

        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        )
        def _get() -> dict:
            with httpx.Client(timeout=60.0, headers=headers) as client:
                r = client.get(self.BASE, params=params)
                r.raise_for_status()
                return r.json()

        payload = _get()
        papers: list[Paper] = []
        for item in payload.get("results", []):
            abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
            authors = [
                a.get("author", {}).get("display_name", "")
                for a in item.get("authorships", [])
                if a.get("author", {}).get("display_name")
            ]
            concepts = [
                c.get("display_name", "")
                for c in item.get("concepts", [])[:8]
                if c.get("display_name")
            ]
            primary = item.get("primary_location") or {}
            source = (primary.get("source") or {}).get("display_name")
            open_access = item.get("open_access") or {}
            oa = open_access.get("oa_url")
            locations = item.get("locations") or []
            best_location = item.get("best_oa_location") or {}
            pdf_url = best_location.get("pdf_url")
            if not pdf_url:
                pdf_url = next(
                    (
                        location.get("pdf_url")
                        for location in locations
                        if location.get("is_oa") and location.get("pdf_url")
                    ),
                    None,
                )
            doi = None
            ids = item.get("ids") or {}
            if ids.get("doi"):
                doi = ids["doi"].replace("https://doi.org/", "")
            papers.append(
                Paper(
                    id=item.get("id", "").split("/")[-1] or item.get("id", ""),
                    title=(item.get("display_name") or "").strip(),
                    year=item.get("publication_year"),
                    doi=doi,
                    abstract=abstract,
                    authors=authors,
                    cited_by=int(item.get("cited_by_count") or 0),
                    venue=source,
                    url=item.get("id"),
                    oa_url=oa,
                    fulltext_url=pdf_url or oa,
                    oa_status=open_access.get("oa_status"),
                    oa_license=best_location.get("license"),
                    oa_version=best_location.get("version"),
                    concepts=concepts,
                    source="openalex",
                    query_tag=query,
                    raw={
                        "openalex_id": item.get("id"),
                        "best_oa_location": best_location,
                    },
                )
            )
        return papers

    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        per_page = min(50, max(cfg.max_papers, cfg.max_papers * cfg.retrieval.fetch_multiplier))
        use_queries = queries if cfg.retrieval.multi_query else queries[:1]
        collected: list[Paper] = []
        errors: list[str] = []
        for q in use_queries:
            try:
                collected.extend(self._fetch_one(q, cfg, per_page))
            except _RETRIEVE_ERRORS as exc:
                errors.append(f"{q[:80]}: {_format_http_exc(exc)}")

        if not collected:
            detail = "; ".join(errors[:3]) or "unknown OpenAlex failure"
            audit.append(
                AuditEvent(
                    step="retrieve",
                    tool="openalex",
                    input_summary="; ".join(use_queries)[:300],
                    output_summary=f"failed: {detail}",
                    meta={"errors": errors[:5], "openalex_api_key": bool(resolve_openalex_api_key(cfg))},
                )
            )
            raise RuntimeError(
                "OpenAlex 检索失败（已重试）。常见原因：429 限流、403、网络中断。"
                f" 详情: {detail}"
            )

        papers = _dedupe_rank(collected, cfg.topic, cfg, ontology)
        topic_mats = extract_topic_materials(cfg.topic, ontology)
        topic_hits = (
            sum(1 for p in papers if paper_mentions_materials(p, topic_mats))
            if topic_mats
            else len(papers)
        )
        audit.append(
            AuditEvent(
                step="retrieve",
                tool="openalex",
                input_summary="; ".join(use_queries)[:300],
                output_summary=f"{len(papers)} papers after rank/filter (raw={len(collected)})",
                meta={
                    "queries": use_queries,
                    "min_relevance": cfg.retrieval.min_relevance,
                    "openalex_api_key": bool(resolve_openalex_api_key(cfg)),
                    "topic_materials": topic_mats,
                    "topic_hit_count": topic_hits,
                    "topic_hit_rate": round(topic_hits / max(1, len(papers)), 4),
                    "top_scores": [
                        {
                            "id": p.id,
                            "score": p.relevance_score,
                            "title": p.title[:80],
                            "topic_hit": paper_mentions_materials(p, topic_mats)
                            if topic_mats
                            else True,
                        }
                        for p in papers[:8]
                    ],
                },
            )
        )
        return papers


class LocalJsonRetriever:
    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        # Resolve relative to project root (…/materials_agent/), not the inner package dir.
        root = Path(__file__).resolve().parents[2]
        cache = Path(cfg.cache_dir)
        if not cache.is_absolute():
            cache = (root / cache).resolve()
        path = cache.parent / "local_papers.json"
        if not path.exists():
            raise FileNotFoundError(f"Local paper file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        papers = [Paper.model_validate(x) for x in data]
        for p in papers:
            p.query_tag = queries[0] if queries else cfg.topic
        papers = _dedupe_rank(papers, cfg.topic, cfg, ontology)
        audit.append(
            AuditEvent(
                step="retrieve",
                tool="local_json",
                input_summary="; ".join(queries)[:200],
                output_summary=f"{len(papers)} papers from {path}",
            )
        )
        return papers


def _fallback_or_fail(
    *,
    configured: str,
    reason: str,
    queries: list[str],
    cfg: AppConfig,
    audit: list[AuditEvent],
    ontology: dict | None,
    extra: dict | None = None,
) -> list[Paper]:
    from materials_agent.tools.backend_honesty import BackendFallbackError, retrieve_meta

    allow = bool(getattr(cfg.retrieval, "allow_backend_fallback", True))
    if not allow:
        audit.append(
            AuditEvent(
                step="retrieve",
                tool=configured,
                input_summary="; ".join(queries)[:200],
                output_summary=f"FAIL; {reason}; fallback forbidden",
                meta=retrieve_meta(
                    configured=configured,
                    effective=configured,
                    fallback_reason=reason,
                    extra=extra,
                ),
            )
        )
        raise BackendFallbackError(
            f"{configured} failed ({reason}); retrieval.allow_backend_fallback=false. "
            "Provide credentials / fix the backend, or set allow_backend_fallback: true."
        )
    audit.append(
        AuditEvent(
            step="retrieve",
            tool=configured,
            input_summary="; ".join(queries)[:200],
            output_summary=f"{reason}; fallback openalex",
            meta=retrieve_meta(
                configured=configured,
                effective="openalex",
                fallback_reason=reason,
                extra=extra,
            ),
        )
    )
    return OpenAlexRetriever().search(queries, cfg, audit, ontology)


class SciverseRetriever:
    """Sciverse Agent Tools backend; optional OpenAlex fallback when allowed."""

    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        from materials_agent.tools.backend_honesty import retrieve_meta
        from materials_agent.tools.sciverse_client import (
            SciverseClient,
            resolve_sciverse_base,
            resolve_sciverse_token,
        )

        token = resolve_sciverse_token(cfg)
        if not token:
            return _fallback_or_fail(
                configured="sciverse",
                reason="no token",
                queries=queries,
                cfg=cfg,
                audit=audit,
                ontology=ontology,
                extra={"hint": "Set SCIVERSE_API_TOKEN from https://sciverse.space"},
            )

        client = SciverseClient(token, resolve_sciverse_base(cfg))
        papers: list[Paper] = []
        errors: list[str] = []
        per = max(cfg.max_papers, cfg.max_papers * cfg.retrieval.fetch_multiplier)
        mode = (getattr(cfg.retrieval, "sciverse_mode", "meta") or "meta").lower()
        use_semantic = mode in {"semantic", "agentic", "hybrid"}

        for query in queries:
            try:
                if use_semantic:
                    batch = client.semantic_search(query, top_k=min(per, 30))
                else:
                    batch = client.meta_search(
                        query, year_from=cfg.year_from, page_size=min(per, 50)
                    )
                papers.extend(batch)
            except _RETRIEVE_ERRORS as exc:
                errors.append(f"{query[:80]}: {_format_http_exc(exc)}")

        if mode == "hybrid":
            for query in queries[:2]:
                try:
                    papers.extend(
                        client.meta_search(
                            query, year_from=cfg.year_from, page_size=min(per, 50)
                        )
                    )
                except _RETRIEVE_ERRORS as exc:
                    errors.append(f"meta:{query[:60]}: {_format_http_exc(exc)}")

        if not papers:
            return _fallback_or_fail(
                configured="sciverse",
                reason="empty/error",
                queries=queries,
                cfg=cfg,
                audit=audit,
                ontology=ontology,
                extra={"errors": errors[:5]},
            )

        ranked = _dedupe_rank(papers, cfg.topic, cfg, ontology)
        audit.append(
            AuditEvent(
                step="retrieve",
                tool="sciverse",
                input_summary="; ".join(queries)[:200],
                output_summary=f"{len(ranked)} papers (raw={len(papers)})",
                meta=retrieve_meta(
                    configured="sciverse",
                    effective="sciverse",
                    extra={
                        "mode": getattr(cfg.retrieval, "sciverse_mode", "meta"),
                        "errors": errors[:5],
                    },
                ),
            )
        )
        return ranked


class SemanticScholarRetriever:
    """Semantic Scholar Graph search; falls back to OpenAlex on empty/error."""

    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        from materials_agent.tools.semantic_scholar_client import (
            SemanticScholarClient,
            resolve_semantic_scholar_api_key,
        )

        api_key = resolve_semantic_scholar_api_key(cfg)
        client = SemanticScholarClient(api_key)
        per = max(cfg.max_papers, cfg.max_papers * cfg.retrieval.fetch_multiplier)
        use_queries = queries if cfg.retrieval.multi_query else queries[:1]
        collected: list[Paper] = []
        errors: list[str] = []

        for query in use_queries:
            try:
                batch = client.search(
                    query,
                    limit=min(per, 100),
                    year_from=cfg.year_from,
                    open_access_only=bool(cfg.open_access_only),
                )
                if cfg.retrieval.min_cited_by > 0:
                    batch = [
                        p for p in batch if (p.cited_by or 0) >= cfg.retrieval.min_cited_by
                    ]
                collected.extend(batch)
            except _RETRIEVE_ERRORS as exc:
                errors.append(f"{query[:80]}: {_format_http_exc(exc)}")

        if not collected:
            return _fallback_or_fail(
                configured="semantic_scholar",
                reason="empty/error",
                queries=use_queries,
                cfg=cfg,
                audit=audit,
                ontology=ontology,
                extra={
                    "errors": errors[:5],
                    "has_api_key": bool(api_key),
                    "hint": "Set S2_API_KEY from https://www.semanticscholar.org/product/api",
                },
            )

        from materials_agent.tools.backend_honesty import retrieve_meta

        ranked = _dedupe_rank(collected, cfg.topic, cfg, ontology)
        audit.append(
            AuditEvent(
                step="retrieve",
                tool="semantic_scholar",
                input_summary="; ".join(use_queries)[:200],
                output_summary=f"{len(ranked)} papers after rank/filter (raw={len(collected)})",
                meta=retrieve_meta(
                    configured="semantic_scholar",
                    effective="semantic_scholar",
                    extra={
                        "has_api_key": bool(api_key),
                        "errors": errors[:5],
                        "top_scores": [
                            {"id": p.id, "score": p.relevance_score, "title": p.title[:80]}
                            for p in ranked[:5]
                        ],
                    },
                ),
            )
        )
        return ranked


class SciBaseRetriever:
    """opendatalab/Sci-Base via local materials cache (default) or HF streaming."""

    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        from materials_agent.tools.backend_honesty import retrieve_meta
        from materials_agent.tools.scibase_client import (
            build_materials_cache,
            iter_hf_stream,
            load_cache_rows,
            resolve_scibase_cache_path,
            row_to_paper,
            score_row,
            search_cache,
        )

        cache_path = resolve_scibase_cache_path(cfg)
        cats = list(getattr(cfg.retrieval, "scibase_category_substrings", None) or [])
        prefer_cache = bool(getattr(cfg.retrieval, "scibase_prefer_cache", True))
        allow_stream = bool(getattr(cfg.retrieval, "scibase_streaming", False))
        top_k = max(cfg.max_papers, cfg.max_papers * cfg.retrieval.fetch_multiplier)
        use_queries = queries if cfg.retrieval.multi_query else queries[:1]

        rows = load_cache_rows(cache_path) if prefer_cache else []
        mode = "cache"
        if not rows and allow_stream:
            mode = "stream_build"
            try:
                build_materials_cache(
                    cache_path,
                    dataset=getattr(cfg.retrieval, "scibase_dataset", "opendatalab/Sci-Base"),
                    config=getattr(cfg.retrieval, "scibase_config", "paper"),
                    max_scan=int(getattr(cfg.retrieval, "scibase_max_scan", 5000) or 5000),
                    max_keep=max(80, top_k * 10),
                    category_substrings=cats or None,
                    keyword_boost=" ".join(use_queries)[:200],
                )
                rows = load_cache_rows(cache_path)
            except Exception as exc:  # noqa: BLE001
                return _fallback_or_fail(
                    configured="scibase",
                    reason=f"stream_build_failed:{type(exc).__name__}",
                    queries=use_queries,
                    cfg=cfg,
                    audit=audit,
                    ontology=ontology,
                    extra={"error": str(exc)[:240], "cache_path": str(cache_path)},
                )

        if not rows and allow_stream:
            mode = "stream_search"
            collected: list[Paper] = []
            max_scan = int(getattr(cfg.retrieval, "scibase_max_scan", 5000) or 5000)
            try:
                for row in iter_hf_stream(
                    dataset=getattr(cfg.retrieval, "scibase_dataset", "opendatalab/Sci-Base"),
                    config=getattr(cfg.retrieval, "scibase_config", "paper"),
                    max_scan=max_scan,
                ):
                    best = 0.0
                    best_q = use_queries[0] if use_queries else cfg.topic
                    for q in use_queries:
                        s = score_row(row, q)
                        if s > best:
                            best = s
                            best_q = q
                    if best < cfg.retrieval.min_relevance:
                        continue
                    paper = row_to_paper(row, query_tag=best_q)
                    if paper is None:
                        continue
                    paper.relevance_score = round(best, 4)
                    collected.append(paper)
                    if len(collected) >= top_k * 3:
                        break
            except Exception as exc:  # noqa: BLE001
                return _fallback_or_fail(
                    configured="scibase",
                    reason=f"stream_search_failed:{type(exc).__name__}",
                    queries=use_queries,
                    cfg=cfg,
                    audit=audit,
                    ontology=ontology,
                    extra={"error": str(exc)[:240]},
                )
            ranked = _dedupe_rank(collected, cfg.topic, cfg, ontology)
        elif rows:
            ranked = search_cache(
                rows,
                use_queries or [cfg.topic],
                top_k=top_k,
                category_substrings=cats or None,
            )
            ranked = _dedupe_rank(ranked, cfg.topic, cfg, ontology)
        else:
            return _fallback_or_fail(
                configured="scibase",
                reason="empty_cache_no_stream",
                queries=use_queries,
                cfg=cfg,
                audit=audit,
                ontology=ontology,
                extra={
                    "cache_path": str(cache_path),
                    "hint": "Run scripts/build_scibase_cache.py or set scibase_streaming: true",
                },
            )

        if not ranked:
            return _fallback_or_fail(
                configured="scibase",
                reason="no_hits",
                queries=use_queries,
                cfg=cfg,
                audit=audit,
                ontology=ontology,
                extra={"mode": mode, "cache_rows": len(rows)},
            )

        audit.append(
            AuditEvent(
                step="retrieve",
                tool="scibase",
                input_summary="; ".join(use_queries)[:200],
                output_summary=f"{len(ranked)} papers (mode={mode}, cache_rows={len(rows)})",
                meta=retrieve_meta(
                    configured="scibase",
                    effective="scibase",
                    extra={
                        "dataset": getattr(
                            cfg.retrieval, "scibase_dataset", "opendatalab/Sci-Base"
                        ),
                        "cache_path": str(cache_path),
                        "mode": mode,
                        "cache_rows": len(rows),
                        "top_scores": [
                            {"id": p.id, "score": p.relevance_score, "title": p.title[:80]}
                            for p in ranked[:5]
                        ],
                    },
                ),
            )
        )
        return ranked


class HybridSciverseSciBaseRetriever:
    """Sciverse primary + Sci-Base enrichment (handbook: use Sci-Base corpus)."""

    def search(
        self,
        queries: list[str],
        cfg: AppConfig,
        audit: list[AuditEvent],
        ontology: dict | None = None,
    ) -> list[Paper]:
        from materials_agent.tools.backend_honesty import retrieve_meta

        primary = SciverseRetriever().search(queries, cfg, audit, ontology)
        secondary: list[Paper] = []
        try:
            # Sci-Base enrichment should not silently replace Sciverse with OpenAlex
            # when cache is empty: temporarily forbid fallback for the scibase leg.
            scibase_cfg = cfg.model_copy(deep=True)
            scibase_cfg.retrieval.allow_backend_fallback = False
            secondary = SciBaseRetriever().search(queries, scibase_cfg, audit, ontology)
        except Exception as exc:  # noqa: BLE001
            audit.append(
                AuditEvent(
                    step="retrieve",
                    tool="sciverse_scibase",
                    input_summary="; ".join(queries)[:200],
                    output_summary=f"scibase enrich skipped: {type(exc).__name__}",
                    meta={"error": str(exc)[:240], "primary_n": len(primary)},
                )
            )

        merged_primary = _dedupe_rank(primary + secondary, cfg.topic, cfg, ontology)
        reserve = min(2, max(1, cfg.max_papers // 3), cfg.max_papers)
        scibase_hits = sorted(
            [p for p in secondary if p.source == "scibase"],
            key=lambda x: x.relevance_score,
            reverse=True,
        )
        # Boost reserved Sci-Base rows so oversampling + fulltext select cannot drop them.
        reserved: list[Paper] = []
        for p in scibase_hits[:reserve]:
            p.relevance_score = max(float(p.relevance_score or 0.0), 0.55)
            reserved.append(p)
        primary_keep = [
            p
            for p in merged_primary
            if p.id not in {r.id for r in reserved}
        ]
        # Cap primary so reserved slots survive max_papers / oversample trim.
        slot = max(cfg.max_papers, cfg.max_papers * cfg.retrieval.fetch_multiplier)
        keep_n = max(0, slot - len(reserved))
        merged = primary_keep[:keep_n] + reserved
        # Stable order: score desc but reserved already boosted.
        merged = sorted(
            merged,
            key=lambda x: (x.relevance_score, x.cited_by),
            reverse=True,
        )[:slot]

        audit.append(
            AuditEvent(
                step="retrieve",
                tool="sciverse_scibase",
                input_summary="; ".join(queries)[:200],
                output_summary=(
                    f"{len(merged)} merged "
                    f"(sciverse≈{sum(1 for p in merged if p.source=='sciverse')}, "
                    f"scibase={sum(1 for p in merged if p.source=='scibase')})"
                ),
                meta=retrieve_meta(
                    configured="sciverse_scibase",
                    effective="sciverse_scibase",
                    extra={
                        "primary_n": len(primary),
                        "secondary_n": len(secondary),
                        "merged_n": len(merged),
                        "scibase_reserved": len(reserved),
                        "scibase_in_merged": sum(1 for p in merged if p.source == "scibase"),
                    },
                ),
            )
        )
        return merged


def get_retriever(name: str) -> Retriever:
    mapping = {
        "openalex": OpenAlexRetriever(),
        "local_json": LocalJsonRetriever(),
        "sciverse": SciverseRetriever(),
        "scibase": SciBaseRetriever(),
        "sciverse_scibase": HybridSciverseSciBaseRetriever(),
        "semantic_scholar": SemanticScholarRetriever(),
        "s2": SemanticScholarRetriever(),
    }
    if name not in mapping:
        raise ValueError(f"Unknown retrieval backend: {name}")
    return mapping[name]
