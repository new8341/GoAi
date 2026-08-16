"""Deprecated wrapper → scripts/maintenance/build_sciverse_verify_bundle.py"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

print(
    "WARNING: moved to scripts/maintenance/build_sciverse_verify_bundle.py",
    file=sys.stderr,
)
runpy.run_path(
    str(Path(__file__).resolve().parent / "maintenance" / "build_sciverse_verify_bundle.py"),
    run_name="__main__",
)
