#!/usr/bin/env python
"""Acceptance checks against readme_agent.md optimization expectations."""
from __future__ import annotations

import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.agents.evidence import quote_in_source
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.routes.route_a import RouteASearcher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "configs" / "demo_local.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    agent = LiteratureSurveyAgent(cfg)
    bundle = agent.run()
    agent.save(bundle)
    cands = RouteASearcher(cfg, bundle).run()

    checks = []

    def ok(name: str, cond: bool, detail: str = "") -> None:
        checks.append((name, cond, detail))
        status = "PASS" if cond else "FAIL"
        print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))

    types = {g.gap_type for g in bundle.gaps}
    ok("consistency_pass", bool(bundle.consistency and bundle.consistency.ok))
    ok("known_pairs_nonempty", len(bundle.known_pairs) > 0, str(len(bundle.known_pairs)))
    ok("has_contradiction_gap", "contradiction" in types, str(types))
    ok("has_method_or_underexplored", bool(types & {"method_gap", "underexplored"}), str(types))
    ok(
        "all_gaps_have_next_and_falsify",
        all(g.suggested_next_step and g.falsification_test for g in bundle.gaps),
    )
    ok(
        "all_gaps_have_evidence",
        all(len(g.evidence_chain) > 0 for g in bundle.gaps),
    )
    fulltext_spans = [
        ev for gap in bundle.gaps for ev in gap.evidence_chain if ev.location in {"fulltext", "chunk"}
    ]
    quote_hits = [
        quote_in_source(
            ev.quote_or_basis,
            next(
                (paper.full_text or paper.abstract or paper.title for paper in bundle.papers if paper.id == ev.paper_id),
                "",
            ),
            ev.provenance,
        )
        for gap in bundle.gaps
        for ev in gap.evidence_chain
    ]
    if cfg.quality.require_fulltext_gap_evidence:
        ok("fulltext_gap_evidence", len(fulltext_spans) > 0, str(len(fulltext_spans)))
    if cfg.quality.require_quote_substring:
        ok(
            "gap_quote_in_source",
            bool(quote_hits) and all(quote_hits),
            f"{sum(quote_hits)}/{len(quote_hits)}",
        )
    ok(
        "limitations_retained",
        sum(1 for e in bundle.extractions if e.limitations) >= 3,
        str(sum(1 for e in bundle.extractions if e.limitations)),
    )
    ok("query_rewrite_variants", len(bundle.query_variants) >= 3, str(len(bundle.query_variants)))
    ok("no_seed_mechanism_leak", all("governed by seed" not in c.hypothesis for c in cands), 
       cands[0].hypothesis[:80] if cands else "no cand")
    ok(
        "route_a_has_novelty_label",
        all(c.novelty_label in {"known", "candidate_new", "uncertain"} for c in cands),
    )
    # no empty generic temporal-only gap
    ok(
        "no_vague_temporal_only",
        not any("paradigm shift between early and recent" in g.title.lower() for g in bundle.gaps),
    )

    failed = [n for n, c, _ in checks if not c]
    out = ROOT / cfg.output_dir / "acceptance.json"
    out.write_text(
        json.dumps(
            [{"name": n, "pass": c, "detail": d} for n, c, d in checks],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{len(checks) - len(failed)}/{len(checks)} passed → {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
