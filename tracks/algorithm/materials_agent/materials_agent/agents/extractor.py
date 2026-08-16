from __future__ import annotations

import re

from materials_agent.agents.evidence import make_evidence, parse_confidence, sanitize_extraction
from materials_agent.config import QualityConfig
from materials_agent.limitation_quality import is_strong_limitation
from materials_agent.llm import LLMClient
from materials_agent.models import AuditEvent, ExtractedRecord, Paper

_MATERIAL_PAT = re.compile(
    r"\b(?:Bi2Te3|PbTe|SnSe|GeTe|Mg3Sb2|CoSb3|SiGe|Cu2Se|half[- ]Heusler|"
    r"perovskite|MOF|COF|MXene|graphene|LiFePO4|NMC|NCA|"
    r"[A-Z][a-z]?(?:\d+[A-Z][a-z]?\d*){1,4})\b"
)
_PROP_PAT = re.compile(
    r"(?:figure of merit|\bZT\b|Seebeck|thermal conductivity|electrical conductivity|"
    r"band gap|mobility|power factor|capacity|conductivity|hardness|"
    r"catalytic activity|adsorption|stability)",
    re.I,
)
_METHOD_PAT = re.compile(
    r"(?:DFT|density functional|molecular dynamics|\bMD\b|Monte Carlo|"
    r"machine learning|neural network|XRD|SEM|TEM|synthesis|"
    r"spark plasma|hydrothermal|sol[- ]gel)",
    re.I,
)
def _limitation_sentences(text: str) -> list[str]:
    if not text:
        return []
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for s in sents:
        quote = s.strip()
        if is_strong_limitation(quote):
            out.append(quote)
    return out[:3]


def _heuristic_extract(
    paper: Paper, quality: QualityConfig, ontology: dict | None
) -> ExtractedRecord:
    from materials_agent.tools.fulltext import paper_source_text

    text, location = paper_source_text(paper)
    if not text:
        text = f"{paper.title}. {paper.abstract or ''}"
        location = "abstract" if paper.abstract else "title"
    materials = list(dict.fromkeys(_MATERIAL_PAT.findall(text)))[:12]
    properties = list(dict.fromkeys(m.group(0) for m in _PROP_PAT.finditer(text)))[:12]
    methods = list(dict.fromkeys(m.group(0) for m in _METHOD_PAT.finditer(text)))[:12]
    findings = []
    body = paper.full_text or paper.abstract or ""
    if body:
        sent = re.split(r"(?<=[.!?])\s+", body)
        findings = [s.strip() for s in sent[:3] if len(s.strip()) > 40][:3]
    limitations = _limitation_sentences(body) or _limitation_sentences(text)
    evidence = []
    quote = (paper.full_text or paper.abstract or paper.title or "")[:400]
    ev = make_evidence(
        paper.id,
        "fulltext/title heuristic extraction" if location == "fulltext" else "title/abstract heuristic extraction",
        quote,
        0.55 if location == "fulltext" else 0.4,
        location,
        quality.min_quote_chars,
    )
    if ev:
        evidence.append(ev)
    record = ExtractedRecord(
        paper_id=paper.id,
        materials=materials,
        composition=materials,
        structure=[],
        properties=properties,
        methods=methods,
        synthesis=[m for m in methods if re.search(r"synthesis|hydrothermal|sol|spark", m, re.I)],
        key_findings=findings,
        limitations=limitations,
        evidence=evidence,
    )
    return sanitize_extraction(record, text, quality, ontology)


def extract_knowledge(
    papers: list[Paper],
    llm: LLMClient,
    quality: QualityConfig,
    audit: list[AuditEvent],
    ontology: dict | None = None,
) -> list[ExtractedRecord]:
    ontology = ontology or {}
    domain_hint = ""
    if ontology:
        domain_hint = (
            f"Domain properties of interest: {ontology.get('properties', [])}. "
            f"Common methods: {ontology.get('methods', [])}."
        )
    records: list[ExtractedRecord] = []
    for paper in papers:
        from materials_agent.tools.fulltext import paper_source_text

        source, location = paper_source_text(paper)
        if not source:
            source = f"{paper.title}. {paper.abstract or ''}"
            location = "abstract" if paper.abstract else "title"
        record = None
        if llm.enabled and (paper.full_text or paper.abstract):
            body = paper.full_text or paper.abstract or ""
            payload = llm.chat_json(
                system=(
                    "You are a materials science extraction agent. "
                    "Only extract claims supported by the given document text. "
                    "limitations must be verbatim-like sentences that signal unresolved open "
                    "issues (remain/unclear/still low/challenge/limitation), not positive "
                    "results that merely contain 'however'. "
                    "Return JSON keys: materials, composition, structure, properties, "
                    "methods, synthesis, key_findings, limitations, "
                    "evidence:[{claim,quote_or_basis,confidence}]. "
                    + domain_hint
                ),
                user=f"Title: {paper.title}\nYear: {paper.year}\nText ({location}):\n{body[:6000]}",
                step="extract",
                validator=lambda d: isinstance(d, dict),
            )
            if isinstance(payload, dict):
                evidence = []
                for item in payload.get("evidence") or []:
                    if not isinstance(item, dict):
                        continue
                    ev = make_evidence(
                        paper.id,
                        str(item.get("claim") or "llm evidence"),
                        str(item.get("quote_or_basis") or ""),
                        parse_confidence(item.get("confidence"), 0.65),
                        location,
                        quality.min_quote_chars,
                    )
                    if ev:
                        evidence.append(ev)
                if not evidence:
                    ev = make_evidence(
                        paper.id,
                        "LLM extraction anchor",
                        body[:400] or paper.title,
                        0.55,
                        location,
                        quality.min_quote_chars,
                    )
                    if ev:
                        evidence.append(ev)
                record = ExtractedRecord(
                    paper_id=paper.id,
                    materials=list(payload.get("materials") or []),
                    composition=list(payload.get("composition") or []),
                    structure=list(payload.get("structure") or []),
                    properties=list(payload.get("properties") or []),
                    methods=list(payload.get("methods") or []),
                    synthesis=list(payload.get("synthesis") or []),
                    key_findings=list(payload.get("key_findings") or []),
                    limitations=list(payload.get("limitations") or [])
                    or _limitation_sentences(body),
                    evidence=evidence,
                )
                record = sanitize_extraction(record, source, quality, ontology)
        if record is None:
            record = _heuristic_extract(paper, quality, ontology)
        records.append(record)

    dropped = sum(len(r.dropped_fields) for r in records)
    audit.append(
        AuditEvent(
            step="extract",
            tool="llm" if llm.enabled else "heuristic",
            input_summary=f"{len(papers)} papers",
            output_summary=f"{len(records)} records; dropped_ungrounded={dropped}",
            meta={
                "mean_confidence": round(
                    sum(r.extraction_confidence for r in records) / max(1, len(records)), 3
                ),
                "with_limitations": sum(1 for r in records if r.limitations),
            },
        )
    )
    return records
