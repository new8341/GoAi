from materials_agent.agents.evidence_selector import (
    ground_gap_evidence,
    is_boilerplate_text,
)
from materials_agent.config import EvidenceRetrievalConfig, QualityConfig
from materials_agent.models import (
    DocumentChunk,
    ExtractedRecord,
    Paper,
    ResearchGap,
)
from materials_agent.tools.index.file_index import FileEvidenceIndex


def test_is_boilerplate_detects_license_and_peer_review() -> None:
    assert is_boilerplate_text(
        "Open Access This article is licensed under a Creative Commons Attribution 4.0."
    )
    assert is_boilerplate_text(
        "Peer review information Nature Communications thanks Iris for their contribution."
    )
    assert not is_boilerplate_text(
        "However, the ZT of SnSe around room temperature is still low compared to other materials."
    )


def test_rule_score_penalizes_boilerplate_evidence() -> None:
    from scripts.ai_human_review import _rule_score_A

    clean = {
        "gap_type": "underexplored",
        "evidence_chain": [
            {"quote_or_basis": "However, the ZT of SnSe around room temperature is still low."}
        ],
        "suggested_next_step": "Measure kappa_lat on vacancy-engineered SnSe under fixed carrier density.",
        "falsification_test": "If kappa_lat does not change under vacancy series, reject the limitation gap.",
        "title": "Open SnSe limitations",
        "description": "corpus-scoped",
    }
    noisy = {
        **clean,
        "evidence_chain": [
            {
                "quote_or_basis": (
                    "Open Access This article is licensed under a Creative Commons Attribution 4.0 "
                    "International License."
                )
            }
        ],
    }
    assert _rule_score_A(clean, [])["evidence_fit"] == 2
    assert _rule_score_A(noisy, [])["evidence_fit"] == 0


def test_gap_evidence_prefers_fulltext_chunk(tmp_path) -> None:
    paper = Paper(
        id="P1",
        title="SnSe paper",
        abstract="Abstract only.",
        full_text="Results show vacancy engineering lowers lattice thermal conductivity.",
        fulltext_source="mineru",
        pdf_hash="abc123",
    )
    chunk = DocumentChunk(
        chunk_id="P1:0000",
        paper_id="P1",
        text=paper.full_text,
        char_start=0,
        char_end=len(paper.full_text),
        parser="mineru",
        pdf_hash="abc123",
    )
    index = FileEvidenceIndex(tmp_path / "chunks.json")
    index.upsert([chunk])
    gap = ResearchGap(
        id="G1",
        title="Vacancy mechanism remains unresolved",
        description="Need discriminate vacancy scattering.",
        supporting_paper_ids=["P1"],
    )
    grounded = ground_gap_evidence(
        [gap],
        [paper],
        index,
        EvidenceRetrievalConfig(),
        QualityConfig(require_fulltext_gap_evidence=True, allow_abstract_fallback=False),
        [],
    )

    assert grounded[0].evidence_chain[0].location == "fulltext"
    assert grounded[0].evidence_chain[0].provenance is not None


def test_gap_evidence_skips_boilerplate_for_limitations(tmp_path) -> None:
    paper = Paper(
        id="P1",
        title="SnSe vacancy paper",
        abstract="SnSe thermoelectric study.",
        full_text="body",
        fulltext_source="grobid_fusion",
        pdf_hash="h1",
    )
    license_chunk = DocumentChunk(
        chunk_id="P1:0000",
        paper_id="P1",
        text=(
            "Open Access This article is licensed under a Creative Commons Attribution "
            "4.0 International License. Peer review information thanks the reviewers."
        ),
        char_start=0,
        char_end=160,
        section="Body",
        parser="grobid_fusion",
        pdf_hash="h1",
    )
    science_chunk = DocumentChunk(
        chunk_id="P1:0001",
        paper_id="P1",
        text=(
            "However, the ZT of polycrystalline SnSe around room temperature remains low, "
            "and vacancy engineering is still a challenge for scalable devices."
        ),
        char_start=200,
        char_end=360,
        section="Discussion",
        parser="grobid_fusion",
        pdf_hash="h1",
    )
    index = FileEvidenceIndex(tmp_path / "chunks.json")
    index.upsert([license_chunk, science_chunk])
    gap = ResearchGap(
        id="gap-open-P1-0",
        title="Unresolved: However, the ZT of polycrystalline SnSe around room temperature remains low.",
        description=(
            "Paper `P1` signals an open scientific limitation rather than a settled conclusion: "
            "However, the ZT of polycrystalline SnSe around room temperature remains low."
        ),
        supporting_paper_ids=["P1"],
    )
    extraction = ExtractedRecord(
        paper_id="P1",
        materials=["SnSe"],
        properties=["ZT"],
        limitations=[
            "However, the ZT of polycrystalline SnSe around room temperature remains low."
        ],
    )
    grounded = ground_gap_evidence(
        [gap],
        [paper],
        index,
        EvidenceRetrievalConfig(min_retrieval_score=0.0),
        QualityConfig(require_fulltext_gap_evidence=True, allow_abstract_fallback=False),
        [],
        extractions=[extraction],
    )

    assert len(grounded) == 1
    quote = grounded[0].evidence_chain[0].quote_or_basis.lower()
    assert "creative commons" not in quote
    assert "peer review" not in quote
    assert "however" in quote or "remains low" in quote


