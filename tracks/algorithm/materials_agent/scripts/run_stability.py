#!/usr/bin/env python
"""Multi-seed stability statistics (MLE-bench style mean ± std)."""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import typer
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.agents.evidence import quote_in_source
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.routes.route_a import RouteASearcher

app = typer.Typer(add_completion=False)


def _mean_std(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    if len(vals) == 1:
        return vals[0], 0.0
    return statistics.mean(vals), statistics.pstdev(vals)


@app.command()
def main(
    config: Path = typer.Option(ROOT / "configs/demo_local.yaml", "-c", "--config"),
    seeds: str = typer.Option("41,42,43", "--seeds", help="Comma-separated seeds"),
    out_dir: Path = typer.Option(ROOT / "outputs/stability", "--out"),
) -> None:
    seed_list = [int(x.strip()) for x in seeds.split(",") if x.strip()]
    if len(seed_list) < 3:
        raise typer.BadParameter("Need at least 3 seeds for stability (N≥3).")

    base = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    rows: list[dict] = []

    for seed in seed_list:
        cfg_dict = dict(base)
        cfg_dict["seed"] = seed
        if "route_a" in cfg_dict and isinstance(cfg_dict["route_a"], dict):
            cfg_dict["route_a"] = dict(cfg_dict["route_a"])
            cfg_dict["route_a"]["seed"] = seed
        run_out = out_dir / f"seed_{seed}"
        cfg_dict["output_dir"] = str(run_out)
        # write temp config
        tmp = out_dir / f"_tmp_seed_{seed}.yaml"
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp.write_text(yaml.safe_dump(cfg_dict, allow_unicode=True), encoding="utf-8")
        cfg = load_config(tmp)

        agent = LiteratureSurveyAgent(cfg)
        bundle = agent.run()
        agent.save(bundle, run_out)
        cands = []
        if cfg.route_a.enabled:
            cands = RouteASearcher(cfg, bundle).run()
            RouteASearcher(cfg, bundle).save(cands, run_out)

        gap_types = sorted({g.gap_type for g in bundle.gaps})
        ext_pass = sum(
            1
            for c in cands
            if (c.external_validation or {}).get("verdict") == "pass"
        )
        rows.append(
            {
                "seed": seed,
                "n_papers": len(bundle.papers),
                "n_gaps": len(bundle.gaps),
                "gap_types": gap_types,
                "n_known": len(bundle.known_pairs),
                "consistency_ok": bool(bundle.consistency and bundle.consistency.ok),
                "n_route_a": len(cands),
                "top_score": cands[0].score if cands else None,
                "ext_pass": ext_pass,
                "fulltext_ev": sum(
                    1
                    for e in bundle.extractions
                    for ev in e.evidence
                    if ev.location == "fulltext"
                ),
                "gap_fulltext_ratio": (
                    sum(
                        1
                        for gap in bundle.gaps
                        for ev in gap.evidence_chain
                        if ev.location in {"fulltext", "chunk"}
                    )
                    / max(1, sum(len(gap.evidence_chain) for gap in bundle.gaps))
                ),
                "quote_in_source_ratio": (
                    sum(
                        1
                        for gap in bundle.gaps
                        for ev in gap.evidence_chain
                        if quote_in_source(
                            ev.quote_or_basis,
                            next(
                                (
                                    paper.full_text or paper.abstract or paper.title
                                    for paper in bundle.papers
                                    if paper.id == ev.paper_id
                                ),
                                "",
                            ),
                            ev.provenance,
                        )
                    )
                    / max(1, sum(len(gap.evidence_chain) for gap in bundle.gaps))
                ),
            }
        )
        tmp.unlink(missing_ok=True)

    n_gaps = [float(r["n_gaps"]) for r in rows]
    top_scores = [float(r["top_score"]) for r in rows if r["top_score"] is not None]
    fulltext = [float(r["fulltext_ev"]) for r in rows]
    gap_fulltext = [float(r["gap_fulltext_ratio"]) for r in rows]
    quote_rates = [float(r["quote_in_source_ratio"]) for r in rows]
    mg, sg = _mean_std(n_gaps)
    mt, st = _mean_std(top_scores)
    mf, sf = _mean_std(fulltext)
    mgf, sgf = _mean_std(gap_fulltext)
    mqs, sqs = _mean_std(quote_rates)

    # type-set Jaccard stability across seeds
    type_sets = [set(r["gap_types"]) for r in rows]
    jaccards: list[float] = []
    for i in range(len(type_sets)):
        for j in range(i + 1, len(type_sets)):
            a, b = type_sets[i], type_sets[j]
            jaccards.append(len(a & b) / max(1, len(a | b)))
    mj, sj = _mean_std(jaccards)

    summary = {
        "seeds": seed_list,
        "n_runs": len(rows),
        "runs": rows,
        "metrics": {
            "n_gaps_mean": round(mg, 3),
            "n_gaps_std": round(sg, 3),
            "route_a_top_score_mean": round(mt, 3) if top_scores else None,
            "route_a_top_score_std": round(st, 3) if top_scores else None,
            "fulltext_evidence_mean": round(mf, 3),
            "fulltext_evidence_std": round(sf, 3),
            "gap_fulltext_ratio_mean": round(mgf, 3),
            "gap_fulltext_ratio_std": round(sgf, 3),
            "quote_in_source_ratio_mean": round(mqs, 3),
            "quote_in_source_ratio_std": round(sqs, 3),
            "gap_type_jaccard_mean": round(mj, 3),
            "gap_type_jaccard_std": round(sj, 3),
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stability_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Multi-seed stability",
        "",
        f"Seeds: `{seed_list}` (N={len(seed_list)})",
        "",
        "| Metric | Mean | Std |",
        "|--------|------|-----|",
        f"| n_gaps | {mg:.3f} | {sg:.3f} |",
        f"| route_a top score | {mt:.3f} | {st:.3f} |" if top_scores else "| route_a top score | n/a | n/a |",
        f"| fulltext evidence count | {mf:.3f} | {sf:.3f} |",
        f"| Gap fulltext evidence ratio | {mgf:.3f} | {sgf:.3f} |",
        f"| Quote-in-source ratio | {mqs:.3f} | {sqs:.3f} |",
        f"| gap-type Jaccard | {mj:.3f} | {sj:.3f} |",
        "",
        "Per-seed details in `stability_summary.json`.",
    ]
    (out_dir / "stability_report.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary["metrics"], ensure_ascii=False, indent=2))
    print(f"Wrote {out_dir / 'stability_report.md'}")


if __name__ == "__main__":
    app()
