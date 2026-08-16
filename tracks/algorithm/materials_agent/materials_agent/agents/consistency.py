from __future__ import annotations

import re

from materials_agent.agents.evidence import quote_in_source
from materials_agent.config import QualityConfig
from materials_agent.models import (
    AuditEvent,
    ConsistencyIssue,
    ConsistencyReport,
    ExtractedRecord,
    Paper,
    ResearchGap,
)


_ID_RE = re.compile(r"`([A-Za-z0-9._:-]+)`")


def check_consistency(
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    gaps: list[ResearchGap],
    report_markdown: str,
    audit: list[AuditEvent],
    quality: QualityConfig | None = None,
) -> ConsistencyReport:
    paper_ids = {p.id for p in papers}
    issues: list[ConsistencyIssue] = []

    ext_ids = {e.paper_id for e in extractions}
    for pid in ext_ids - paper_ids:
        issues.append(
            ConsistencyIssue(kind="extraction_unknown_paper", detail=pid, severity="error")
        )
    for p in papers:
        if p.id not in ext_ids:
            issues.append(
                ConsistencyIssue(
                    kind="paper_missing_extraction",
                    detail=p.id,
                    severity="warn",
                )
            )

    quality = quality or QualityConfig()
    paper_by_id = {paper.id: paper for paper in papers}
    for g in gaps:
        for pid in g.supporting_paper_ids + g.contradicting_paper_ids:
            if pid not in paper_ids and pid != "corpus":
                issues.append(
                    ConsistencyIssue(
                        kind="gap_unknown_paper",
                        detail=f"{g.id}:{pid}",
                        severity="error",
                    )
                )
        for ev in g.evidence_chain:
            if ev.paper_id not in paper_ids and ev.paper_id != "corpus":
                issues.append(
                    ConsistencyIssue(
                        kind="gap_evidence_unknown_paper",
                        detail=f"{g.id}:{ev.paper_id}",
                        severity="error",
                    )
                )
                continue
            paper = paper_by_id.get(ev.paper_id)
            if paper and quality.require_quote_substring:
                source = paper.full_text or paper.abstract or paper.title
                if not quote_in_source(ev.quote_or_basis, source, ev.provenance):
                    issues.append(
                        ConsistencyIssue(
                            kind="evidence_quote_not_in_source",
                            detail=f"{g.id}:{ev.paper_id}",
                            severity="error",
                        )
                    )
            if (
                quality.reject_evidence_without_provenance
                and ev.location in {"fulltext", "chunk"}
                and not ev.provenance
            ):
                issues.append(
                    ConsistencyIssue(
                        kind="gap_evidence_missing_provenance",
                        detail=f"{g.id}:{ev.paper_id}",
                        severity="error",
                    )
                )
        if not g.evidence_chain:
            issues.append(
                ConsistencyIssue(kind="gap_no_evidence", detail=g.id, severity="error")
            )
        if not (g.suggested_next_step or "").strip():
            issues.append(
                ConsistencyIssue(kind="gap_no_next_step", detail=g.id, severity="error")
            )

        if quality.require_fulltext_gap_evidence and any(
            paper_by_id.get(pid) and paper_by_id[pid].full_text
            for pid in g.supporting_paper_ids
        ):
            if not any(ev.location in {"fulltext", "chunk"} for ev in g.evidence_chain):
                issues.append(
                    ConsistencyIssue(
                        kind="gap_missing_fulltext_evidence",
                        detail=g.id,
                        severity="error",
                    )
                )

    # IDs mentioned in report backticks should mostly exist
    mentioned = set(_ID_RE.findall(report_markdown or ""))
    noise = {"ZT", "DFT", "MD", "RAG", "OA", "ID", "DOI"}
    for mid in mentioned:
        if mid in noise or mid.startswith("gap-"):
            continue
        if mid.startswith("LOCAL-") or mid.startswith("W") or "-" in mid:
            if mid not in paper_ids and not mid.startswith("gap"):
                # only flag paper-like tokens present in papers namespace mismatch
                if any(mid == p.id for p in papers):
                    continue
                if mid in paper_ids:
                    continue
                # soft: ignore pure English words
                if re.fullmatch(r"[A-Za-z]{1,6}", mid):
                    continue
                if mid not in paper_ids:
                    issues.append(
                        ConsistencyIssue(
                            kind="report_unknown_id",
                            detail=mid,
                            severity="warn",
                        )
                    )

    errors = [i for i in issues if i.severity == "error"]
    report = ConsistencyReport(ok=len(errors) == 0, issues=issues)
    audit.append(
        AuditEvent(
            step="check_consistency",
            tool="validator",
            input_summary=f"papers={len(papers)} gaps={len(gaps)}",
            output_summary=f"ok={report.ok} issues={len(issues)} errors={len(errors)}",
            meta={"issues": [i.model_dump() for i in issues[:50]]},
        )
    )
    return report
