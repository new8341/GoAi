from materials_agent.models import Paper, ResearchGap
from materials_agent.topic_focus import (
    compute_optimization_metrics,
    extract_topic_materials,
    gap_aligned_to_topic,
)
from materials_agent.tools.retrievers import score_relevance


def test_extract_topic_materials_snse() -> None:
    mats = extract_topic_materials("SnSe lattice thermal conductivity vacancy engineering")
    assert any(m.lower() == "snse" for m in mats)


def test_score_relevance_penalizes_off_topic_te() -> None:
    topic = "SnSe lattice thermal conductivity vacancy engineering"
    snse = Paper(
        id="1",
        title="Vacancy engineering lowers lattice thermal conductivity of SnSe",
        abstract="SnSe polycrystalline vacancy phonon scattering",
    )
    bite = Paper(
        id="2",
        title="Bi2Te3-based applied thermoelectric materials",
        abstract="Thermoelectric figure of merit advances for Bi2Te3 cooling",
    )
    assert score_relevance(snse, topic) > score_relevance(bite, topic)
    assert score_relevance(bite, topic) < 0.35


def test_gap_alignment_rejects_pbte_temporal() -> None:
    mats = ["SnSe"]
    bad = ResearchGap(
        id="gap-temporal-PbTe",
        title="Temporal claim tension for PbTe across 2018–2022",
        description="PbTe early vs recent",
        gap_type="contradiction",
    )
    good = ResearchGap(
        id="gap-temporal-SnSe",
        title="Temporal claim tension for SnSe across 2018–2022",
        description="SnSe early vs recent",
        gap_type="contradiction",
    )
    assert not gap_aligned_to_topic(bad, mats)
    assert gap_aligned_to_topic(good, mats)
    scoped_lim = ResearchGap(
        id="gap-limitations",
        title="Open SnSe limitations repeatedly signaled in screened fulltexts",
        description="Within the screened SnSe corpus",
        gap_type="underexplored",
    )
    assert gap_aligned_to_topic(scoped_lim, mats)


def test_optimization_metrics_flags() -> None:
    topic = "SnSe vacancy"
    papers = [
        Paper(id="a", title="SnSe vacancy study", abstract="lattice thermal"),
        Paper(id="b", title="GeTe defect structures", abstract="thermoelectric"),
    ]
    gaps = [
        ResearchGap(
            id="gap-temporal-SnSe",
            title="Temporal claim tension for SnSe",
            description="SnSe",
            gap_type="contradiction",
        )
    ]
    metrics = compute_optimization_metrics(topic, papers, gaps)
    assert metrics["topic_materials"]
    assert 0.0 < metrics["topic_hit_rate"] <= 1.0
    assert "pass_flags" in metrics
