"""Ground Research Gaps in retrievable full-text chunks rather than abstracts."""

from __future__ import annotations

import re

from materials_agent.config import EvidenceRetrievalConfig, QualityConfig
from materials_agent.limitation_quality import is_strong_limitation, looks_like_limitation
from materials_agent.models import (
    AuditEvent,
    EvidenceProvenance,
    EvidenceSpan,
    ExtractedRecord,
    Paper,
    ResearchGap,
)
from materials_agent.tools.index.base import EvidenceIndex

_BOILERPLATE_RE = re.compile(
    r"(?:"
    r"creative\s+commons|creativecommons\.org|to view a copy of this license|"
    r"open access this article is licensed|peer review information|"
    r"reprints and permission|publisher'?s? note|all rights reserved|"
    r"correspondence and requests for materials|competing (?:financial )?interest|"
    r"conflict of interest|author contributions|data availability|"
    r"supporting information is available|supplementary information|"
    r"acknowledgements?|funding(?:\s+information)?|"
    r"this article is protected by copyright"
    r")",
    re.I,
)

_SECTION_DENY = {
    "references",
    "bibliography",
    "acknowledgements",
    "acknowledgement",
    "additional information",
    "supplementary",
    "supplementary information",
    "funding",
    "license",
    "author information",
    "competing interests",
}

def is_boilerplate_text(text: str, section: str | None = None) -> bool:
    """True when a chunk/quote is publisher/legal/meta noise rather than science."""
    if section and section.strip().lower() in _SECTION_DENY:
        return True
    sample = (text or "")[:1200]
    if not sample.strip():
        return True
    if _BOILERPLATE_RE.search(sample):
        return True
    # Reference-block heuristic: many year+author citation commas, little prose verbs.
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", sample))
    if years >= 6 and len(sample) < 900:
        return True
    return False


def _looks_like_limitation(text: str) -> bool:
    return looks_like_limitation(text)


def _is_limitation_gap(gap: ResearchGap) -> bool:
    return gap.id == "gap-limitations" or gap.id.startswith("gap-open-")


def _sync_supporting_to_evidence(gap: ResearchGap) -> None:
    """Keep supporting_paper_ids consistent with grounded evidence (non-contradiction)."""
    if gap.gap_type == "contradiction" or not gap.evidence_chain:
        return
    evid_ids = list(dict.fromkeys(span.paper_id for span in gap.evidence_chain if span.paper_id))
    if not evid_ids:
        return
    kept = [pid for pid in gap.supporting_paper_ids if pid in evid_ids]
    gap.supporting_paper_ids = kept or evid_ids


def _abstract_fallback(paper: Paper, claim: str, quality: QualityConfig) -> EvidenceSpan | None:
    quote = (paper.abstract or paper.title or "").strip()[:500]
    if len(quote) < quality.min_quote_chars:
        return None
    if is_boilerplate_text(quote):
        return None
    return EvidenceSpan(
        paper_id=paper.id,
        claim=claim,
        quote_or_basis=quote,
        confidence=0.35,
        location="abstract" if paper.abstract else "title",
    )


