from __future__ import annotations

import re

from materials_agent.agents.evidence import make_evidence, parse_confidence
from materials_agent.agents.evidence_selector import ground_gap_evidence
from materials_agent.config import EvidenceRetrievalConfig, QualityConfig
from materials_agent.limitation_quality import is_strong_limitation, strip_leading_citations
from materials_agent.llm import LLMClient
from materials_agent.models import (
    AuditEvent,
    EvidenceSpan,
    ExtractedRecord,
    KnownPair,
    Paper,
    ResearchGap,
)
from materials_agent.tools.index.base import EvidenceIndex
from materials_agent.topic_focus import extract_topic_materials, paper_mentions_materials

_VALID_TYPES = {"missing_link", "contradiction", "underexplored", "method_gap"}
_CONFLICT_CUES = (
    "conflict",
    "contradict",
    "conflicting",
    "others report",
    "unresolved",
)
_DEBATE_CUES = (
    "debated",
    "debate",
    "remain debated",
)


def _paper_slug(paper_id: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "", paper_id)
    return (slug[-24:] if slug else "paper")


def _topic_prop_bits(topic: str) -> tuple[str, ...]:
    low = (topic or "").lower()
    bits = (
        "thermal",
        "conductivity",
        "phonon",
        "zt",
        "grain",
        "boundary",
        "vacanc",
        "scatter",
        "anisotropic",
        "lattice",
    )
    return tuple(b for b in bits if b in low) or bits


def _ensure_next_step(text: str, title: str) -> str:
    t = (text or "").strip()
    if len(t) >= 20 and "more research" not in t.lower():
        return t
    return (
        f"Propose one falsifiable experiment or Materials Project/OQMD check that would "
        f"confirm or reject: {title[:120]}"
    )


def _ev_for(
    paper_by_id: dict[str, Paper],
    pids: list[str],
    claim: str,
    quality: QualityConfig,
) -> list[EvidenceSpan]:
    out: list[EvidenceSpan] = []
    for pid in pids[:4]:
        p = paper_by_id.get(pid)
        if not p:
            continue
        ev = make_evidence(
            pid,
            claim,
            (p.abstract or p.title)[:240],
            0.5,
            "abstract" if p.abstract else "title",
            quality.min_quote_chars,
        )
        if ev:
            out.append(ev)
    return out


def _topic_materials(topic: str, extractions: list[ExtractedRecord]) -> list[str]:
    mats = []
    low = topic.lower()
    for e in extractions:
        for m in e.materials:
            if m.lower() in low:
                mats.append(m)
    mats.extend(extract_topic_materials(topic))
    if mats:
        return list(dict.fromkeys(mats))
    # Do not promote corpus-frequency siblings (PbTe/GeTe) when topic already
    # names a material; extract_topic_materials would have returned it.
    from collections import Counter

    c = Counter(m for e in extractions for m in e.materials)
    return [m for m, _ in c.most_common(2)]


