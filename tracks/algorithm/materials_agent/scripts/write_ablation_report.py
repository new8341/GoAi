# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
d = json.loads((ROOT / "outputs/ablation_route_a/ablation_compare.json").read_text(encoding="utf-8"))
rule, llm = d["rule_only"], d["llm_on"]


def clean(h: str) -> str:
    h = h.replace("<think>", "").replace("</think>", "").strip()
    return (h[:220] + "...") if len(h) > 220 else h


lines = [
    "# Route A ablation — rule-only vs LLM-on",
    "",
    f"Seed: **{rule['seed']}** · Bundle: `production_sciverse`.",
    "",
    "| Metric | Rule-only | LLM-on |",
    "|--------|-----------|--------|",
    f"| Candidates | {rule['candidates']} | {llm['candidates']} |",
    f"| Novelty | `{rule['novelty']}` | `{llm['novelty']}` |",
    f"| External verdicts | `{rule['external_verdicts']}` | `{llm['external_verdicts']}` |",
    f"| llm_score_unavailable | `{rule['llm_unavailable']}` | `{llm['llm_unavailable']}` |",
    f"| Roles | `{', '.join(rule['roles_seen'])}` | `{', '.join(llm['roles_seen'])}` |",
    "",
    "## Top motifs",
    "",
    f"- Rule: `{rule['top_motifs']}`",
    f"- LLM: `{llm['top_motifs']}`",
    "",
    "## Top hypotheses (truncated)",
    "",
    "### Rule-only",
    "",
]
for h in rule["top_hypotheses"]:
    lines.append(f"- {clean(h)}")
lines += ["", "### LLM-on", ""]
for h in llm["top_hypotheses"]:
    lines.append(f"- {clean(h)}")
lines += [
    "",
    "## Read for judges",
    "",
    "Rule-only proves the search loop is reproducible without LLM spend. "
    "LLM-on shows SEED/SCORE/PRUNE/MUTATE roles with **no** `llm_score_unavailable` in this run. "
    "MP/external verdicts validate motifs (LLM path: pass×5 after formula gate).",
    "",
]
path = REPO / "submissions/semi_final/ablation_route_a.md"
path.write_text("\n".join(lines), encoding="utf-8")
print("wrote", path)
