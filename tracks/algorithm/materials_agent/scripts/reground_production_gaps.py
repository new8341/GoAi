"""Deprecated wrapper → scripts/maintenance/reground_production_gaps.py"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

print(
    "WARNING: moved to scripts/maintenance/reground_production_gaps.py",
    file=sys.stderr,
)
runpy.run_path(
    str(Path(__file__).resolve().parent / "maintenance" / "reground_production_gaps.py"),
    run_name="__main__",
)
