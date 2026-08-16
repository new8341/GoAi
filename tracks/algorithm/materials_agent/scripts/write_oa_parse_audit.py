# -*- coding: utf-8 -*-
"""Write semi-final OA parse audit from production_sciverse artifacts."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
out = ROOT / "outputs" / "production_sciverse"
idx = json.loads((out / "fulltext_index.json").read_text(encoding="utf-8"))
papers = json.loads((out / "papers.json").read_text(encoding="utf-8"))
src = Counter(e.get("fulltext_source") or "none" for e in idx)
parsed = sum(
    1
    for e in idx
    if e.get("fulltext_source") in {"grobid", "mineru", "grobid_fusion"} and e.get("pdf_hash")
)
lines = [
    "# OA fulltext parse audit (production_sciverse)",
    "",
    f"Papers: **{len(papers)}**; parser-derived with `pdf_hash`: **{parsed}/{len(papers)}**.",
    "",
    "| Paper | fulltext_source | has_pdf_hash | note |",
    "|-------|-----------------|--------------|------|",
]
by = {e["paper_id"]: e for e in idx}
for p in papers:
    e = by.get(p["id"], {})
    src_ = e.get("fulltext_source") or "none"
    ok = bool(e.get("pdf_hash")) and src_ in {"grobid", "mineru", "grobid_fusion"}
    note = "parsed OK" if ok else "no OA parse / unreachable / not used as production evidence"
    lines.append(
        f"| `{p['id']}` | `{src_}` | `{bool(e.get('pdf_hash'))}` | {note} |"
    )
lines += [
    "",
    "## Counts",
    "",
    f"- source histogram: `{dict(src)}`",
    "",
    "Semi-final policy: raise parsed ratio via legal OA mirrors only, or document each miss "
    "(403 / no-OA / parse fail). Never scrape paywalls or claim abstract as production fulltext.",
    "",
]
dest = REPO / "submissions" / "semi_final" / "oa_parse_audit.md"
dest.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {dest} parsed={parsed}/{len(papers)}")
