from __future__ import annotations

from materials_agent.agents.evidence import parse_confidence
from materials_agent.config import QualityConfig
from materials_agent.llm import LLMClient
from materials_agent.models import (
    AuditEvent,
    EvidenceSpan,
    KnownPair,
    Paper,
    ResearchGap,
)
from materials_agent.topic_focus import extract_topic_materials, gap_aligned_to_topic


_VALID_TYPES = {"missing_link", "contradiction", "underexplored", "method_gap"}
_VAGUE = (
    "paradigm shift",
    "possible paradigm",
    "more research",
    "further study",
    "in general",
)


def _heuristic_review(
    gaps: list[ResearchGap],
    papers: list[Paper],
    known: list[KnownPair],
    quality: QualityConfig,
    topic: str = "",
) -> list[ResearchGap]:
    paper_ids = {p.id for p in papers}
    paper_by_id = {p.id: p for p in papers}
    known_keys = {(k.material.lower(), k.property.lower()) for k in known}
    topic_mats = extract_topic_materials(topic) if topic else []
    out: list[ResearchGap] = []

    for g in gaps:
        notes: list[str] = []
        status = "accepted"
        blob = f"{g.title} {g.description}".lower()

        if g.gap_type not in _VALID_TYPES:
            g.gap_type = "underexplored"
            notes.append("normalized invalid gap_type")

        g.supporting_paper_ids = [x for x in g.supporting_paper_ids if x in paper_ids]
        g.contradicting_paper_ids = [x for x in g.contradicting_paper_ids if x in paper_ids]

        if topic_mats and (
            g.id.startswith("gap-temporal-")
            or g.id.startswith("gap-conflict-")
            or g.id.startswith("gap-open-")
            or g.gap_type == "contradiction"
        ):
            if not gap_aligned_to_topic(g, topic_mats):
                status = "rejected"
                notes.append("off-topic material vs survey topic")

        # Reject legacy meta limitation bags (corpus counting, not falsifiable science)
        if g.id == "gap-limitations" or "open limitations repeatedly signaled" in blob:
            status = "rejected"
            notes.append("meta corpus-limitation bag (not a falsifiable science gap)")

        # Align supporting IDs to evidenced papers for non-contradiction gaps
        if g.evidence_chain and g.gap_type != "contradiction" and status != "rejected":
            evid_ids = list(
                dict.fromkeys(span.paper_id for span in g.evidence_chain if span.paper_id in paper_ids)
            )
            if evid_ids:
                kept = [pid for pid in g.supporting_paper_ids if pid in evid_ids]
                if kept != g.supporting_paper_ids:
                    notes.append("supporting papers trimmed to evidenced ids")
                g.supporting_paper_ids = kept or evid_ids

        # Reject vague temporal contradictions that do not share a material token
        if g.gap_type == "contradiction" and "temporal" in g.id:
            mats_support = set()
            mats_contra = set()
            # weak check via title tokens overlapping paper titles
            for pid in g.supporting_paper_ids:
                mats_support |= set((paper_by_id[pid].title or "").lower().split())
            for pid in g.contradicting_paper_ids:
                mats_contra |= set((paper_by_id[pid].title or "").lower().split())
            # require chemical-like token intersection or explicit material in title
            chem = {t for t in mats_support & mats_contra if any(c.isdigit() for c in t) or t in {"snse", "pbte", "bi2te3", "mg3sb2"}}
            if not chem and "same-material" not in blob and "for " not in g.title.lower():
                status = "rejected"
                notes.append("temporal contradiction without shared material system")

        if any(v in blob for v in _VAGUE) and g.gap_type == "contradiction" and "conflict" not in blob:
            if "unresolved conflicting" not in blob and "conflicting claims" not in blob:
                g.novelty = min(g.novelty, 0.45)
                notes.append("vague contradiction wording; novelty capped")

        if g.gap_type == "contradiction":
            if not g.contradicting_paper_ids and not g.supporting_paper_ids:
                status = "rejected"
                notes.append("contradiction without papers")
            elif not g.contradicting_paper_ids and len(g.supporting_paper_ids) >= 1:
                # within-paper contradiction: allow same id on both sides
                g.contradicting_paper_ids = list(g.supporting_paper_ids)
                notes.append("within-paper contradiction mirrored to both sides")

        if not g.evidence_chain and quality.drop_gaps_without_evidence:
            if quality.require_fulltext_gap_evidence:
                status = "rejected"
                notes.append("no fulltext evidence chain")
                g.review_status = status
                g.review_notes = "; ".join(notes)
                continue
            for pid in (g.supporting_paper_ids + g.contradicting_paper_ids)[:2]:
                p = paper_by_id.get(pid)
                if p:
                    source = p.full_text or p.abstract or p.title
                    g.evidence_chain.append(
                        EvidenceSpan(
                            paper_id=pid,
                            claim="support anchor",
                            quote_or_basis=source[:240],
                            confidence=0.35,
                            location="fulltext" if p.full_text else ("abstract" if p.abstract else "title"),
                        )
                    )
            if not g.evidence_chain:
                status = "rejected"
                notes.append("no evidence chain")

        if quality.require_next_step and not (g.suggested_next_step or "").strip():
            g.suggested_next_step = (
                f"Design a falsifiable check for '{g.title[:80]}' via database lookup "
                "or a controlled experiment/computation."
            )
            notes.append("auto-filled next step")

        if quality.require_falsification and not (g.falsification_test or "").strip():
            g.falsification_test = (
                "If the predicted link fails under the proposed protocol on held-out conditions, "
                "reject this gap hypothesis."
            )
            notes.append("auto-filled falsification test")

        g.overlaps_known = any(m in blob and p in blob for m, p in known_keys)
        if g.overlaps_known and g.novelty > 0.7:
            g.novelty = min(g.novelty, 0.55)
            notes.append("novelty capped due to known dense region")

        if g.actionability < quality.min_gap_actionability and status == "accepted":
            status = "revised"
            notes.append("low actionability")
            g.actionability = max(g.actionability, quality.min_gap_actionability)

        if status == "rejected":
            g.review_status = "rejected"
            g.review_notes = "; ".join(notes)
            continue

        g.review_status = status
        g.review_notes = "; ".join(notes)
        out.append(g)

    # Prefer higher-actionability / explicit-conflict gaps first
    out.sort(key=lambda x: (x.actionability + x.novelty, x.id), reverse=True)
    return out[:8]


