from __future__ import annotations

from collections import defaultdict

from materials_agent.models import AuditEvent, ExtractedRecord, KnownPair
from materials_agent.normalize import normalize_material, normalize_property


def build_known_pairs(
    extractions: list[ExtractedRecord],
    audit: list[AuditEvent],
    *,
    min_count: int = 1,
    ontology: dict | None = None,
) -> list[KnownPair]:
    """
    Frequent / ontology-prior material-property pairs = known dense region.
    For small corpora, min_count=1 still surfaces in-corpus observed links as Known
    (so Route A / Gaps do not claim them as discoveries).
    """
    ontology = ontology or {}
    bucket: dict[tuple[str, str], list[str]] = defaultdict(list)
    for e in extractions:
        mats = e.materials or e.composition
        for m in mats:
            m_n = normalize_material(m, ontology)
            for p in e.properties:
                p_n = normalize_property(p, ontology)
                if m_n and p_n:
                    bucket[(m_n, p_n)].append(e.paper_id)

    # ontology prior boost: if both appear in ontology examples, keep even singleton
    prior_mats = {normalize_material(str(x), ontology) for x in ontology.get("materials_examples") or []}
    prior_props = {normalize_property(str(x), ontology) for x in ontology.get("properties") or []}

    pairs: list[KnownPair] = []
    for (m, p), ids in sorted(bucket.items(), key=lambda x: -len(set(x[1]))):
        uniq = list(dict.fromkeys(ids))
        is_prior = m in prior_mats and p in prior_props
        if len(uniq) >= min_count or (is_prior and len(uniq) >= 1):
            pairs.append(KnownPair(material=m, property=p, count=len(uniq), paper_ids=uniq))

    audit.append(
        AuditEvent(
            step="build_known_table",
            tool="frequency+ontology",
            input_summary=f"{len(extractions)} extractions",
            output_summary=f"{len(pairs)} known pairs (min_count={min_count})",
            meta={"top": [x.model_dump() for x in pairs[:15]]},
        )
    )
    return pairs
