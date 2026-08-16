from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


GapType = Literal["missing_link", "contradiction", "underexplored", "method_gap"]
NoveltyLabel = Literal["known", "candidate_new", "uncertain"]


class Paper(BaseModel):
    id: str
    title: str
    year: int | None = None
    doi: str | None = None
    abstract: str | None = None
    full_text: str | None = None
    authors: list[str] = Field(default_factory=list)
    cited_by: int = 0
    venue: str | None = None
    url: str | None = None
    oa_url: str | None = None
    concepts: list[str] = Field(default_factory=list)
    source: str = "openalex"
    relevance_score: float = 0.0
    query_tag: str = ""
    fulltext_source: str = ""  # local_cache | oa_pdf | mineru | grobid | none
    # Readers still accept legacy grobid_fusion via canonical_fulltext_source().
    pdf_path: str | None = None
    pdf_hash: str | None = None
    oa_status: str | None = None
    oa_license: str | None = None
    oa_version: str | None = None
    fulltext_url: str | None = None
    parse_manifest_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class EvidenceProvenance(BaseModel):
    """Coordinates and source metadata required to reproduce an evidence quote."""

    source_url: str | None = None
    pdf_hash: str | None = None
    parser: str | None = None
    parser_version: str | None = None
    page: int | None = None
    section: str | None = None
    chunk_id: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    chunk_hash: str | None = None


class EvidenceSpan(BaseModel):
    paper_id: str
    claim: str
    quote_or_basis: str
    confidence: float = 0.5
    location: str = "abstract"  # abstract | title | fulltext | chunk | heuristic
    provenance: EvidenceProvenance | None = None
    # Literature DB used to retrieve this paper (handbook: name the database per claim/Gap).
    retrieval_database: str = ""

    @field_validator("quote_or_basis")
    @classmethod
    def quote_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if len(v) < 8:
            raise ValueError("evidence quote too short")
        return v


class DocumentChunk(BaseModel):
    """A stable, source-addressable unit in the evidence index."""

    chunk_id: str
    paper_id: str
    text: str
    char_start: int
    char_end: int
    section: str | None = None
    page: int | None = None
    parser: str = "local_cache"
    source_url: str | None = None
    pdf_hash: str | None = None
    chunk_hash: str = ""


class ParseManifest(BaseModel):
    """Per-paper record of OA acquisition and parser outcomes."""

    manifest_id: str
    paper_id: str
    source_url: str | None = None
    pdf_path: str | None = None
    pdf_hash: str | None = None
    oa_license: str | None = None
    oa_version: str | None = None
    parsers: list[str] = Field(default_factory=list)
    parser_outputs: dict[str, str] = Field(default_factory=dict)
    chunk_count: int = 0
    errors: list[str] = Field(default_factory=list)


class ExtractedRecord(BaseModel):
    paper_id: str
    materials: list[str] = Field(default_factory=list)
    composition: list[str] = Field(default_factory=list)
    structure: list[str] = Field(default_factory=list)
    properties: list[str] = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    synthesis: list[str] = Field(default_factory=list)
    key_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    dropped_fields: list[str] = Field(default_factory=list)
    extraction_confidence: float = 0.0


class ResearchGap(BaseModel):
    id: str
    title: str
    description: str
    gap_type: GapType = "underexplored"
    novelty: float = 0.5
    actionability: float = 0.5
    supporting_paper_ids: list[str] = Field(default_factory=list)
    contradicting_paper_ids: list[str] = Field(default_factory=list)
    evidence_chain: list[EvidenceSpan] = Field(default_factory=list)
    suggested_next_step: str = ""
    falsification_test: str = ""
    review_status: str = "accepted"  # accepted | revised | rejected
    review_notes: str = ""
    overlaps_known: bool = False


class KnownPair(BaseModel):
    material: str
    property: str
    count: int
    paper_ids: list[str] = Field(default_factory=list)


class ConsistencyIssue(BaseModel):
    kind: str
    detail: str
    severity: str = "warn"  # warn | error


class ConsistencyReport(BaseModel):
    ok: bool = True
    issues: list[ConsistencyIssue] = Field(default_factory=list)


class AuditEvent(BaseModel):
    step: str
    tool: str
    input_summary: str
    output_summary: str
    meta: dict[str, Any] = Field(default_factory=dict)


class SurveyBundle(BaseModel):
    topic: str
    subfield: str
    papers: list[Paper]
    extractions: list[ExtractedRecord]
    gaps: list[ResearchGap]
    known_pairs: list[KnownPair] = Field(default_factory=list)
    query_variants: list[str] = Field(default_factory=list)
    consistency: ConsistencyReport | None = None
    report_markdown: str = ""
    audit: list[AuditEvent] = Field(default_factory=list)
