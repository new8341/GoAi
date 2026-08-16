from __future__ import annotations

from datetime import datetime, timezone

from materials_agent.evidence_attribution import gap_databases_summary
from materials_agent.llm import LLMClient
from materials_agent.models import (
    AuditEvent,
    ConsistencyReport,
    ExtractedRecord,
    KnownPair,
    Paper,
    ResearchGap,
)


def _render_heuristic_report(
    topic: str,
    subfield: str,
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    gaps: list[ResearchGap],
    known: list[KnownPair],
    query_variants: list[str],
    consistency: ConsistencyReport | None,
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        f"# Literature Survey Report: {topic}",
        "",
        f"- Subfield: **{subfield}**",
        f"- Generated: {now}",
        f"- Papers screened: **{len(papers)}**",
        f"- Research Gaps: **{len(gaps)}**",
        f"- Known dense pairs: **{len(known)}**",
        "",
        "## 1. Scope and method",
        "",
        "Pipeline: query rewrite → multi-query retrieve → evidence-grounded extract → "
        "gap identify → gap review → consistency check → report.",
        "",
        "### Query variants",
        "",
    ]
    for q in query_variants:
        lines.append(f"- {q}")

    lines += [
        "",
        "## 2. Screened literature",
        "",
        "| ID | Year | Rel. | Cited | Database | Title | DOI |",
        "|----|------|------|-------|----------|-------|-----|",
    ]
    for p in papers:
        title = p.title.replace("|", "/")
        db = (p.source or "unknown").replace("|", "/")
        lines.append(
            f"| `{p.id}` | {p.year or '-'} | {p.relevance_score:.2f} | {p.cited_by} | "
            f"`{db}` | {title} | {p.doi or '-'} |"
        )

    lines += ["", "## 3. Known dense regions (not claimed as novel Gaps)", ""]
    if known:
        lines += [
            "| Material | Property | Count | Paper IDs |",
            "|----------|----------|-------|-----------|",
        ]
        for k in known[:20]:
            ids = ", ".join(f"`{x}`" for x in k.paper_ids[:6])
            lines.append(f"| {k.material} | {k.property} | {k.count} | {ids} |")
    else:
        lines.append("_No frequent material-property pairs above threshold._")

    lines += ["", "## 4. Structured knowledge extractions", ""]
    for e in extractions:
        lines.append(f"### `{e.paper_id}` (confidence={e.extraction_confidence:.2f})")
        lines.append(f"- Materials: {', '.join(e.materials) or '—'}")
        lines.append(f"- Properties: {', '.join(e.properties) or '—'}")
        lines.append(f"- Methods: {', '.join(e.methods) or '—'}")
        lines.append(f"- Synthesis: {', '.join(e.synthesis) or '—'}")
        if e.key_findings:
            lines.append("- Key findings:")
            for f in e.key_findings:
                lines.append(f"  - {f}")
        if e.limitations:
            lines.append("- Limitations:")
            for lim in e.limitations:
                lines.append(f"  - {lim}")
        lines.append("- Evidence:")
        for ev in e.evidence:
            provenance = ""
            if ev.provenance:
                provenance = (
                    f" [chunk={ev.provenance.chunk_id or '-'} "
                    f"section={ev.provenance.section or '-'}]"
                )
            db = ev.retrieval_database or "unknown"
            lines.append(
                f"  - Database: `{db}` ({ev.location}, conf={ev.confidence:.2f}){provenance} "
                f"{ev.quote_or_basis[:180]}"
            )
        if e.dropped_fields:
            lines.append(f"- Dropped ungrounded fields: {len(e.dropped_fields)}")
        lines.append("")

    lines += ["## 5. Research Gap inventory", ""]
    for g in gaps:
        dbs = gap_databases_summary(g)
        db_note = ", ".join(f"`{d}`" for d in dbs) if dbs else "`unknown`"
        lines.append(f"### `{g.id}`: {g.title}")
        lines.append(f"- Type: `{g.gap_type}` | Review: `{g.review_status}`")
        lines.append(f"- Databases used: {db_note}")
        lines.append(
            f"- Novelty: {g.novelty:.2f} | Actionability: {g.actionability:.2f} | "
            f"Overlaps known: {g.overlaps_known}"
        )
        lines.append(f"- Description: {g.description}")
        lines.append(
            f"- Supporting: {', '.join(f'`{x}`' for x in g.supporting_paper_ids) or '—'}"
        )
        lines.append(
            f"- Contradicting: {', '.join(f'`{x}`' for x in g.contradicting_paper_ids) or '—'}"
        )
        lines.append(f"- Suggested next step: {g.suggested_next_step}")
        lines.append(f"- Falsification test: {g.falsification_test}")
        lines.append("- Evidence chain:")
        for ev in g.evidence_chain:
            provenance = ""
            if ev.provenance:
                provenance = (
                    f" page={ev.provenance.page or '-'} section={ev.provenance.section or '-'} "
                    f"chunk={ev.provenance.chunk_id or '-'} "
                    f"offset={ev.provenance.char_start}-{ev.provenance.char_end}"
                )
            db = ev.retrieval_database or "unknown"
            lines.append(
                f"  - Database: `{db}` | `{ev.paper_id}` — {ev.claim} "
                f"(conf={ev.confidence:.2f};{provenance}): "
                f"{ev.quote_or_basis[:180]}"
            )
        if g.review_notes:
            lines.append(f"- Review notes: {g.review_notes}")
        lines.append("")

    lines += [
        "## 6. Cross-reference matrix (Gap × Paper)",
        "",
        "| Gap | Supporting | Contradicting |",
        "|-----|------------|---------------|",
    ]
    for g in gaps:
        s = ", ".join(f"`{x}`" for x in g.supporting_paper_ids[:8]) or "—"
        c = ", ".join(f"`{x}`" for x in g.contradicting_paper_ids[:8]) or "—"
        lines.append(f"| `{g.id}` | {s} | {c} |")

    lines += [
        "",
        "## 7. Known vs candidate-new",
        "",
        "- **Known**: frequent material-property pairs in Section 3.",
        "- **Candidate-new**: Gaps with `overlaps_known=false` and actionable next steps;",
        "  these remain hypotheses pending database/experimental falsification.",
        "",
        "## 8. Consistency check",
        "",
    ]
    if consistency:
        lines.append(f"- Status: **{'PASS' if consistency.ok else 'FAIL'}**")
        lines.append(f"- Issues: {len(consistency.issues)}")
        for issue in consistency.issues[:20]:
            lines.append(f"  - `[{issue.severity}]` {issue.kind}: {issue.detail}")
    else:
        lines.append("- Not run.")

    lines += [
        "",
        "## 9. System note",
        "",
        "Evidence-grounded extraction drops ungrounded fields. "
        "Enable `OPENAI_API_KEY` for higher-quality rewrite/extract/gap/review.",
        "",
    ]
    return "\n".join(lines)


def write_report(
    topic: str,
    subfield: str,
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    gaps: list[ResearchGap],
    known: list[KnownPair],
    query_variants: list[str],
    consistency: ConsistencyReport | None,
    llm: LLMClient,
    audit: list[AuditEvent],
) -> str:
    base = _render_heuristic_report(
        topic, subfield, papers, extractions, gaps, known, query_variants, consistency
    )
    if llm.enabled:
        polished = llm.chat_text(
            system=(
                "You are a materials science technical writer. "
                "Improve clarity while preserving all paper IDs, gap IDs, tables, "
                "evidence quotes, falsification tests, and consistency findings. Keep markdown."
            ),
            user=base,
            step="report",
        )
        if polished:
            base = polished

    audit.append(
        AuditEvent(
            step="write_report",
            tool="llm" if llm.enabled else "template",
            input_summary=topic,
            output_summary=f"{len(base)} chars",
        )
    )
    return base
