# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
gaps = json.loads((ROOT / "outputs/production_sciverse/gaps.json").read_text(encoding="utf-8"))
lines = [
    "# L2 真人抽检归档（复赛 · 草案待签字）",
    "",
    "> 标准：`experiments/reviews/专家级真人核对标准.md`  ",
    "> 跑次：`outputs/production_sciverse`  ",
    "> 工程预填基于 L0/verify PASS；**领域专家签字后升格正式 L2**。",
    "",
]
for i, g in enumerate(gaps[:3], 1):
    dbs = sorted(
        {
            (e.get("retrieval_database") or "unknown")
            for e in (g.get("evidence_chain") or [])
        }
    )
    lines += [
        f"## Gap-{i}: `{g.get('id')}`",
        "",
        f"- Title: {g.get('title')}",
        f"- Type: `{g.get('gap_type')}` · novelty={g.get('novelty')} · actionability={g.get('actionability')}",
        f"- Databases: {', '.join(f'`{d}`' for d in dbs) or '`unknown`'}",
        f"- Supporting papers: {', '.join(f'`{p}`' for p in (g.get('supporting_paper_ids') or [])[:6]) or '—'}",
        f"- Next step: {g.get('suggested_next_step') or '—'}",
        f"- Falsification: {g.get('falsification_test') or '—'}",
        "- E2 quote-in-source: covered by production verify PASS",
        "- 判决（真人）：□ 同意 □ 修订 □ 拒绝 · 签字：________ 日期：________",
        "",
    ]
lines += [
    "UI：`py -3 scripts/serve_viewer.py` → 专家核对。",
    "",
]
path = ROOT / "experiments/reviews/l2-draft-20260812-production_sciverse.md"
path.write_text("\n".join(lines), encoding="utf-8")
print("wrote", path)
