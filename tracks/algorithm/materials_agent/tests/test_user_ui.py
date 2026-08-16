"""Smoke tests for user black-box API helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "serve_viewer.py"


def _load():
    spec = importlib.util.spec_from_file_location("serve_viewer", MODULE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_user_and_debug_assets_exist() -> None:
    assert (ROOT / "user" / "index.html").is_file()
    assert (ROOT / "user" / "app.js").is_file()
    assert (ROOT / "viewer" / "index.html").is_file()


def test_sanitize_hides_audit_and_parser_fields() -> None:
    mod = _load()
    paper = SimpleNamespace(
        id="P1",
        title="Title",
        year=2020,
        doi="10.1/x",
        venue="J",
        cited_by=3,
        abstract="A" * 400,
        full_text="full text here",
    )
    span = SimpleNamespace(
        paper_id="P1",
        claim="c",
        quote_or_basis="quote",
        confidence=0.8,
        location="fulltext",
        provenance={"pdf_hash": "secret-hash", "chunk_id": "P1:0"},
    )
    gap = SimpleNamespace(
        id="G1",
        title="Gap",
        description="d",
        gap_type="underexplored",
        novelty=0.5,
        actionability=0.6,
        review_status="accepted",
        supporting_paper_ids=["P1"],
        contradicting_paper_ids=[],
        suggested_next_step="next",
        falsification_test="falsify",
        evidence_chain=[span],
    )
    bundle = SimpleNamespace(
        topic="topic",
        subfield="thermoelectrics",
        query_variants=["q1"],
        papers=[paper],
        gaps=[gap],
        consistency=SimpleNamespace(ok=True, issues=[]),
        report_markdown="# report",
        audit=[SimpleNamespace(step="x")],
    )
    result = mod.sanitize_user_result(bundle, output_dir="outputs/x")
    blob = str(result)
    assert "secret-hash" not in blob
    assert "audit" not in result
    assert result["gaps"][0]["evidence"][0]["quote"] == "quote"
    assert result["papers"][0]["abstract_preview"].endswith("…")


def test_related_docs_and_artifacts() -> None:
    mod = _load()
    docs = mod.related_docs()
    assert docs
    assert any(d["id"] == "usage" for d in docs)
    assert all(d["url"].startswith("/api/docs/") for d in docs)
    arts = mod.artifact_links("outputs/production_sciverse")
    # production_sciverse may or may not exist in CI; function should not crash
    assert isinstance(arts, list)
    if (ROOT / "outputs" / "production_sciverse" / "report.md").is_file():
        assert any(a["name"] == "report.md" for a in arts)
        assert arts[0]["url"].startswith("/api/run/production_sciverse/")


def test_sanitize_includes_doc_links() -> None:
    mod = _load()
    paper = SimpleNamespace(
        id="P1",
        title="Title",
        year=2020,
        doi="10.1/x",
        venue="J",
        cited_by=3,
        abstract="A" * 400,
        full_text="full text here",
    )
    gap = SimpleNamespace(
        id="G1",
        title="Gap",
        description="d",
        gap_type="underexplored",
        novelty=0.5,
        actionability=0.6,
        review_status="accepted",
        supporting_paper_ids=["P1"],
        contradicting_paper_ids=[],
        suggested_next_step="next",
        falsification_test="falsify",
        evidence_chain=[],
    )
    bundle = SimpleNamespace(
        topic="topic",
        subfield="thermoelectrics",
        query_variants=["q1"],
        papers=[paper],
        gaps=[gap],
        consistency=SimpleNamespace(ok=True, issues=[]),
        report_markdown="# report",
        audit=[],
    )
    result = mod.sanitize_user_result(bundle, output_dir="outputs/production_sciverse")
    assert "docs" in result
    assert "artifacts" in result
    assert result["debug_url"].startswith("/debug/")


def test_public_from_run_missing() -> None:
    mod = _load()
    try:
        mod._public_from_run("__no_such_run__")
        raise AssertionError("expected FileNotFoundError")
    except FileNotFoundError:
        pass


def test_create_job_rejects_short_topic() -> None:
    mod = _load()
    try:
        mod.create_job({"topic": "ab", "profile": "quick"})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "3" in str(exc)