def _heuristic_gaps(
    topic: str,
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    known: list[KnownPair],
    quality: QualityConfig,
) -> list[ResearchGap]:
    gaps: list[ResearchGap] = []
    paper_by_id = {p.id: p for p in papers}
    ext_by_id = {e.paper_id: e for e in extractions}
    known_keys = {(k.material.lower(), k.property.lower()) for k in known}
    topic_mats = _topic_materials(topic, extractions)

    # 1) Explicit within-paper conflict cues → underexplored (not cross-paper contradiction)
    for p in papers:
        if topic_mats and not paper_mentions_materials(p, topic_mats):
            continue
        blob = f"{p.title}. {p.abstract or ''}".lower()
        # Avoid COI / boilerplate "conflict of interest"
        if "conflict of interest" in blob or "competing interest" in blob:
            blob_for_cues = blob.replace("conflict of interest", " ").replace(
                "competing interest", " "
            )
        else:
            blob_for_cues = blob
        if any(c in blob_for_cues for c in _CONFLICT_CUES):
            title = f"Unresolved conflicting claims in `{p.id}`"
            gaps.append(
                ResearchGap(
                    id=f"gap-conflict-{p.id}",
                    title=title,
                    description=(
                        f"Paper `{p.id}` explicitly signals conflicting/opposing conclusions. "
                        "Treat as underexplored until two opposing claims are isolated across "
                        "independent sources or protocols."
                    ),
                    gap_type="underexplored",
                    novelty=0.62,
                    actionability=0.7,
                    supporting_paper_ids=[p.id],
                    contradicting_paper_ids=[],
                    evidence_chain=_ev_for(paper_by_id, [p.id], "explicit conflict cue", quality),
                    suggested_next_step=(
                        "Extract the two opposing claims, define a common measurement protocol, "
                        "and test which claim holds on a held-out sample/condition."
                    ),
                    falsification_test=(
                        "If both claims become consistent under a shared protocol and error bars, "
                        "reject the contradiction framing."
                    ),
                )
            )
        elif any(c in blob_for_cues for c in _DEBATE_CUES):
            title = f"Mechanism still debated in `{p.id}`"
            gaps.append(
                ResearchGap(
                    id=f"gap-debate-{p.id}",
                    title=title,
                    description=(
                        f"Paper `{p.id}` marks a mechanism as debated rather than settled. "
                        "Treat as underexplored until opposing quantitative claims are isolated."
                    ),
                    gap_type="underexplored",
                    novelty=0.52,
                    actionability=0.65,
                    supporting_paper_ids=[p.id],
                    evidence_chain=_ev_for(paper_by_id, [p.id], "debate cue", quality),
                    suggested_next_step=(
                        "List candidate mechanisms mentioned as debated and design one discriminating measurement."
                    ),
                    falsification_test=(
                        "If subsequent consensus literature resolves the debate, close this gap."
                    ),
                )
            )

    # 2) Concrete open issues from strong limitation sentences (topic-aligned)
    # Do NOT emit a meta "N papers contain limitations" bag — that fails G1.
    prop_bits = _topic_prop_bits(topic)
    open_items: list[tuple[str, str]] = []
    for e in extractions:
        paper = paper_by_id.get(e.paper_id)
        if not paper:
            continue
        if topic_mats and not paper_mentions_materials(paper, topic_mats):
            continue
        for lim in e.limitations:
            quote = (lim or "").strip()
            if len(quote) < quality.min_quote_chars:
                continue
            if not is_strong_limitation(quote):
                continue
            low = quote.lower()
            if topic_mats and not any(m.lower() in low for m in topic_mats):
                if not any(b in low for b in prop_bits):
                    continue
            open_items.append((e.paper_id, quote))

    seen_keys: list[str] = []
    unique_open: list[tuple[str, str]] = []
    for pid, quote in open_items:
        key = quote[:90].lower()
        if any(key in prev or prev in key for prev in seen_keys):
            continue
        seen_keys.append(key)
        unique_open.append((pid, quote))

    # Prefer open issues that mention topic properties (science-review S2).
    unique_open.sort(
        key=lambda item: (
            0 if any(b in item[1].lower() for b in prop_bits) else 1,
            0 if topic_mats and any(m.lower() in item[1].lower() for m in topic_mats) else 1,
        )
    )

    for i, (pid, quote) in enumerate(unique_open[:3]):
        clean = strip_leading_citations(quote)
        short = clean if len(clean) <= 110 else clean[:107].rsplit(" ", 1)[0] + "…"
        title = f"Unresolved: {short}"
        # Prefer property-linked open issues when topic names properties (science S2).
        if prop_bits and not any(b in clean.lower() for b in prop_bits):
            # Keep if materials named; otherwise skip weak descriptive leftovers.
            if topic_mats and not any(m.lower() in clean.lower() for m in topic_mats):
                continue
            if not is_strong_limitation(clean):
                continue
        ev = make_evidence(
            pid,
            "limitation sentence",
            quote[:500],
            0.65,
            "fulltext",
            quality.min_quote_chars,
        )
        gaps.append(
            ResearchGap(
                id=f"gap-open-{_paper_slug(pid)}-{i}",
                title=title,
                description=(
                    f"Paper `{pid}` signals an open scientific limitation rather than a "
                    f"settled conclusion: {clean[:450]}"
                ),
                gap_type="underexplored",
                novelty=0.58,
                actionability=0.74,
                supporting_paper_ids=[pid],
                evidence_chain=[ev] if ev else [],
                suggested_next_step=(
                    "Design one discriminating measurement or computation that would resolve "
                    "the quoted open issue on the topic material/condition set."
                ),
                falsification_test=(
                    "If a controlled follow-up shows the quoted limitation no longer holds "
                    "under the same conditions, close this gap."
                ),
            )
        )

    # 3) Method gap: computation/ML without experimental closure on same paper
    method_gap_ids = []
    for e in extractions:
        methods_l = " ".join(e.methods).lower()
        has_comp = any(x in methods_l for x in ("dft", "machine learning", "molecular dynamics"))
        has_exp = any(
            x in methods_l for x in ("xrd", "sem", "tem", "synthesis", "spark plasma", "experiment")
        )
        # also look at abstract
        abs_l = (paper_by_id.get(e.paper_id).abstract or "").lower() if e.paper_id in paper_by_id else ""
        abs_exp = any(
            x in abs_l for x in ("experiment", "synthes", "sinter", "measured", "fabrication")
        )
        if has_comp and not (has_exp or abs_exp):
            method_gap_ids.append(e.paper_id)
        # explicit "not fully integrated" style method gap
        if "not fully" in abs_l or "method gap" in abs_l or "leaving a method" in abs_l:
            method_gap_ids.append(e.paper_id)
    method_gap_ids = list(dict.fromkeys(method_gap_ids))
    if method_gap_ids:
        title = "Computation/ML conclusions lack experimental or process closure"
        gaps.append(
            ResearchGap(
                id="gap-method-balance",
                title=title,
                description=(
                    "Several papers emphasize DFT/ML predictions while synthesis constraints, "
                    "phase stability, or experimental validation remain thin or explicitly missing."
                ),
                gap_type="method_gap",
                novelty=0.58,
                actionability=0.78,
                supporting_paper_ids=method_gap_ids[:8],
                evidence_chain=_ev_for(paper_by_id, method_gap_ids, "method imbalance", quality),
                suggested_next_step=(
                    "Pick one predicted candidate and require a minimal experimental/process check "
                    "(synthesis feasibility or database phase-stability filter) before claiming discovery."
                ),
                falsification_test=(
                    "If re-screening with experimental filters removes the imbalance, treat as retrieval bias."
                ),
            )
        )

    # 4) Topic-material missing links: properties discussed corpus-wide but not for topic material
    # topic_mats already computed above
    if topic_mats:
        topic_mat = topic_mats[0]
        props_on_topic = {
            p for e in extractions if topic_mat in e.materials for p in e.properties
        }
        props_elsewhere = {
            p for e in extractions if topic_mat not in e.materials for p in e.properties
        }
        missing = sorted(props_elsewhere - props_on_topic)
        # remove known dense pairs
        missing = [
            p
            for p in missing
            if (topic_mat.lower(), p.lower()) not in known_keys
        ]
        if missing:
            support = [e.paper_id for e in extractions if topic_mat in e.materials][:6]
            title = f"Missing property coverage for topic material {topic_mat}"
            gaps.append(
                ResearchGap(
                    id="gap-missing-link-topic",
                    title=title,
                    description=(
                        f"Within this corpus, {topic_mat} is not linked to properties that appear "
                        f"elsewhere: {', '.join(missing[:8])}. This is a candidate missing_link, "
                        "not a claim that the broader literature lacks these links."
                    ),
                    gap_type="missing_link",
                    novelty=0.6,
                    actionability=0.7,
                    supporting_paper_ids=support,
                    evidence_chain=_ev_for(paper_by_id, support, "topic material anchor", quality),
                    suggested_next_step=(
                        f"Test whether {topic_mat}–{missing[0]} linkage is supported in Materials Project/"
                        "OQMD or a targeted experiment; if yes, mark as known and remove from candidate-new."
                    ),
                    falsification_test=(
                        f"If curated databases already densely cover {topic_mat}–{missing[0]}, "
                        "reject novelty of this missing-link gap."
                    ),
                )
            )

    # 5) Same-system temporal contradiction only for TOPIC materials
    years = [p.year for p in papers if p.year]
    if years and max(years) - min(years) >= 3:
        temporal_mats = topic_mats or []
        for mat in temporal_mats:
            early = [
                p
                for p in papers
                if p.year
                and p.year <= min(years) + 1
                and mat in (ext_by_id.get(p.id).materials if ext_by_id.get(p.id) else [])
            ]
            recent = [
                p
                for p in papers
                if p.year
                and p.year >= max(years) - 1
                and mat in (ext_by_id.get(p.id).materials if ext_by_id.get(p.id) else [])
            ]
            if early and recent:
                support_ids = [p.id for p in recent[:3]]
                contradict_ids = [p.id for p in early[:3]]
                # Require disjoint paper sets for cross-era contradiction claims.
                if set(support_ids) & set(contradict_ids):
                    continue
                if not support_ids or not contradict_ids:
                    continue
                title = f"Candidate temporal tension for {mat} across {min(years)}–{max(years)} (corpus-scoped)"
                gaps.append(
                    ResearchGap(
                        id=f"gap-temporal-{re.sub(r'[^A-Za-z0-9]+', '', mat)[:12]}",
                        title=title,
                        description=(
                            f"Both early and recent papers discuss {mat}. Compare mechanisms/metrics "
                            "before asserting a narrative shift; only retain if claims conflict "
                            "under normalized conditions within this screened corpus."
                        ),
                        gap_type="contradiction",
                        novelty=0.5,
                        actionability=0.55,
                        supporting_paper_ids=support_ids,
                        contradicting_paper_ids=contradict_ids,
                        evidence_chain=_ev_for(
                            paper_by_id,
                            support_ids[:2] + contradict_ids[:2],
                            "same-material temporal pair",
                            quality,
                        ),
                        suggested_next_step=(
                            f"Build a claim table for {mat} (metric, condition, conclusion) across eras "
                            "and keep only rows that disagree."
                        ),
                        falsification_test=(
                            f"If early/recent {mat} claims agree under normalized conditions, reject contradiction."
                        ),
                    )
                )

    # annotate known overlap
    for g in gaps:
        blob = f"{g.title} {g.description}".lower()
        g.overlaps_known = any(m in blob and p in blob for m, p in known_keys)

    if not gaps:
        title = f"Need deeper causal structure-property mapping for {topic}"
        gaps.append(
            ResearchGap(
                id="gap-default",
                title=title,
                description=(
                    "Screening yields descriptive correlations but insufficient mechanism-level links."
                ),
                gap_type="underexplored",
                novelty=0.45,
                actionability=0.55,
                supporting_paper_ids=[p.id for p in papers[:5]],
                evidence_chain=_ev_for(paper_by_id, [p.id for p in papers[:3]], "default", quality),
                suggested_next_step=_ensure_next_step("", title),
                falsification_test="If Route A cannot produce a checkable SPR, narrow the topic.",
            )
        )
    return gaps


