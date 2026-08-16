#!/usr/bin/env python
"""Write external_versions.json for a run directory (or from a config profile)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.export.versions import dump_external_versions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Optional YAML profile (fills seed/backend/topic)",
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        default=None,
        help="Output directory (default: config.output_dir or outputs/)",
    )
    args = parser.parse_args()
    cfg = load_config(args.config) if args.config else None
    if args.out_dir:
        out = args.out_dir
    elif cfg:
        out = Path(cfg.output_dir)
        if not out.is_absolute():
            out = ROOT / out
    else:
        out = ROOT / "outputs" / "production_sciverse"
    path = dump_external_versions(
        out,
        cfg,
        profile_name=args.config.stem if args.config else out.name,
    )
    print(json.dumps(json.loads(path.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
