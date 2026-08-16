"""Regression tests for architecture upgrades U1–U8 / U15."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from materials_agent.config import AppConfig, RetrievalConfig, load_ontology
from materials_agent.models import AuditEvent, Paper
from materials_agent.topic_focus import REQUIRED_METRIC_KEYS, compute_optimization_metrics, topic_property_tokens
from materials_agent.tools.backend_honesty import BackendFallbackError
from materials_agent.tools.fulltext_labels import canonical_fulltext_source, is_parser_derived_source
from materials_agent.tools.paper_titles import is_placeholder_title, title_from_tei_xml
from materials_agent.tools.retrievers import SciverseRetriever

ROOT = Path(__file__).resolve().parents[1]


def _viewer():
    spec = importlib.util.spec_from_file_location("serve_viewer", ROOT / "scripts" / "serve_viewer.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_u2_placeholder_and_tei_title() -> None:
    assert is_placeholder_title("SV-paper 10.1002 aenm", "SV-paper_10.1002_aenm")
    assert is_placeholder_title("", "x")
    assert not is_placeholder_title("Vacancy engineering of SnSe", "SV-paper_1")
    tei = """<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader>
      <fileDesc><titleStmt><title>High thermoelectric performance in SnSe</title></titleStmt></fileDesc>
    </teiHeader></TEI>"""
    assert title_from_tei_xml(tei) == "High thermoelectric performance in SnSe"


def test_u3_sciverse_no_token_hard_fails_when_fallback_forbidden(monkeypatch) -> None:
    monkeypatch.delenv("SCIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("SCIVERSE_API_KEY", raising=False)
    cfg = AppConfig(
        topic="SnSe",
        max_papers=2,
        retrieval=RetrievalConfig(
            backend="sciverse",
            sciverse_api_token="",
            allow_backend_fallback=False,
        ),
    )
    with pytest.raises(BackendFallbackError, match="allow_backend_fallback=false"):
        SciverseRetriever().search(["SnSe"], cfg, [])


def test_u3_sciverse_fallback_still_allowed_when_enabled(monkeypatch) -> None:
    monkeypatch.delenv("SCIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("SCIVERSE_API_KEY", raising=False)
    cfg = AppConfig(
        topic="SnSe",
        max_papers=2,
        retrieval=RetrievalConfig(backend="sciverse", sciverse_api_token="", allow_backend_fallback=True),
    )
    audit: list[AuditEvent] = []
    fake = [Paper(id="OA-1", title="OpenAlex hit", abstract="SnSe", source="openalex")]
    from unittest.mock import patch

    with patch("materials_agent.tools.retrievers.OpenAlexRetriever.search", return_value=fake):
        out = SciverseRetriever().search(["SnSe"], cfg, audit)
    assert out == fake
    assert audit[-1].meta["effective_backend"] == "openalex"


def test_u4_user_result_cache_invalidates_on_title_change(tmp_path: Path, monkeypatch) -> None:
    from materials_agent.models import ResearchGap, SurveyBundle

    mod = _viewer()
    run = tmp_path / "outputs" / "demo_run"
    run.mkdir(parents=True)
    papers = [Paper(id="p1", title="Old title", abstract="SnSe vacancy", full_text="x" * 100)]
    gaps = [
        ResearchGap(
            id="g1",
            title="SnSe gap",
            description="d",
            gap_type="underexplored",
        )
    ]
    bundle = SurveyBundle(
        topic="SnSe",
        subfield="thermoelectrics",
        papers=papers,
        extractions=[],
        gaps=gaps,
        report_markdown="# r",
    )
    (run / "bundle.json").write_text(bundle.model_dump_json(), encoding="utf-8")
    (run / "gaps.json").write_text(json.dumps([g.model_dump() for g in gaps]), encoding="utf-8")
    (run / "papers.json").write_text(json.dumps([p.model_dump() for p in papers]), encoding="utf-8")
    monkeypatch.setattr(mod, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    first = mod._public_from_run("demo_run")
    assert first["papers"][0]["title"] == "Old title"
    payload = json.loads((run / "papers.json").read_text(encoding="utf-8"))
    payload[0]["title"] = "New SnSe title"
    (run / "papers.json").write_text(json.dumps(payload), encoding="utf-8")
    # bundle must change too or sanitize still reads bundle; update both
    bundle.papers[0].title = "New SnSe title"
    (run / "bundle.json").write_text(bundle.model_dump_json(), encoding="utf-8")
    second = mod._public_from_run("demo_run")
    assert second["papers"][0]["title"] == "New SnSe title"


def test_u6_metrics_contract_keys() -> None:
    metrics = compute_optimization_metrics(
        "SnSe vacancy",
        [Paper(id="a", title="SnSe vacancy study", abstract="lattice thermal", full_text="body")],
        [],
    )
    assert REQUIRED_METRIC_KEYS <= set(metrics)


def test_u7_verify_fails_on_boilerplate(tmp_path: Path) -> None:
    from materials_agent.config import QualityConfig

    spec = importlib.util.spec_from_file_location("verify_production", ROOT / "scripts" / "verify_production.py")
    assert spec and spec.loader
    vmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vmod)
    verify_run = vmod.verify_run

    papers = [
        {
            "id": "p1",
            "title": "SnSe lattice thermal conductivity",
            "full_text": "Open Access This article is licensed under a Creative Commons Attribution 4.0.",
            "fulltext_source": "grobid",
            "source": "sciverse",
        }
    ]
    gaps = [
        {
            "id": "g1",
            "evidence_chain": [
                {
                    "paper_id": "p1",
                    "location": "fulltext",
                    "quote_or_basis": "Open Access This article is licensed under a Creative Commons Attribution 4.0.",
                    "provenance": {"pdf_hash": "abc", "chunk_id": "c1"},
                }
            ],
        }
    ]
    (tmp_path / "papers.json").write_text(json.dumps(papers), encoding="utf-8")
    (tmp_path / "gaps.json").write_text(json.dumps(gaps), encoding="utf-8")
    (tmp_path / "fulltext_index.json").write_text(
        json.dumps([{"paper_id": "p1", "fulltext_source": "grobid", "pdf_hash": "abc"}]),
        encoding="utf-8",
    )
    (tmp_path / "optimization_metrics.json").write_text(
        json.dumps(
            {
                "topic_hit_rate": 1,
                "gap_material_alignment": 1,
                "evidence_boilerplate_rate": 1,
                "provenance_coverage": 1,
                "pass_flags": {},
                "fulltext_ratio": 1,
                "n_papers": 1,
                "n_gaps": 1,
            }
        ),
        encoding="utf-8",
    )
    cfg = AppConfig(topic="SnSe", quality=QualityConfig(min_fulltext_paper_ratio=0.0))
    report = verify_run(tmp_path, cfg, profile_name="t", config_path="x.yaml")
    assert report["status"] == "FAIL"
    boiler = next(c for c in report["checks"] if c["name"] == "no_boilerplate_evidence")
    assert boiler["pass"] is False


def test_u8_canonical_parser_label() -> None:
    assert canonical_fulltext_source("grobid_fusion") == "grobid"
    assert is_parser_derived_source("grobid_fusion")
    assert not is_parser_derived_source("local_cache")


def test_u1_objective_does_not_overwrite_verify(tmp_path: Path, monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "objective_review_run", ROOT / "scripts" / "objective_review_run.py"
    )
    assert spec and spec.loader
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)

    (tmp_path / "papers.json").write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / "gaps.json").write_text(json.dumps([]), encoding="utf-8")
    (tmp_path / "fulltext_index.json").write_text(json.dumps([]), encoding="utf-8")
    original = {"profile": "production_sciverse", "status": "PASS", "checks": []}
    (tmp_path / "production_verification.json").write_text(json.dumps(original), encoding="utf-8")
    obj.run_verify_like(tmp_path, min_ratio=0.0)
    kept = json.loads((tmp_path / "production_verification.json").read_text(encoding="utf-8"))
    assert kept["profile"] == "production_sciverse"
    shadow = json.loads((tmp_path / "objective_verify_shadow.json").read_text(encoding="utf-8"))
    assert shadow["profile"] == "objective_review"


def test_u15_property_tokens_come_from_ontology() -> None:
    ontology = load_ontology(ROOT / "configs/ontologies/thermoelectrics.yaml")
    tokens = topic_property_tokens(
        "SnSe lattice thermal conductivity vacancy engineering", ontology
    )
    assert "vacancy" in tokens
    assert "lattice" in tokens
    custom = topic_property_tokens(
        "perovskite bandgap stability",
        {"property_focus": ["bandgap", "stability"], "properties": []},
    )
    assert "bandgap" in custom
    assert "stability" in custom
