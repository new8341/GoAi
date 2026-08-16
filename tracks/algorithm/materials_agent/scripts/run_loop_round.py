#!/usr/bin/env python
"""Run one survey + objective review round for the six-round optimization loop."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.pipeline import LiteratureSurveyAgent
from scripts.objective_review_run import main as _unused  # noqa: F401 — ensure importable
from scripts import objective_review_run as objrev


TOPICS = [
    "SnSe lattice thermal conductivity vacancy engineering",
    "Bi2Te3 phonon scattering grain boundary thermoelectric",
    "PbTe resonant doping Seebeck coefficient thermoelectric",
    "Mg3Sb2 n-type thermoelectric lattice thermal conductivity",
    "GeTe phase transition thermoelectric figure of merit ZT",
    "half-Heusler thermoelectric power factor DFT",
]


def run_round(round_idx: int, topic: str, config_path: Path) -> dict:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = ROOT / "outputs" / "loop_rounds" / f"r{round_idx}-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    raw["topic"] = topic
    raw["output_dir"] = str(run_dir.relative_to(ROOT)).replace("\\", "/")
    raw["run_name"] = f"loop_r{round_idx}"
    tmp = run_dir / "_config.yaml"
    tmp.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")

    cfg = load_config(tmp)
    agent = LiteratureSurveyAgent(cfg)
    bundle = agent.run()
    agent.save(bundle, run_dir)

    # Objective review (reuse module functions)
    run_id = str(run_dir.relative_to(ROOT / "outputs")).replace("\\", "/")
    verify = objrev.run_verify_like(run_dir, min_ratio=0.5)
    science = None
    try:
        import os
        import subprocess

        proc = subprocess.run(
            [
                "py",
                "-3",
                str(ROOT / "scripts/science_review_gate.py"),
                "-c",
                str(ROOT / "configs/production.yaml"),
                "--run",
                str(run_dir),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(ROOT)},
            timeout=180,
        )
        science = objrev._load(run_dir, "science_review.json")
        if science is None and proc.returncode not in (0, 1):
            science = {"status": "ERROR", "detail": (proc.stderr or "")[-500:]}
    except Exception as exc:  # noqa: BLE001
        science = {"status": "ERROR", "detail": str(exc)}

    pack = objrev.build_expert_review_pack(run_dir, run_id=run_id)
    objrev.write_expert_review_pack(run_dir, run_id=run_id)
    verdicts = objrev.auto_judge(run_dir, pack)
    summary = objrev.summarize(verdicts)

    out = {
        "round": round_idx,
        "topic": topic,
        "run_dir": str(run_dir),
        "run_id": run_id,
        "n_papers": len(bundle.papers),
        "n_gaps": len(bundle.gaps),
        "gap_ids": [g.id for g in bundle.gaps],
        "fulltext_papers": sum(1 for p in bundle.papers if p.full_text),
        "verify": verify,
        "science_review": {
            "status": (science or {}).get("status"),
            "one_liner": (science or {}).get("one_liner"),
        },
        "summary": summary,
        "must_fail": summary.get("must_fail") or [],
    }
    (run_dir / "round_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    # also write objective_review.json for parity
    obj_path = run_dir / "objective_review.json"
    obj_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "topic": topic,
                "reviewer": "auto-objective",
                "verify": verify,
                "science_review": out["science_review"],
                "summary": summary,
                "verdicts": verdicts,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, required=True, choices=range(1, 7))
    parser.add_argument("--topic", type=str, default="")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs/loop_six_round.yaml",
    )
    args = parser.parse_args()
    topic = args.topic.strip() or TOPICS[args.round - 1]
    print(json.dumps({"phase": "start", "round": args.round, "topic": topic}, ensure_ascii=False))
    result = run_round(args.round, topic, args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("summary", {}).get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
