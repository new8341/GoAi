#!/usr/bin/env python
"""Recompute full optimization_metrics.json from papers/gaps (no network)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config, load_ontology
from materials_agent.models import ExtractedRecord, Paper, ResearchGap
from materials_agent.topic_focus import REQUIRED_METRIC_KEYS, compute_optimization_metrics


def refresh(run_dir: Path, config: Path | None = None) -> dict:
    papers = [Paper.model_validate(p) for p in json.loads((run_dir / "papers.json").read_text(encoding="utf-8"))]
    gaps = [ResearchGap.model_validate(g) for g in json.loads((run_dir / "gaps.json").read_text(encoding="utf-8"))]
    extractions = None
    ext_path = run_dir / "extractions.json"
    if ext_path.is_file():
        extractions = [ExtractedRecord.model_validate(e) for e in json.loads(ext_path.read_text(encoding="utf-8"))]
    topic = "SnSe lattice thermal conductivity vacancy engineering"
    ontology = {}
    if config and config.is_file():
        cfg = load_config(config)
        topic = cfg.topic
        ontology = load_ontology(cfg.ontology_path)
    elif (run_dir / "bundle.json").is_file():
        bundle = json.loads((run_dir / "bundle.json").read_text(encoding="utf-8"))
        topic = bundle.get("topic") or topic
    metrics = compute_optimization_metrics(topic, papers, gaps, extractions, ontology)
    missing = REQUIRED_METRIC_KEYS - set(metrics)
    if missing:
        raise SystemExit(f"metrics missing keys: {sorted(missing)}")
    (run_dir / "optimization_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, default=ROOT / "outputs/production_sciverse")
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "configs/production_sciverse.yaml")
    args = parser.parse_args()
    metrics = refresh(args.run_dir, args.config)
    print(json.dumps({k: metrics[k] for k in sorted(REQUIRED_METRIC_KEYS)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
