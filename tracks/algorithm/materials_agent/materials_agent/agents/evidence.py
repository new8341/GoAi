from __future__ import annotations

from materials_agent.config import QualityConfig
from materials_agent.limitation_quality import is_strong_limitation
from materials_agent.models import EvidenceProvenance, EvidenceSpan, ExtractedRecord
from materials_agent.normalize import (
    dedupe_preserve,
    normalize_material,
    normalize_method,
    normalize_property,
)


def parse_confidence(value: object, default: float = 0.65) -> float:
    """Coerce LLM confidence labels/numbers into a float in [0, 1]."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value).strip().lower()
    labeled = {
        "high": 0.85,
        "medium": 0.65,
        "med": 0.65,
        "low": 0.4,
        "very high": 0.95,
        "very low": 0.25,
    }
    if text in labeled:
        return labeled[text]
    try:
        return max(0.0, min(1.0, float(text)))
    except (TypeError, ValueError):
        return default


def quote_supported(item: str, evidence_text: str) -> bool:
    """Loose support check: token overlap with source text."""
    src = (evidence_text or "").lower()
    token = (item or "").strip().lower()
    if not token or not src:
        return False
    if token in src:
        return True
    # meta limitation labels: accept if cue words exist in source
    if token.startswith("abstract signals") or "cue '" in token:
        for cue in ("however", "limitation", "challenge", "remain", "unclear", "conflict", "debate"):
            if cue in src:
                return True
    parts = [p for p in token.replace("-", " ").split() if len(p) > 2]
    if not parts:
        return False
    hits = sum(1 for p in parts if p in src)
    return hits >= max(1, len(parts) // 2)


def quote_in_source(
    quote: str, source_text: str, provenance: EvidenceProvenance | None = None
) -> bool:
    """Verify a quote exactly, and validate offsets when they are available."""
    cleaned_quote = (quote or "").strip()
    source = source_text or ""
    if not cleaned_quote or not source or cleaned_quote not in source:
        return False
    if provenance and provenance.char_start is not None and provenance.char_end is not None:
        return source[provenance.char_start : provenance.char_end] == cleaned_quote
    return True


def make_evidence(
    paper_id: str,
    claim: str,
    quote: str,
    confidence: float,
    location: str,
    min_chars: int,
    provenance: EvidenceProvenance | None = None,
) -> EvidenceSpan | None:
    q = (quote or "").strip()
    if len(q) < min_chars:
        return None
    try:
        return EvidenceSpan(
            paper_id=paper_id,
            claim=claim,
            quote_or_basis=q[:500],
            confidence=confidence,
            location=location,
            provenance=provenance,
        )
    except Exception:
        return None


def sanitize_extraction(
    record: ExtractedRecord,
    source_text: str,
    quality: QualityConfig,
    ontology: dict | None = None,
) -> ExtractedRecord:
    """Normalize, dedupe, drop ungrounded fields; calibrate confidence."""
    ontology = ontology or {}
    dropped: list[str] = []
    data = record.model_dump()

    data["materials"] = [
        normalize_material(x, ontology) for x in dedupe_preserve(data.get("materials") or [])
    ]
    data["composition"] = [
        normalize_material(x, ontology) for x in dedupe_preserve(data.get("composition") or [])
    ]
    data["properties"] = [
        normalize_property(x, ontology) for x in dedupe_preserve(data.get("properties") or [])
    ]
    data["methods"] = [
        normalize_method(x, ontology) for x in dedupe_preserve(data.get("methods") or [])
    ]
    data["synthesis"] = [
        normalize_method(x, ontology) for x in dedupe_preserve(data.get("synthesis") or [])
    ]
    data["structure"] = dedupe_preserve(data.get("structure") or [])
    data["key_findings"] = dedupe_preserve(data.get("key_findings") or [])
    data["limitations"] = dedupe_preserve(data.get("limitations") or [])

    if quality.require_evidence:
        for name in (
            "materials",
            "composition",
            "structure",
            "properties",
            "methods",
            "synthesis",
            "key_findings",
            "limitations",
        ):
            kept: list[str] = []
            for item in data.get(name) or []:
                # limitations: keep only strong open-issue sentences grounded in source
                if name == "limitations":
                    item_s = str(item)
                    if is_strong_limitation(item_s) and (
                        quote_supported(item_s, source_text)
                        or any(
                            c in source_text.lower()
                            for c in (
                                "limitation",
                                "challenge",
                                "remain",
                                "unclear",
                                "not fully",
                                "still low",
                            )
                        )
                    ):
                        kept.append(item_s)
                    else:
                        dropped.append(f"{name}:{item}")
                    continue
                if quote_supported(str(item), source_text):
                    kept.append(str(item))
                else:
                    dropped.append(f"{name}:{item}")
            data[name] = dedupe_preserve(kept)

    evidence = []
    for ev in record.evidence:
        if len(ev.quote_or_basis.strip()) < quality.min_quote_chars:
            dropped.append("evidence:short_quote")
            continue
        if ev.confidence < quality.min_evidence_confidence:
            dropped.append("evidence:low_confidence")
            continue
        if quality.reject_evidence_without_provenance and ev.location in {"fulltext", "chunk"}:
            if not ev.provenance:
                dropped.append("evidence:missing_provenance")
                continue
        if quality.require_quote_substring and not quote_in_source(
            ev.quote_or_basis, source_text, ev.provenance
        ):
            dropped.append("evidence:quote_not_in_source")
            continue
        evidence.append(ev)
    if not evidence:
        ev = make_evidence(
            record.paper_id,
            "fallback title/abstract anchor",
            source_text[:240] or "insufficient source text available for evidence",
            0.3,
            "heuristic",
            quality.min_quote_chars,
        )
        if ev:
            evidence.append(ev)

    filled = sum(
        1
        for n in (
            "materials",
            "properties",
            "methods",
            "key_findings",
            "limitations",
        )
        if data.get(n)
    )
    # calibrated: never saturate just because many fields exist
    conf = round(min(0.95, 0.12 * filled + 0.15 * min(3, len(evidence)) + 0.1), 3)
    return ExtractedRecord(
        paper_id=record.paper_id,
        materials=data["materials"],
        composition=data["composition"],
        structure=data["structure"],
        properties=data["properties"],
        methods=data["methods"],
        synthesis=data["synthesis"],
        key_findings=data["key_findings"],
        limitations=data["limitations"],
        evidence=evidence,
        dropped_fields=dropped,
        extraction_confidence=conf,
    )
