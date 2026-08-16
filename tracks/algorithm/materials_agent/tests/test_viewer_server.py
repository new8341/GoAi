"""Basic smoke checks for the HTML viewer server helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "serve_viewer.py"


def _load_viewer_module():
    spec = importlib.util.spec_from_file_location("serve_viewer", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_viewer_assets_exist() -> None:
    viewer = ROOT / "viewer"
    assert (viewer / "index.html").is_file()
    assert (viewer / "styles.css").is_file()
    assert (viewer / "app.js").is_file()


def test_safe_join_blocks_traversal(tmp_path: Path) -> None:
    mod = _load_viewer_module()
    assert mod._safe_join(tmp_path, "../secret") is None
    child = tmp_path / "ok.json"
    child.write_text("{}", encoding="utf-8")
    assert mod._safe_join(tmp_path, "ok.json") == child.resolve()


def test_attach_doc_links_adds_align_urls_and_gates() -> None:
    mod = _load_viewer_module()
    if not (mod.OUTPUTS / "production").is_dir():
        return
    payload = mod.attach_doc_links({"output_dir": "outputs/production", "topic": "t"})
    assert payload["run_id"] == "production"
    assert "run=production" in payload["debug_url"] or "run=production" in payload["debug_url"].replace("%3D", "=")
    assert payload["user_url"].startswith("/?run=")
    assert "gates" in payload
    assert "verify" in payload["gates"]


def test_outputs_rel_handles_absolute_and_nested() -> None:
    mod = _load_viewer_module()
    assert mod._outputs_rel("outputs/user_jobs/abc") == "user_jobs/abc"
    assert mod._outputs_rel(r"E:\proj\outputs\user_jobs\abc") == "user_jobs/abc"
    assert mod._outputs_rel("production") == "production"


def test_resolve_run_dir_nested_user_jobs(tmp_path: Path, monkeypatch) -> None:
    mod = _load_viewer_module()
    outputs = tmp_path / "outputs"
    job = outputs / "user_jobs" / "jid1"
    job.mkdir(parents=True)
    (job / "gaps.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(mod, "OUTPUTS", outputs)
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    assert mod._resolve_run_dir("user_jobs/jid1") == job.resolve()
    assert mod._resolve_run_dir("../etc") is None


def test_expert_review_pack_smoke() -> None:
    from materials_agent.expert_review_pack import build_expert_review_pack

    run = ROOT / "outputs" / "production"
    if not (run / "gaps.json").is_file():
        return
    pack = build_expert_review_pack(run, run_id="production")
    assert pack["summary"]["total_checks"] > 0
    assert pack["standards_doc"]["standards"]


def test_route_a_save_writes_summary(tmp_path: Path) -> None:
    from materials_agent.config import AppConfig
    from materials_agent.models import SurveyBundle
    from materials_agent.routes.route_a import RouteASearcher, SPRCandidate

    cfg = AppConfig(topic="t")
    bundle = SurveyBundle(topic="t", subfield="x", papers=[], extractions=[], gaps=[])
    searcher = RouteASearcher(cfg, bundle)
    cand = SPRCandidate(
        hypothesis="h",
        material_motif="SnSe",
        property_target="kappa",
        mechanism="vacancy",
        score=0.5,
        llm_plausibility=0.5,
        gap_alignment=0.5,
        novelty_label="candidate_new",
        evidence_paper_ids=[],
        generation=0,
        role_trace=["seed", "score"],
        external_validation={"verdict": "n/a", "provider": "offline"},
    )
    out = searcher.save([cand], tmp_path)
    assert (out / "route_a_run_summary.json").is_file()
    assert (out / "route_a_spr_candidates.json").is_file()
