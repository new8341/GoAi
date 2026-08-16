#!/usr/bin/env python
"""Pre-survey platform healthcheck (green / yellow / red). Does not print secrets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config


def _status(ok: bool, warn: bool = False) -> str:
    if ok:
        return "green"
    return "yellow" if warn else "red"


def check_http(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code < 500, f"HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, str(exc)[:160]


def run_healthcheck(config: Path) -> dict:
    cfg = load_config(config)
    grobid_url = cfg.fulltext.parsers.grobid_url.rstrip("/") + "/api/isalive"
    qdrant_url = cfg.fulltext.index.qdrant_url.rstrip("/") + "/readyz"
    grobid_needed = cfg.fulltext.parsers.primary.lower() == "grobid" or (
        cfg.fulltext.parsers.secondary.lower() == "grobid"
    )
    grobid_ok, grobid_detail = check_http(grobid_url)
    qdrant_ok, qdrant_detail = check_http(qdrant_url)
    qdrant_store = ROOT / "data" / "qdrant"
    baidu_junk = []
    if qdrant_store.is_dir():
        baidu_junk = [str(p.relative_to(ROOT)) for p in qdrant_store.rglob("*.baiduyun.uploading.cfg")]

    token = bool((cfg.retrieval.sciverse_api_token or os.environ.get("SCIVERSE_API_TOKEN") or "").strip())
    s2 = bool((cfg.retrieval.semantic_scholar_api_key or os.environ.get("S2_API_KEY") or "").strip())
    openai = bool((cfg.llm.api_key or os.environ.get("OPENAI_API_KEY") or "").strip())
    mp = bool((cfg.materials_db.mp_api_key or os.environ.get("MP_API_KEY") or "").strip())

    windows = sys.platform.startswith("win")
    mineru_primary = cfg.fulltext.parsers.primary.lower() == "mineru"
    mineru_warn = windows and mineru_primary

    checks = [
        {
            "name": "grobid",
            "status": _status(grobid_ok) if grobid_needed else _status(grobid_ok, warn=True),
            "detail": grobid_detail + ("" if grobid_needed else " (not required by this profile)"),
            "url": grobid_url,
        },
        {
            "name": "qdrant",
            "status": _status(qdrant_ok, warn=True),
            "detail": qdrant_detail + ("" if qdrant_ok else " (file index fallback is OK)"),
        },
        {
            "name": "qdrant_storage_clean",
            "status": "yellow" if baidu_junk else "green",
            "detail": (
                f"Baidu Yun sidecars break WAL ({len(baidu_junk)} files); delete *.baiduyun.uploading.cfg"
                if baidu_junk
                else "no Baidu Yun sidecar files"
            ),
        },
        {
            "name": "sciverse_token",
            "status": _status(
                token,
                warn=cfg.retrieval.backend not in {"sciverse", "sciverse_scibase"},
            ),
            "detail": "present" if token else "missing",
        },
        {
            "name": "scibase_cache",
            "status": _status(
                (ROOT / "data" / "scibase" / "materials_cache.jsonl").is_file()
                or Path(
                    getattr(cfg.retrieval, "scibase_cache_path", "") or ""
                ).is_file(),
                warn=cfg.retrieval.backend not in {"scibase", "sciverse_scibase"},
            ),
            "detail": (
                "materials_cache.jsonl present"
                if (ROOT / "data" / "scibase" / "materials_cache.jsonl").is_file()
                else "missing — run scripts/build_scibase_cache.py"
            ),
        },
        {
            "name": "semantic_scholar_key",
            "status": _status(s2, warn=cfg.retrieval.backend not in {"semantic_scholar", "s2"}),
            "detail": "present" if s2 else "missing",
        },
        {
            "name": "llm_key",
            "status": _status(openai or bool(cfg.llm.cursor_api_key), warn=not cfg.llm.enabled),
            "detail": "present" if (openai or cfg.llm.cursor_api_key) else "missing",
        },
        {
            "name": "mp_api_key",
            "status": _status(mp, warn=not cfg.route_a.enabled),
            "detail": "present" if mp else "missing",
        },
        {
            "name": "mineru_windows",
            "status": "yellow" if mineru_warn else "green",
            "detail": (
                "Windows + MinerU primary: prefer GROBID (see production_sciverse.yaml)"
                if mineru_warn
                else f"primary={cfg.fulltext.parsers.primary}"
            ),
        },
    ]
    worst = "green"
    if any(c["status"] == "yellow" for c in checks):
        worst = "yellow"
    if any(c["status"] == "red" for c in checks):
        worst = "red"
    return {
        "overall": worst,
        "config": str(config.as_posix()),
        "backend": cfg.retrieval.backend,
        "allow_backend_fallback": cfg.retrieval.allow_backend_fallback,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=Path, default=ROOT / "configs/production_sciverse.yaml")
    args = parser.parse_args()
    report = run_healthcheck(args.config)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["overall"] != "red" else 1


if __name__ == "__main__":
    raise SystemExit(main())
