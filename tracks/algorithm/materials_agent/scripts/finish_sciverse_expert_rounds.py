"""Deprecated wrapper → scripts/maintenance/finish_sciverse_expert_rounds.py"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

print(
    "WARNING: moved to scripts/maintenance/finish_sciverse_expert_rounds.py",
    file=sys.stderr,
)
runpy.run_path(
    str(Path(__file__).resolve().parent / "maintenance" / "finish_sciverse_expert_rounds.py"),
    run_name="__main__",
)