def review_gaps(
    gaps: list[ResearchGap],
    papers: list[Paper],
    known: list[KnownPair],
    llm: LLMClient,
    quality: QualityConfig,
    audit: list[AuditEvent],
    topic: str = "",
) -> list[ResearchGap]:
    reviewed = _heuristic_review(gaps, papers, known, quality, topic=topic)
    rejected_ids = [g.id for g in gaps if g.review_status == "rejected"]

    if llm.enabled and gaps:
        payload = llm.chat_json(
            system=(
                "You are a critical materials-science reviewer. "
                "Reject vague temporal contradictions across unrelated materials. "
                "Reject gaps about materials not named in the survey topic. "
                "Reject meta bags that only count limitation sentences without a concrete "
                "physical open question. "
                "Keep explicit conflict/open-issue/method gaps on the topic material. "
                "Return JSON {\"decisions\":[{\"id\",\"status\":\"accepted|revised|rejected\","
                "\"notes\",\"gap_type\",\"suggested_next_step\",\"falsification_test\","
                "\"novelty\",\"actionability\"}]}."
            ),
            user=str(
                [
                    {
                        "id": g.id,
                        "title": g.title,
                        "type": g.gap_type,
                        "description": g.description[:300],
                        "supports": g.supporting_paper_ids,
                        "contradicts": g.contradicting_paper_ids,
                        "next": g.suggested_next_step,
                    }
                    for g in reviewed
                ]
            ),
            step="review",
            validator=lambda d: isinstance(d.get("decisions"), list),
        )
        if payload:
            by_id = {g.id: g for g in reviewed}
            kept: list[ResearchGap] = []
            for d in payload["decisions"]:
                gid = str(d.get("id") or "")
                g = by_id.get(gid)
                if not g:
                    continue
                status = str(d.get("status") or g.review_status)
                if status == "rejected":
                    g.review_status = "rejected"
                    g.review_notes = str(d.get("notes") or "llm rejected")
                    rejected_ids.append(g.id)
                    continue
                if d.get("gap_type") in _VALID_TYPES:
                    g.gap_type = d["gap_type"]
                if d.get("suggested_next_step"):
                    g.suggested_next_step = str(d["suggested_next_step"])
                if d.get("falsification_test"):
                    g.falsification_test = str(d["falsification_test"])
                if d.get("novelty") is not None:
                    g.novelty = parse_confidence(d["novelty"], g.novelty)
                if d.get("actionability") is not None:
                    g.actionability = parse_confidence(d["actionability"], g.actionability)
                g.review_status = status
                g.review_notes = (g.review_notes + "; " + str(d.get("notes") or "")).strip("; ")
                kept.append(g)
            if kept:
                reviewed = kept

    audit.append(
        AuditEvent(
            step="review_gaps",
            tool="llm+rules" if llm.enabled else "rules",
            input_summary=f"{len(gaps)} gaps in",
            output_summary=f"{len(reviewed)} kept; rejected={len(set(rejected_ids))}",
            meta={"accepted": [g.id for g in reviewed], "rejected": list(set(rejected_ids))},
        )
    )
    return reviewed