def _span_from_chunk(chunk, score: float, claim: str, quote: str | None = None) -> EvidenceSpan:
    raw = (quote or chunk.text[:500]).strip()
    if quote:
        idx = chunk.text.find(quote[: min(80, len(quote))])
        if idx < 0:
            idx = 0
            raw = chunk.text[:500].strip()
        else:
            raw = chunk.text[idx : idx + 500].strip()
            start = chunk.char_start + idx
            return EvidenceSpan(
                paper_id=chunk.paper_id,
                claim=claim,
                quote_or_basis=raw,
                confidence=min(0.9, max(0.4, 0.45 + score / 2)),
                location="fulltext",
                provenance=EvidenceProvenance(
                    source_url=chunk.source_url,
                    pdf_hash=chunk.pdf_hash,
                    parser=chunk.parser,
                    section=chunk.section,
                    chunk_id=chunk.chunk_id,
                    char_start=start,
                    char_end=start + len(raw),
                    chunk_hash=chunk.chunk_hash,
                ),
            )
    start = chunk.char_start + (chunk.text.find(raw) if raw else 0)
    if start < chunk.char_start:
        start = chunk.char_start
    return EvidenceSpan(
        paper_id=chunk.paper_id,
        claim=claim,
        quote_or_basis=raw,
        confidence=min(0.9, max(0.4, 0.45 + score / 2)),
        location="fulltext",
        provenance=EvidenceProvenance(
            source_url=chunk.source_url,
            pdf_hash=chunk.pdf_hash,
            parser=chunk.parser,
            section=chunk.section,
            chunk_id=chunk.chunk_id,
            char_start=start,
            char_end=start + len(raw),
            chunk_hash=chunk.chunk_hash,
        ),
    )


def _retrieval_query(gap: ResearchGap) -> str:
    if _is_limitation_gap(gap):
        return (
            f"{gap.title} limitation challenge remain unclear not fully debated "
            "still low unresolved drawback uncertainty bottleneck obstacle"
        )
    if gap.id.startswith("gap-temporal") or gap.gap_type == "contradiction":
        return (
            f"{gap.title} result finding mechanism metric ZT "
            "thermal conductivity Seebeck phonon scattering"
        )
    return f"{gap.title}. {gap.description}"


def _usable_hit(
    chunk,
    score: float,
    retrieval: EvidenceRetrievalConfig,
    *,
    require_limitation_cue: bool = False,
) -> bool:
    if score < retrieval.min_retrieval_score:
        return False
    if is_boilerplate_text(chunk.text, chunk.section):
        return False
    if require_limitation_cue and not _looks_like_limitation(chunk.text):
        return False
    return True


def _search_filtered(
    index: EvidenceIndex,
    query: str,
    paper_ids: list[str],
    retrieval: EvidenceRetrievalConfig,
    *,
    require_limitation_cue: bool = False,
    limit: int | None = None,
) -> list[tuple[object, float]]:
    cap = limit or max(retrieval.top_k * 3, 8)
    hits = index.search(query, paper_ids=paper_ids, limit=cap)
    out: list[tuple[object, float]] = []
    for chunk, score in hits:
        if _usable_hit(
            chunk, score, retrieval, require_limitation_cue=require_limitation_cue
        ):
            out.append((chunk, score))
    if retrieval.prefer_same_section:
        # Prefer non-denied scientific-looking sections; Body/Results first.
        def _section_rank(row: tuple[object, float]) -> tuple[int, float]:
            section = (getattr(row[0], "section", None) or "").lower()
            prefer = 0 if any(k in section for k in ("result", "discussion", "body", "intro")) else 1
            return (prefer, -row[1])

        out.sort(key=_section_rank)
    return out


def _dedupe_spans(spans: list[EvidenceSpan], limit: int = 4) -> list[EvidenceSpan]:
    seen: set[str] = set()
    out: list[EvidenceSpan] = []
    for span in spans:
        key = f"{span.paper_id}:{span.quote_or_basis[:80]}"
        if key in seen:
            continue
        if is_boilerplate_text(span.quote_or_basis):
            continue
        seen.add(key)
        out.append(span)
        if len(out) >= limit:
            break
    return out


def _locate_quote_chunk(
    index: EvidenceIndex,
    paper_id: str,
    quote: str,
) -> tuple[object, float] | None:
    """Find a non-boilerplate chunk that contains a distinctive probe from quote."""
    quote = (quote or "").strip()
    if len(quote) < 20:
        return None
    probes = [quote[:80], quote[10:70] if len(quote) > 70 else quote[:40], quote[-60:]]
    hits = index.search(quote[:240], paper_ids=[paper_id], limit=20)
    for chunk, score in hits:
        if is_boilerplate_text(chunk.text, getattr(chunk, "section", None)):
            continue
        text = chunk.text or ""
        if any(p and p in text for p in probes):
            return chunk, max(float(score), 0.75)
    # Broader pass: any overlapping limitation-like chunk for this paper.
    for chunk, score in hits:
        if is_boilerplate_text(chunk.text, getattr(chunk, "section", None)):
            continue
        if _looks_like_limitation(chunk.text):
            return chunk, float(score)
    return None


