#!/usr/bin/env python
"""Run Route A SPR search on an existing survey output directory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.models import SurveyBundle
from materials_agent.routes.route_a import RouteASearcher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=ROOT / "configs/production_route_a.yaml",
    )
    parser.add_argument(
        "--bundle-dir",
        type=Path,
        default=ROOT / "outputs/production",
        help="Directory containing bundle.json from a prior survey run",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: config.output_dir)",
    )
    args = parser.parse_args()
    cfg = load_config(args.config)
    cfg.route_a.enabled = True

    bundle_path = args.bundle_dir / "bundle.json"
    if not bundle_path.is_file():
        print(json.dumps({"status": "FAIL", "missing": str(bundle_path)}))
        return 1

    bundle = SurveyBundle.model_validate_json(
        bundle_path.read_text(encoding="utf-8")
    )
    print(f"[route_a] bundle={bundle_path} llm={cfg.llm.enabled}", flush=True)
    searcher = RouteASearcher(cfg, bundle)
    candidates = searcher.run()
    out = args.out or (ROOT / cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    searcher.save(candidates, out)

    roles = sorted({role for c in candidates for role in c.role_trace})
    validations = [
        (c.external_validation or {}).get("verdict")
        for c in candidates
        if c.external_validation
    ]
    providers = sorted(
        {
            (c.external_validation or {}).get("provider")
            for c in candidates
            if c.external_validation
        }
    )
    report = {
        "status": "OK",
        "candidates": len(candidates),
        "roles_seen": roles,
        "external_verdicts": validations,
        "external_providers": providers,
        "llm_enabled": searcher.llm.enabled,
        "llm_audit_tail": searcher.llm.call_audit[-5:],
        "output_dir": str(out.resolve()),
    }
    (out / "route_a_run_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    has_llm_roles = any(
        r.startswith("llm_") and not r.endswith("_unavailable") for r in roles
    )
    has_real_mp = "materials_project" in providers and any(
        v in {"pass", "fail"} for v in validations
    )
    return 0 if has_real_mp else 2 if has_llm_roles else 1


if __name__ == "__main__":
    raise SystemExit(main())
