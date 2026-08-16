"""Sci-Base cache retrieval tests (no HF download)."""

from __future__ import annotations

from pathlib import Path

from materials_agent.config import AppConfig, RetrievalConfig
from materials_agent.models import AuditEvent
from materials_agent.tools.retrievers import SciBaseRetriever
from materials_agent.tools.scibase_client import load_cache_rows, search_cache


FIXTURE = Path(__file__).parent / "fixtures" / "scibase_materials_cache.jsonl"


def test_search_cache_prefers_snse_materials():
    rows = load_cache_rows(FIXTURE)
    papers = search_cache(
        rows,
        ["SnSe lattice thermal conductivity vacancy"],
        top_k=5,
        category_substrings=["Materials", "Physics"],
    )
    assert papers
    assert all(p.source == "scibase" for p in papers)
    assert any("SnSe" in p.title for p in papers)
    assert all(p.raw.get("dataset") == "opendatalab/Sci-Base" for p in papers)


def test_scibase_retriever_uses_fixture_cache(tmp_path):
    cache = tmp_path / "materials_cache.jsonl"
    cache.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    cfg = AppConfig(
        topic="SnSe lattice thermal conductivity vacancy engineering",
        max_papers=3,
        retrieval=RetrievalConfig(
            backend="scibase",
            scibase_cache_path=str(cache),
            scibase_prefer_cache=True,
            scibase_streaming=False,
            allow_backend_fallback=False,
            min_relevance=0.05,
        ),
        output_dir=str(tmp_path / "out"),
    )
    audit: list[AuditEvent] = []
    papers = SciBaseRetriever().search(
        ["SnSe vacancy thermal conductivity"],
        cfg,
        audit,
    )
    assert len(papers) >= 1
    assert papers[0].source == "scibase"
    assert any(e.tool == "scibase" for e in audit)
