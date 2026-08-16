"""Fill per-claim literature-database labels for handbook compliance."""

from __future__ import annotations

from materials_agent.models import ExtractedRecord, Paper, ResearchGap


def paper_source_map(papers: list[Paper]) -> dict[str, str]:
    return {p.id: (p.source or "unknown").strip() or "unknown" for p in papers}


def annotate_retrieval_databases(
    papers: list[Paper],
    gaps: list[ResearchGap],
    extractions: list[ExtractedRecord] | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, int]:
    """Attach ``retrieval_database`` from ``Paper.source`` onto evidence spans.

    Returns counts useful for audit / verify gates.
    """
    sources = paper_source_map(papers)
    labeled = 0
    missing_paper = 0

    def _fill(span) -> None:
        nonlocal labeled, missing_paper
        if span.retrieval_database and not overwrite:
            labeled += 1
            return
        db = sources.get(span.paper_id)
        if not db:
            missing_paper += 1
            span.retrieval_database = span.retrieval_database or "unknown"
            return
        span.retrieval_database = db
        labeled += 1

    for gap in gaps:
        for span in gap.evidence_chain:
            _fill(span)

    if extractions:
        for rec in extractions:
            for span in rec.evidence:
                _fill(span)

    return {
        "spans_labeled": labeled,
        "spans_missing_paper": missing_paper,
        "gaps": len(gaps),
        "gaps_with_database": sum(
            1
            for g in gaps
            if g.evidence_chain and any(s.retrieval_database for s in g.evidence_chain)
        ),
    }


def gap_databases_summary(gap: ResearchGap) -> list[str]:
    seen: list[str] = []
    for span in gap.evidence_chain:
        db = (span.retrieval_database or "").strip()
        if db and db not in seen:
            seen.append(db)
    return seen
