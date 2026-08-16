#!/usr/bin/env python
"""Run fixed-topic ablation smoke benchmarks (local backend by default)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.pipeline import LiteratureSurveyAgent


def _set_nested(cfg_dict: dict, dotted: str, value) -> None:
    cur = cfg_dict
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def main() -> None:
    bench_path = ROOT / "experiments" / "benchmark_topics.yaml"
    base_cfg_path = ROOT / "configs" / "demo_local.yaml"
    bench = yaml.safe_load(bench_path.read_text(encoding="utf-8"))
    out_root = ROOT / "outputs" / "benchmark"
    out_root.mkdir(parents=True, exist_ok=True)

    summary = []
    for topic_item in bench["topics"][:3]:  # keep smoke run short
        for abl in bench["ablations"]:
            raw = yaml.safe_load(base_cfg_path.read_text(encoding="utf-8"))
            raw["topic"] = topic_item["topic"]
            raw["subfield"] = topic_item.get("subfield", "thermoelectrics")
            raw["route_a"]["enabled"] = False
            raw["output_dir"] = str(out_root / f"{topic_item['id']}__{abl['name']}")
            for k, v in (abl.get("overrides") or {}).items():
                _set_nested(raw, k, v)
            tmp = out_root / f"_tmp_{topic_item['id']}_{abl['name']}.yaml"
            tmp.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
            cfg = load_config(tmp)
            agent = LiteratureSurveyAgent(cfg)
            bundle = agent.run()
            agent.save(bundle)
            row = {
                "topic_id": topic_item["id"],
                "ablation": abl["name"],
                "n_papers": len(bundle.papers),
                "n_gaps": len(bundle.gaps),
                "n_known": len(bundle.known_pairs),
                "consistency_ok": None if not bundle.consistency else bundle.consistency.ok,
                "gap_types": [g.gap_type for g in bundle.gaps],
            }
            summary.append(row)
            print(row)
            tmp.unlink(missing_ok=True)

    (out_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out_root / 'summary.json'}")


if __name__ == "__main__":
    main()
