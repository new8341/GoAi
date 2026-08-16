from __future__ import annotations

import json
from pathlib import Path

from materials_agent.agents.reporter import _render_heuristic_report
from materials_agent.evidence_attribution import annotate_retrieval_databases
from materials_agent.export.latex_report import build_bibtex, export_survey_latex
from materials_agent.models import EvidenceSpan, Paper, ResearchGap


def _sample() -> tuple[list[Paper], list[ResearchGap]]:
    papers = [
        Paper(
            id="W123",
            title="SnSe vacancy thermal transport",
            year=2020,
            doi="10.1000/test",
            source="sciverse",
            authors=["A Author"],
        )
    ]
    gaps = [
        ResearchGap(
            id="gap-1",
            title="Vacancy concentration vs kappa_L",
            description="Need controlled vacancy series for SnSe lattice thermal conductivity.",
            supporting_paper_ids=["W123"],
            evidence_chain=[
                EvidenceSpan(
                    paper_id="W123",
                    claim="vacancy lowers kappa_L",
                    quote_or_basis="Vacancy scattering reduces lattice thermal conductivity in SnSe.",
                )
            ],
        )
    ]
    return papers, gaps


def test_annotate_retrieval_database_from_paper_source() -> None:
    papers, gaps = _sample()
    stats = annotate_retrieval_databases(papers, gaps)
    assert stats["gaps_with_database"] == 1
    assert gaps[0].evidence_chain[0].retrieval_database == "sciverse"


def test_markdown_report_prints_database() -> None:
    papers, gaps = _sample()
    annotate_retrieval_databases(papers, gaps)
    md = _render_heuristic_report(
        "SnSe vacancy",
        "thermoelectrics",
        papers,
        [],
        gaps,
        [],
        ["SnSe vacancy kappa"],
        None,
    )
    assert "Database: `sciverse`" in md
    assert "Databases used:" in md


def test_latex_export_contains_bib_and_database(tmp_path: Path) -> None:
    papers, gaps = _sample()
    annotate_retrieval_databases(papers, gaps)
    run = tmp_path / "run"
    run.mkdir()
    (run / "papers.json").write_text(
        json.dumps([papers[0].model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )
    (run / "gaps.json").write_text(
        json.dumps([gaps[0].model_dump()], ensure_ascii=False),
        encoding="utf-8",
    )
    (run / "extractions.json").write_text("[]", encoding="utf-8")
    (run / "queries.json").write_text('["q1"]', encoding="utf-8")
    result = export_survey_latex(run, compile_pdf=False)
    tex = Path(result["tex"]).read_text(encoding="utf-8")
    bib = Path(result["bib"]).read_text(encoding="utf-8")
    assert "sciverse" in bib.lower()
    assert "Database:" in tex
    assert "W123" in build_bibtex(papers) or "article{" in build_bibtex(papers)
