#!/usr/bin/env python
"""Strict verifier for the OA PDF → parser → evidence production profile."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.agents.evidence import quote_in_source
from materials_agent.agents.evidence_selector import is_boilerplate_text
from materials_agent.config import AppConfig, load_config
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.topic_focus import REQUIRED_METRIC_KEYS
from materials_agent.tools.backend_honesty import STRICT_BACKENDS, audit_effective_backend
from materials_agent.tools.fulltext_labels import is_parser_derived_source
from materials_agent.tools.paper_titles import is_placeholder_title


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_run(out: Path, cfg: AppConfig, *, profile_name: str, config_path: str) -> dict[str, Any]:
    papers_path = out / "papers.json"
    gaps_path = out / "gaps.json"
    index_path = out / "fulltext_index.json"
    missing = [str(path) for path in (papers_path, gaps_path, index_path) if not path.is_file()]
    if missing:
        return {"status": "FAIL", "missing_artifacts": missing, "profile": profile_name}

    papers = _load_json(papers_path)
    gaps = _load_json(gaps_path)
    index = _load_json(index_path)
    paper_by_id = {paper["id"]: paper for paper in papers}
    parsed = [
        entry
        for entry in index
        if is_parser_derived_source(entry.get("fulltext_source")) and entry.get("pdf_hash")
    ]
    checks: list[tuple[str, bool, str]] = [
        ("oa_papers_available", bool(papers), f"papers={len(papers)}"),
        (
            "parsed_oa_ratio",
            len(parsed) / max(1, len(papers)) >= cfg.quality.min_fulltext_paper_ratio,
            f"parsed={len(parsed)}/{len(papers)} threshold={cfg.quality.min_fulltext_paper_ratio}",
        ),
        (
            "no_local_cache_as_production",
            not any(entry.get("fulltext_source") == "local_cache" for entry in index),
            "production accepts parser-derived fulltext only",
        ),
    ]

    fulltext_spans = 0
    invalid_spans: list[str] = []
    boilerplate_spans: list[str] = []
    for gap in gaps:
        for span in gap.get("evidence_chain") or []:
            if span.get("location") not in {"fulltext", "chunk"}:
                invalid_spans.append(f"{gap.get('id')}:non_fulltext")
                continue
            fulltext_spans += 1
            provenance = span.get("provenance") or {}
            paper = paper_by_id.get(span.get("paper_id")) or {}
            source = paper.get("full_text") or ""
            quote = span.get("quote_or_basis") or ""
            if is_boilerplate_text(quote, provenance.get("section")):
                boilerplate_spans.append(f"{gap.get('id')}:boilerplate")
            if not provenance.get("pdf_hash") or not provenance.get("chunk_id"):
                invalid_spans.append(f"{gap.get('id')}:missing_provenance")
            elif not quote_in_source(quote, source):
                invalid_spans.append(f"{gap.get('id')}:quote_not_in_source")
    checks.append(("fulltext_gap_spans", fulltext_spans > 0, f"count={fulltext_spans}"))
    checks.append(("verifiable_gap_spans", not invalid_spans, "; ".join(invalid_spans[:20])))
    checks.append(
        (
            "no_boilerplate_evidence",
            not boilerplate_spans,
            "ok" if not boilerplate_spans else "; ".join(boilerplate_spans[:20]),
        )
    )

    placeholder = [
        f"{p.get('id')}"
        for p in papers
        if is_placeholder_title(p.get("title"), p.get("id") or "")
    ]
    checks.append(
        (
            "no_placeholder_titles",
            not placeholder,
            "ok" if not placeholder else ",".join(placeholder[:8]),
        )
    )

    metrics_path = out / "optimization_metrics.json"
    if metrics_path.is_file():
        metrics = _load_json(metrics_path)
        missing_keys = sorted(REQUIRED_METRIC_KEYS - set(metrics))
        checks.append(
            (
                "optimization_metrics_contract",
                not missing_keys,
                "ok" if not missing_keys else f"missing={missing_keys}",
            )
        )
    else:
        checks.append(("optimization_metrics_contract", False, "optimization_metrics.json missing"))

    configured = cfg.retrieval.backend
    if configured in STRICT_BACKENDS and not cfg.retrieval.allow_backend_fallback:
        audit_rows = _load_json(out / "audit.json") if (out / "audit.json").is_file() else []
        effective = audit_effective_backend(audit_rows)
        sources = {str(p.get("source") or "") for p in papers}
        honest = True
        detail = f"configured={configured} effective={effective} sources={sorted(sources)}"
        if effective and effective != configured:
            honest = False
        elif not effective and sources and sources <= {"openalex"}:
            honest = False
            detail += "; papers look like silent OpenAlex"
        checks.append(("retrieval_backend_honest", honest, detail))
    else:
        checks.append(
            (
                "retrieval_backend_honest",
                True,
                f"configured={configured} allow_fallback={cfg.retrieval.allow_backend_fallback}",
            )
        )

    # Handbook: every Gap claim must name the literature database (span field or Paper.source).
    gaps_missing_db: list[str] = []
    for gap in gaps:
        chain = gap.get("evidence_chain") or []
        if not chain:
            continue
        ok_span = False
        for span in chain:
            db = (span.get("retrieval_database") or "").strip()
            if not db:
                paper = paper_by_id.get(span.get("paper_id")) or {}
                db = (paper.get("source") or "").strip()
            if db and db.lower() != "unknown":
                ok_span = True
                break
            if db:
                ok_span = True
                break
        if not ok_span:
            gaps_missing_db.append(str(gap.get("id") or "?"))
    checks.append(
        (
            "gap_database_attribution",
            not gaps_missing_db,
            "ok" if not gaps_missing_db else f"missing_db={gaps_missing_db[:12]}",
        )
    )

    passed = all(result for _, result, _ in checks)
    return {
        "profile": str(profile_name),
        "config": str(Path(config_path).as_posix()),
        "output_dir": str(out),
        "status": "PASS" if passed else "FAIL",
        "checks": [
            {"name": name, "pass": result, "detail": detail} for name, result, detail in checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "configs/production.yaml")
    parser.add_argument("--run", action="store_true", help="Run the configured pipeline before checking.")
    args = parser.parse_args()
    cfg = load_config(args.config)
    if not Path(cfg.output_dir).is_absolute():
        out = ROOT / cfg.output_dir
    else:
        out = Path(cfg.output_dir)
    profile_name = Path(args.config).stem or Path(str(cfg.output_dir)).name or "production"
    if args.run:
        agent = LiteratureSurveyAgent(cfg)
        bundle = agent.run()
        out = agent.save(bundle)

    report = verify_run(out, cfg, profile_name=profile_name, config_path=str(args.config))
    out.mkdir(parents=True, exist_ok=True)
    (out / "production_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
