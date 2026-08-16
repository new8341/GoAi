"""Tests for strong-limitation filtering and concrete open-issue gaps."""

from materials_agent.agents.gap_finder import _heuristic_gaps
from materials_agent.agents.gap_reviewer import _heuristic_review
from materials_agent.config import QualityConfig
from materials_agent.limitation_quality import is_strong_limitation
from materials_agent.models import ExtractedRecord, Paper, ResearchGap


def test_is_strong_limitation_accepts_open_issues() -> None:
    assert is_strong_limitation(
        "However, the ZT of polycrystalline SnSe around room temperature remains low."
    )
    assert is_strong_limitation(
        "Vacancy engineering is still a challenge for scalable SnSe devices."
    )
    assert is_strong_limitation(
        "Phonon convergence in CP2K remains harder and results are still uncertain."
    )


def test_is_strong_limitation_rejects_positive_however() -> None:
    assert not is_strong_limitation(
        "However, along the b-axis direction, NPs have an intense effect in the reduction "
        "of thermal conductivity, which is beneficial for thermoelectric performance."
    )
    assert not is_strong_limitation(
        "As temperature increases, however, SnS becomes more similar to SnSe structurally."
    )


def test_is_strong_limitation_rejects_descriptive_band_prose() -> None:
    assert not is_strong_limitation(
        'The highest valence bands below the Fermi level show a characteristic '
        '"pudding mold"-like structure in SnS, which is also present in SnSe but with '
        "a more pronounced energy offset between the two maxima."
    )
    assert is_strong_limitation(
        "Nonetheless, these conditions cannot be immediately translated into a material "
        "design strategy due to the interdependence of the physical parameters contributing to ZT."
    )


def test_heuristic_gaps_emit_concrete_open_not_meta_bag() -> None:
    papers = [
        Paper(
            id="P1",
            title="Anisotropic SnSe lattice thermal conductivity",
            abstract="SnSe grain boundary scattering study.",
            year=2024,
        ),
        Paper(
            id="P2",
            title="SnSe thermoelectric review",
            abstract="SnSe ZT trends.",
            year=2023,
        ),
    ]
    extractions = [
        ExtractedRecord(
            paper_id="P1",
            materials=["SnSe"],
            properties=["thermal conductivity"],
            limitations=[
                "However, grain-boundary scattering of phonons in anisotropic SnSe remains unclear.",
                "However, NPs have an intense effect in reduction which is beneficial for ZT.",
            ],
        ),
        ExtractedRecord(
            paper_id="P2",
            materials=["SnSe"],
            properties=["ZT"],
            limitations=[
                "However, the ZT of polycrystalline SnSe around room temperature remains low."
            ],
        ),
    ]
    gaps = _heuristic_gaps(
        "Anisotropic SnSe lattice thermal conductivity grain boundary scattering",
        papers,
        extractions,
        known=[],
        quality=QualityConfig(min_quote_chars=25),
    )
    assert not any(g.id == "gap-limitations" for g in gaps)
    open_gaps = [g for g in gaps if g.id.startswith("gap-open-")]
    assert open_gaps
    for g in open_gaps:
        assert "Unresolved:" in g.title
        assert "papers contain limitation" not in g.description.lower()
        assert len(g.supporting_paper_ids) == 1
        assert g.supporting_paper_ids[0] in {e.paper_id for e in g.evidence_chain}
        assert "beneficial" not in g.description.lower()


def test_gap_reviewer_rejects_meta_limitations_bag() -> None:
    papers = [
        Paper(id="P1", title="SnSe paper", abstract="SnSe thermal conductivity."),
    ]
    bag = ResearchGap(
        id="gap-limitations",
        title="Open limitations repeatedly signaled in screened abstracts",
        description="3 papers contain limitation/uncertainty sentences.",
        gap_type="underexplored",
        supporting_paper_ids=["P1"],
        evidence_chain=[],
        suggested_next_step="Design a falsifiable check for SnSe grain boundary scattering.",
        falsification_test="If follow-up resolves the issue, close the gap.",
        novelty=0.55,
        actionability=0.72,
    )
    reviewed = _heuristic_review(
        [bag],
        papers,
        known=[],
        quality=QualityConfig(drop_gaps_without_evidence=False, min_gap_actionability=0.5),
        topic="Anisotropic SnSe lattice thermal conductivity grain boundary scattering",
    )
    assert reviewed == []
    assert bag.review_status == "rejected"
