#!/usr/bin/env python3
"""Re-validate Route A top candidates with Materials Project + OQMD."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.tools.materials_db import validate_motif


def main() -> int:
    src = ROOT / "outputs" / "production_route_a" / "route_a_spr_candidates.json"
    if not src.is_file():
        print(f"missing {src}", file=sys.stderr)
        return 1
    cfg = load_config(ROOT / "configs" / "production_route_a.yaml")
    cfg.route_a.materials_db = "mp_oqmd"
    cfg.materials_db.provider = "mp_oqmd"
    cfg.materials_db.allow_offline_fallback = False

    cands = json.loads(src.read_text(encoding="utf-8"))
    rows = []
    for c in cands[:5]:
        motif = c.get("material_motif") or ""
        r = validate_motif(motif, cfg)
        rows.append(
            {
                "motif": motif,
                "hypothesis": (c.get("hypothesis") or "")[:120],
                "validation": r.__dict__,
            }
        )
    out_dir = ROOT / "outputs" / "production_route_a"
    out = out_dir / "route_a_external_validation_mp_oqmd.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    md = [
        "# Route A 外验：Materials Project + OQMD",
        "",
        f"> Source candidates: `{src.as_posix()}`",
        "",
        "| Motif | Verdict | Provider | Detail |",
        "|-------|---------|----------|--------|",
    ]
    for row in rows:
        v = row["validation"]
        md.append(
            f"| `{row['motif'][:40]}` | {v.get('verdict')} | {v.get('provider')} | "
            f"{str(v.get('detail') or '')[:80].replace('|', '/')} |"
        )
    md.append("")
    md_path = ROOT.parents[2] / "submissions" / "semi_final" / "route_a_mp_oqmd.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {out} and {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
