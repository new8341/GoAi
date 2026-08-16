#!/usr/bin/env python
"""Export an existing survey run to report.tex + references.bib (+ optional PDF)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.export.latex_report import export_survey_latex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "run_dir",
        type=Path,
        nargs="?",
        default=ROOT / "outputs" / "production_sciverse",
        help="Survey run directory containing papers.json / gaps.json",
    )
    parser.add_argument("--no-pdf", action="store_true", help="Skip PDF compilation")
    parser.add_argument("-o", "--out-dir", type=Path, default=None)
    args = parser.parse_args()
    result = export_survey_latex(
        args.run_dir,
        compile_pdf=not args.no_pdf,
        out_dir=args.out_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if Path(result["tex"]).is_file() and Path(result["bib"]).is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
