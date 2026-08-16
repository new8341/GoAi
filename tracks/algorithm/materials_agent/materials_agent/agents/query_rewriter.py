from __future__ import annotations

from materials_agent.llm import LLMClient
from materials_agent.models import AuditEvent


def rewrite_queries(
    topic: str,
    subfield: str,
    ontology: dict,
    llm: LLMClient,
    audit: list[AuditEvent],
    *,
    enabled: bool = True,
) -> list[str]:
    """Rewrite user topic into materials-search intents (system / property / method)."""
    keywords = ontology.get("search_keywords") or []
    properties = ontology.get("properties") or []
    methods = ontology.get("methods") or []

    rule_variants = [
        topic,
        f"{topic} {subfield}".strip(),
    ]
    if keywords:
        rule_variants.append(f"{topic} {' '.join(keywords[:3])}")
    if properties:
        rule_variants.append(f"{subfield} {properties[0]} structure property")
    if methods:
        rule_variants.append(f"{topic} {methods[0]}")

    variants: list[str] = []
    seen: set[str] = set()
    for q in rule_variants:
        qn = " ".join(q.split())
        if qn and qn.lower() not in seen:
            seen.add(qn.lower())
            variants.append(qn)

    if enabled and llm.enabled:
        payload = llm.chat_json(
            system=(
                "You are a materials-science retrieval intent rewriter. "
                "Produce diverse search queries. Return JSON "
                '{"queries":["..."]} with 3 to 5 short queries covering: '
                "material system, target property, synthesis/method, and contradictions/limitations."
            ),
            user=f"Topic: {topic}\nSubfield: {subfield}\nOntology hints: {keywords[:8]}",
            step="rewrite",
            validator=lambda d: isinstance(d.get("queries"), list) and len(d["queries"]) >= 1,
        )
        if payload:
            for q in payload["queries"]:
                qn = " ".join(str(q).split())
                if qn and qn.lower() not in seen:
                    seen.add(qn.lower())
                    variants.append(qn)

    audit.append(
        AuditEvent(
            step="rewrite_queries",
            tool="llm" if llm.enabled and enabled else "rules",
            input_summary=topic,
            output_summary=f"{len(variants)} variants",
            meta={"queries": variants},
        )
    )
    return variants[:6] or [topic]