def test_temporal_gap_requires_both_eras(tmp_path) -> None:
    early = Paper(id="E1", title="Early SnSe", year=2020, abstract="early", full_text="early")
    recent = Paper(id="R1", title="Recent SnSe", year=2025, abstract="recent", full_text="recent")
    early_chunk = DocumentChunk(
        chunk_id="E1:0000",
        paper_id="E1",
        text="In 2020 we report phonon scattering lowers lattice thermal conductivity of SnSe.",
        char_start=0,
        char_end=90,
        section="Results",
        parser="grobid_fusion",
        pdf_hash="earlyhash",
    )
    recent_chunk = DocumentChunk(
        chunk_id="R1:0000",
        paper_id="R1",
        text="Recent ZT and Seebeck measurements show a different phonon scattering mechanism in SnSe.",
        char_start=0,
        char_end=100,
        section="Results",
        parser="grobid_fusion",
        pdf_hash="recenthash",
    )
    noise = DocumentChunk(
        chunk_id="E1:0001",
        paper_id="E1",
        text="Data availability The data that support the findings are available upon request. References Snyder 2008 Biswas 2012.",
        char_start=100,
        char_end=220,
        section="References",
        parser="grobid_fusion",
        pdf_hash="earlyhash",
    )
    index = FileEvidenceIndex(tmp_path / "chunks.json")
    index.upsert([early_chunk, recent_chunk, noise])
    gap = ResearchGap(
        id="gap-temporal-SnSe",
        title="Temporal claim tension for SnSe across 2020–2025",
        description="Both early and recent papers discuss SnSe.",
        gap_type="contradiction",
        supporting_paper_ids=["R1"],
        contradicting_paper_ids=["E1"],
    )
    grounded = ground_gap_evidence(
        [gap],
        [early, recent],
        index,
        EvidenceRetrievalConfig(min_retrieval_score=0.0),
        QualityConfig(require_fulltext_gap_evidence=True, allow_abstract_fallback=False),
        [],
    )
    assert len(grounded) == 1
    paper_ids = {e.paper_id for e in grounded[0].evidence_chain}
    assert paper_ids == {"E1", "R1"}
    for span in grounded[0].evidence_chain:
        assert "data availability" not in span.quote_or_basis.lower()


def test_temporal_gap_rejects_one_sided_fulltext(tmp_path) -> None:
    """If only one era has indexed fulltext, do not fake a contradiction with one paper."""
    early = Paper(
        id="E1",
        title="Early SnSe",
        year=2020,
        abstract="Early abstract on SnSe phonon scattering and lattice thermal conductivity.",
        full_text="early",
    )
    recent = Paper(
        id="R1",
        title="Recent SnSe",
        year=2025,
        abstract="Recent abstract on doped SnSe lattice thermal conductivity trends.",
        full_text="",
    )
    early_chunk = DocumentChunk(
        chunk_id="E1:0000",
        paper_id="E1",
        text="In 2020 we report phonon scattering lowers lattice thermal conductivity of SnSe.",
        char_start=0,
        char_end=90,
        section="Results",
        parser="grobid_fusion",
        pdf_hash="earlyhash",
    )
    index = FileEvidenceIndex(tmp_path / "chunks.json")
    index.upsert([early_chunk])
    gap = ResearchGap(
        id="gap-temporal-SnSe",
        title="Temporal claim tension for SnSe across 2020–2025",
        description="Both early and recent papers discuss SnSe.",
        gap_type="contradiction",
        supporting_paper_ids=["R1"],
        contradicting_paper_ids=["E1"],
    )
    grounded = ground_gap_evidence(
        [gap],
        [early, recent],
        index,
        EvidenceRetrievalConfig(min_retrieval_score=0.0),
        QualityConfig(require_fulltext_gap_evidence=False, allow_abstract_fallback=True),
        [],
    )
    assert len(grounded) == 1
    paper_ids = {e.paper_id for e in grounded[0].evidence_chain}
    assert "E1" in paper_ids and "R1" in paper_ids
