#!/usr/bin/env python3
"""Build a slim materials Sci-Base cache from Hugging Face.

Example:
  py -3 scripts/build_scibase_cache.py --max-scan 3000 --max-keep 120
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.tools.scibase_client import (  # noqa: E402
    DEFAULT_CACHE,
    DEFAULT_CONFIG,
    DEFAULT_DATASET,
    build_materials_cache,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Build Sci-Base materials cache")
    p.add_argument("--out", default=DEFAULT_CACHE)
    p.add_argument("--dataset", default=DEFAULT_DATASET)
    p.add_argument("--config", default=DEFAULT_CONFIG)
    p.add_argument("--max-scan", type=int, default=5000)
    p.add_argument("--max-keep", type=int, default=200)
    p.add_argument(
        "--keywords",
        default="SnSe thermoelectric vacancy lattice thermal conductivity materials",
    )
    args = p.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    stats = build_materials_cache(
        out,
        dataset=args.dataset,
        config=args.config,
        max_scan=args.max_scan,
        max_keep=args.max_keep,
        keyword_boost=args.keywords,
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
