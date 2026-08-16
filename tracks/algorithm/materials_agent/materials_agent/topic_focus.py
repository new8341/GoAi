"""Topic-focus helpers: material gates and optimization monitors."""

from __future__ import annotations

import re
from typing import Any

from materials_agent.models import ExtractedRecord, Paper, ResearchGap

_MATERIAL_PAT = re.compile(
    r"\b(?:Bi2Te3|PbTe|SnSe|GeTe|Mg3Sb2|CoSb3|SiGe|Cu2Se|half[- ]Heusler|"
    r"perovskite|MOF|COF|MXene|graphene|LiFePO4|NMC|NCA|"
    r"[A-Z][a-z]?(?:\d+[A-Z][a-z]?\d*){1,4})\b"
)

# Fallback only when ontology does not declare property_focus / properties.
_PROPERTY_FOCUS = (
    "vacancy",
    "vacancies",
    "lattice",
    "thermal",
    "conductivity",
    "phonon",
    "scattering",
    "defect",
    "kappa",
    "κ",
)

REQUIRED_METRIC_KEYS = {
    "topic_hit_rate",
    "gap_material_alignment",
    "evidence_boilerplate_rate",
    "provenance_coverage",
    "pass_flags",
    "fulltext_ratio",
    "n_papers",
    "n_gaps",
}


def extract_topic_materials(topic: str, ontology: dict | None = None) -> list[str]:
    """Materials explicitly named in the topic (plus ontology hits in topic)."""
    ontology = ontology or {}
    found: list[str] = []
    low = (topic or "").lower()
    for m in ontology.get("materials_examples") or []:
        if str(m).lower() in low:
            found.append(str(m))
    found.extend(_MATERIAL_PAT.findall(topic or ""))
    # Preserve order, de-dupe case-insensitively.
    out: list[str] = []
    seen: set[str] = set()
    for m in found:
        key = m.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _ontology_property_tokens(ontology: dict | None) -> set[str]:
    ontology = ontology or {}
    tokens: set[str] = set()
    for key in ("property_focus", "properties", "search_keywords"):
        for item in ontology.get(key) or []:
            raw = str(item).strip().lower()
            if not raw:
                continue
            tokens.add(raw)
            for part in re.findall(r"[a-zA-Zκ]{3,}", raw):
                tokens.add(part.lower())
    return tokens


def topic_property_tokens(topic: str, ontology: dict | None = None) -> set[str]:
    """Tokens that appear in the topic; ontology lists win, hardcoded table is fallback."""
    low = (topic or "").lower()
    declared = _ontology_property_tokens(ontology)
    pool = declared or set(_PROPERTY_FOCUS)
    hits = {t for t in pool if t in low}
    return hits or {t for t in _PROPERTY_FOCUS if t in low}


def paper_blob(paper: Paper) -> str:
    return f"{paper.title} {paper.abstract or ''} {' '.join(paper.concepts or [])}".lower()


def paper_mentions_materials(paper: Paper, materials: list[str]) -> bool:
    if not materials:
        return True
    blob = paper_blob(paper)
    return any(m.lower() in blob for m in materials)


def paper_property_hits(paper: Paper, props: set[str]) -> int:
    if not props:
        return 0
    blob = paper_blob(paper)
    return sum(1 for p in props if p in blob)


def gap_aligned_to_topic(gap: ResearchGap, topic_materials: list[str]) -> bool:
    if not topic_materials:
        return True
    # Corpus-level method balance / default remain about the topic-gated set.
    if gap.id in {"gap-method-balance", "gap-default"}:
        return True
    if gap.id.startswith("gap-missing-link"):
        return True
    blob = f"{gap.id} {gap.title} {gap.description}".lower()
    # Legacy unscoped limitation bags stay unaligned unless they name the topic material.
    if any(m.lower() in blob for m in topic_materials):
        return True
    # Open-issue gaps may quote property language; also accept evidence quotes.
    if gap.id.startswith("gap-open-"):
        ev = " ".join(span.quote_or_basis for span in (gap.evidence_chain or [])).lower()
        return any(m.lower() in ev for m in topic_materials)
    return False


def compute_optimization_metrics(
    topic: str,
    papers: list[Paper],
    gaps: list[ResearchGap],
    extractions: list[ExtractedRecord] | None = None,
    ontology: dict | None = None,
) -> dict[str, Any]:
    """Four headline monitors for retrieval / gap optimization loops."""
    from materials_agent.agents.evidence_selector import is_boilerplate_text

    mats = extract_topic_materials(topic, ontology)
    props = topic_property_tokens(topic, ontology)
    n_papers = max(1, len(papers))
    topic_hits = sum(1 for p in papers if paper_mentions_materials(p, mats)) if mats else len(papers)
    prop_hits = sum(1 for p in papers if paper_property_hits(p, props) > 0) if props else 0
    n_ft = sum(1 for p in papers if (p.full_text or "").strip())

    n_gaps = max(1, len(gaps))
    aligned_gaps = sum(1 for g in gaps if gap_aligned_to_topic(g, mats)) if mats else len(gaps)

    spans = [span for g in gaps for span in (g.evidence_chain or [])]
    n_spans = max(1, len(spans))
    boilerplate = sum(1 for s in spans if is_boilerplate_text(s.quote_or_basis))
    with_prov = sum(
        1
        for s in spans
        if s.provenance and s.provenance.chunk_id and s.provenance.pdf_hash
    )

    ext_topic = 0
    if extractions and mats:
        for e in extractions:
            if any(m.lower() in {x.lower() for x in e.materials} for m in mats):
                ext_topic += 1

    return {
        "topic_materials": mats,
        "topic_property_tokens": sorted(props),
        "topic_hit_rate": round(topic_hits / n_papers, 4),
        "topic_hit_count": topic_hits,
        "papers": len(papers),
        "n_papers": len(papers),
        "n_gaps": len(gaps),
        "fulltext_ratio": round(n_ft / n_papers, 4),
        "property_hit_rate": round(prop_hits / n_papers, 4) if props else None,
        "gap_material_alignment": round(aligned_gaps / n_gaps, 4),
        "aligned_gaps": aligned_gaps,
        "gaps": len(gaps),
        "evidence_boilerplate_rate": round(boilerplate / n_spans, 4),
        "boilerplate_spans": boilerplate,
        "evidence_spans": len(spans),
        "provenance_coverage": round(with_prov / n_spans, 4),
        "provenance_spans": with_prov,
        "extraction_topic_rate": (
            round(ext_topic / max(1, len(extractions or [])), 4) if extractions is not None else None
        ),
        "targets": {
            "topic_hit_rate": 0.7,
            "gap_material_alignment": 0.8,
            "evidence_boilerplate_rate_max": 0.05,
            "provenance_coverage": 0.95,
        },
        "pass_flags": {
            "topic_hit_rate": (topic_hits / n_papers) >= 0.7 if mats else True,
            "gap_material_alignment": (aligned_gaps / n_gaps) >= 0.8 if mats else True,
            "evidence_boilerplate_rate": (boilerplate / n_spans) <= 0.05,
            "provenance_coverage": (with_prov / n_spans) >= 0.95,
        },
    }