def identify_gaps(
    topic: str,
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    known: list[KnownPair],
    llm: LLMClient,
    quality: QualityConfig,
    audit: list[AuditEvent],
    evidence_index: EvidenceIndex | None = None,
    evidence_retrieval: EvidenceRetrievalConfig | None = None,
) -> list[ResearchGap]:
    # Always compute heuristic gaps as a high-precision base; LLM can add more.
    gaps = _heuristic_gaps(topic, papers, extractions, known, quality)
    paper_ids = {p.id for p in papers}

    if llm.enabled:
        paper_briefs = []
        for p, e in zip(papers, extractions):
            paper_briefs.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "year": p.year,
                    "materials": e.materials,
                    "properties": e.properties,
                    "methods": e.methods,
                    "findings": e.key_findings[:2],
                    "limitations": e.limitations[:2],
                }
            )
        known_brief = [f"{k.material}|{k.property}|n={k.count}" for k in known[:12]]
        payload = llm.chat_json(
            system=(
                "You are a senior materials scientist identifying Research Gaps. "
                "Do NOT invent temporal contradictions across unrelated materials. "
                "Prefer explicit conflict cues, strong open-issue limitation sentences "
                "(remain/unclear/still low/challenge — not positive 'however' results), "
                "and method gaps. "
                "Never propose a meta gap that only counts how many papers contain limitations; "
                "each underexplored gap must state a concrete physical open question. "
                "Each gap MUST include suggested_next_step and falsification_test. "
                "gap_type in [missing_link, contradiction, underexplored, method_gap]. "
                "Return JSON {\"gaps\":[...]}."
            ),
            user=f"Topic: {topic}\nKnown pairs: {known_brief}\nPapers:\n{paper_briefs}",
            step="gap",
            validator=lambda d: isinstance(d.get("gaps"), list),
        )
        if payload:
            existing_ids = {g.id for g in gaps}
            for i, g in enumerate(payload["gaps"]):
                gtype = str(g.get("gap_type") or "underexplored")
                if gtype not in _VALID_TYPES:
                    gtype = "underexplored"
                supports = [x for x in list(g.get("supporting_paper_ids") or []) if x in paper_ids]
                contrad = [x for x in list(g.get("contradicting_paper_ids") or []) if x in paper_ids]
                evidence_chain: list[EvidenceSpan] = []
                for item in g.get("evidence") or []:
                    if not isinstance(item, dict):
                        continue
                    pid = str(item.get("paper_id") or "")
                    if pid not in paper_ids:
                        continue
                    try:
                        evidence_chain.append(
                            EvidenceSpan(
                                paper_id=pid,
                                claim=str(item.get("claim") or "support"),
                                quote_or_basis=str(item.get("quote_or_basis") or "see abstract")[:500],
                                confidence=parse_confidence(item.get("confidence"), 0.6),
                                location="abstract",
                            )
                        )
                    except Exception:
                        continue
                title = str(g.get("title") or "Untitled gap")
                gid = str(g.get("id") or f"gap-llm-{i+1}")
                if gid in existing_ids:
                    continue
                gaps.append(
                    ResearchGap(
                        id=gid,
                        title=title,
                        description=str(g.get("description") or ""),
                        gap_type=gtype,  # type: ignore[arg-type]
                        novelty=parse_confidence(g.get("novelty"), 0.5),
                        actionability=parse_confidence(g.get("actionability"), 0.5),
                        supporting_paper_ids=supports,
                        contradicting_paper_ids=contrad,
                        evidence_chain=evidence_chain,
                        suggested_next_step=_ensure_next_step(
                            str(g.get("suggested_next_step") or ""), title
                        ),
                        falsification_test=str(g.get("falsification_test") or "")
                        or "Reject if the proposed check fails to distinguish from known pairs.",
                    )
                )

    gaps = ground_gap_evidence(
        gaps,
        papers,
        evidence_index,
        evidence_retrieval or EvidenceRetrievalConfig(),
        quality,
        audit,
        extractions=extractions,
    )
    audit.append(
        AuditEvent(
            step="identify_gaps",
            tool="heuristic+llm" if llm.enabled else "heuristic",
            input_summary=topic,
            output_summary=f"{len(gaps)} gaps",
            meta={"types": [g.gap_type for g in gaps]},
        )
    )
    return gaps