def _ground_limitation_seeds(
    gap: ResearchGap,
    index: EvidenceIndex | None,
    extractions: list[ExtractedRecord],
    retrieval: EvidenceRetrievalConfig,
) -> list[EvidenceSpan]:
    paper_ids = set(gap.supporting_paper_ids + gap.contradicting_paper_ids)
    selected: list[EvidenceSpan] = []
    for record in extractions:
        if record.paper_id not in paper_ids:
            continue
        for lim in record.limitations[:2]:
            lim = (lim or "").strip()
            if (
                len(lim) < 25
                or is_boilerplate_text(lim)
                or not is_strong_limitation(lim)
            ):
                continue
            if not (index and retrieval.enabled):
                continue
            located = _locate_quote_chunk(index, record.paper_id, lim)
            if located:
                chunk, score = located
                selected.append(
                    _span_from_chunk(chunk, score, "limitation sentence", lim)
                )
                continue
            hits = _search_filtered(
                index,
                lim[:240],
                [record.paper_id],
                retrieval,
                require_limitation_cue=True,
                limit=6,
            )
            if hits:
                selected.append(
                    _span_from_chunk(hits[0][0], max(hits[0][1], 0.55), "limitation sentence")
                )
    return _dedupe_spans(selected, limit=4)


def _ground_temporal(
    gap: ResearchGap,
    index: EvidenceIndex,
    retrieval: EvidenceRetrievalConfig,
) -> list[EvidenceSpan]:
    query = _retrieval_query(gap)
    support = _search_filtered(
        index, query, list(dict.fromkeys(gap.supporting_paper_ids)), retrieval, limit=8
    )
    contradict = _search_filtered(
        index, query, list(dict.fromkeys(gap.contradicting_paper_ids)), retrieval, limit=8
    )
    if not support or not contradict:
        return []
    selected = [
        _span_from_chunk(support[0][0], support[0][1], gap.title),
        _span_from_chunk(contradict[0][0], contradict[0][1], gap.title),
    ]
    if len(support) > 1:
        selected.append(_span_from_chunk(support[1][0], support[1][1], gap.title))
    if len(contradict) > 1:
        selected.append(_span_from_chunk(contradict[1][0], contradict[1][1], gap.title))
    return _dedupe_spans(selected, limit=4)


def ground_gap_evidence(
    gaps: list[ResearchGap],
    papers: list[Paper],
    index: EvidenceIndex | None,
    retrieval: EvidenceRetrievalConfig,
    quality: QualityConfig,
    audit: list[AuditEvent],
    extractions: list[ExtractedRecord] | None = None,
) -> list[ResearchGap]:
    """Replace abstract anchors with top evidence chunks for each Gap claim."""
    paper_by_id = {paper.id: paper for paper in papers}
    records = extractions or []
    fulltext_count = 0
    fallback_count = 0
    rejected_count = 0
    for gap in gaps:
        paper_ids = list(
            dict.fromkeys(gap.supporting_paper_ids + gap.contradicting_paper_ids)
        )
        selected: list[EvidenceSpan] = []
        is_temporal = gap.id.startswith("gap-temporal") or (
            gap.gap_type == "contradiction"
            and bool(gap.supporting_paper_ids)
            and bool(gap.contradicting_paper_ids)
        )

        if _is_limitation_gap(gap) and records:
            selected = _ground_limitation_seeds(gap, index, records, retrieval)

        if not selected and is_temporal and index and retrieval.enabled and paper_ids:
            selected = _ground_temporal(gap, index, retrieval)
            if not selected and quality.allow_abstract_fallback:
                # Both eras must contribute; never fill with one-sided boilerplate-prone hits.
                support_fb = [
                    span
                    for paper_id in gap.supporting_paper_ids[:2]
                    if (paper := paper_by_id.get(paper_id))
                    and (span := _abstract_fallback(paper, gap.title, quality))
                ]
                contradict_fb = [
                    span
                    for paper_id in gap.contradicting_paper_ids[:2]
                    if (paper := paper_by_id.get(paper_id))
                    and (span := _abstract_fallback(paper, gap.title, quality))
                ]
                if support_fb and contradict_fb:
                    selected = _dedupe_spans(support_fb[:2] + contradict_fb[:2], limit=4)
                    gap.review_notes = (
                        f"{gap.review_notes}; temporal evidence used abstract on "
                        "at least one era (missing dual-era fulltext)"
                    ).strip("; ")

        if not selected and not is_temporal and index and retrieval.enabled and paper_ids:
            require_lim = _is_limitation_gap(gap)
            hits = _search_filtered(
                index,
                _retrieval_query(gap),
                paper_ids,
                retrieval,
                require_limitation_cue=require_lim,
            )
            selected = _dedupe_spans(
                [_span_from_chunk(chunk, score, gap.title) for chunk, score in hits],
                limit=4,
            )
            # Soft fallback for limitations: allow non-cue hits if still non-boilerplate.
            if not selected and require_lim:
                hits = _search_filtered(
                    index, _retrieval_query(gap), paper_ids, retrieval, require_limitation_cue=False
                )
                selected = _dedupe_spans(
                    [
                        _span_from_chunk(chunk, score, gap.title)
                        for chunk, score in hits
                        if _looks_like_limitation(chunk.text)
                    ],
                    limit=4,
                )

        # Keep non-boilerplate seeded quotes if retrieval found nothing better.
        if not selected and not is_temporal:
            seeded = [
                span
                for span in gap.evidence_chain
                if not is_boilerplate_text(span.quote_or_basis)
                and len(span.quote_or_basis) >= quality.min_quote_chars
            ]
            if _is_limitation_gap(gap):
                seeded = [s for s in seeded if _looks_like_limitation(s.quote_or_basis)]
            selected = _dedupe_spans(seeded, limit=4)

        if selected and quality.require_fulltext_gap_evidence:
            selected = [
                span
                for span in selected
                if span.provenance
                and span.provenance.chunk_id
                and span.provenance.pdf_hash
            ]
        if selected:
            gap.evidence_chain = selected
            _sync_supporting_to_evidence(gap)
            fulltext_count += 1
            continue

        if quality.allow_abstract_fallback:
            fallback = [
                span
                for paper_id in paper_ids[:4]
                if (paper := paper_by_id.get(paper_id))
                and (span := _abstract_fallback(paper, gap.title, quality))
            ]
            if _is_limitation_gap(gap):
                fallback = [s for s in fallback if _looks_like_limitation(s.quote_or_basis)]
            if fallback:
                gap.evidence_chain = fallback
                _sync_supporting_to_evidence(gap)
                gap.review_notes = (
                    f"{gap.review_notes}; abstract fallback because no fulltext chunk"
                ).strip("; ")
                fallback_count += 1
                continue
        if quality.require_fulltext_gap_evidence:
            gap.review_status = "rejected"
            gap.review_notes = (
                f"{gap.review_notes}; rejected: no qualifying fulltext evidence"
            ).strip("; ")
            rejected_count += 1

    audit.append(
        AuditEvent(
            step="evidence_retrieve",
            tool=type(index).__name__ if index else "none",
            input_summary=f"{len(gaps)} gaps",
            output_summary=(
                f"fulltext={fulltext_count} abstract_fallback={fallback_count} "
                f"rejected={rejected_count}"
            ),
        )
    )
    return [gap for gap in gaps if gap.review_status != "rejected"]
