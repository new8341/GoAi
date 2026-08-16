"""Snapshot external resource versions for submission reproducibility."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from materials_agent.config import AppConfig

ROOT = Path(__file__).resolve().parents[2]


def _compose_images(compose_path: Path) -> dict[str, str]:
    if not compose_path.is_file():
        return {}
    text = compose_path.read_text(encoding="utf-8")
    images: dict[str, str] = {}
    current = ""
    for line in text.splitlines():
        m_svc = re.match(r"^  ([a-zA-Z0-9_-]+):\s*$", line)
        if m_svc:
            current = m_svc.group(1)
            continue
        m_img = re.match(r"^\s+image:\s*(.+)\s*$", line)
        if m_img and current:
            images[current] = m_img.group(1).strip()
    return images


def dump_external_versions(
    out_dir: Path | str,
    cfg: AppConfig | None = None,
    *,
    profile_name: str | None = None,
) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    images = _compose_images(ROOT / "docker-compose.yml")
    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "profile": profile_name or (Path(cfg.output_dir).name if cfg else None),
        "seed": getattr(cfg, "seed", None) if cfg else None,
        "topic": getattr(cfg, "topic", None) if cfg else None,
        "ontology_path": getattr(cfg, "ontology_path", None) if cfg else None,
        "retrieval_backend": cfg.retrieval.backend if cfg else None,
        "allow_backend_fallback": cfg.retrieval.allow_backend_fallback if cfg else None,
        "docker_images": images,
        "llm": {
            "provider": cfg.llm.provider if cfg else os.getenv("LLM_PROVIDER"),
            "model": (cfg.llm.model if cfg else None) or os.getenv("OPENAI_MODEL"),
            "base_url_set": bool(
                (cfg.llm.base_url if cfg else None) or os.getenv("OPENAI_BASE_URL")
            ),
            "api_key_set": bool(os.getenv("OPENAI_API_KEY") or os.getenv("CURSOR_API_KEY")),
        },
        "materials_project_key_set": bool(os.getenv("MP_API_KEY")),
        "sciverse_token_set": bool(os.getenv("SCIVERSE_API_TOKEN")),
        "access_notes": {
            "sciverse": "https://sciverse.opendatalab.com or https://sciverse.space (Bearer token)",
            "scibase": "https://huggingface.co/datasets/opendatalab/Sci-Base (CC-BY-4.0 structure; OA content licenses)",
            "openalex": "https://openalex.org (polite pool via OPENALEX_EMAIL)",
            "materials_project": "https://materialsproject.org (MP_API_KEY)",
            "grobid": images.get("grobid", "grobid/grobid:0.8.0"),
            "qdrant": images.get("qdrant", "qdrant/qdrant"),
        },
        "scibase": {
            "dataset": getattr(cfg.retrieval, "scibase_dataset", None) if cfg else "opendatalab/Sci-Base",
            "config": getattr(cfg.retrieval, "scibase_config", None) if cfg else "paper",
            "cache_path": getattr(cfg.retrieval, "scibase_cache_path", None) if cfg else None,
        },
    }
    if cfg and getattr(cfg, "route_a", None) is not None:
        ra = cfg.route_a
        payload["route_a"] = {
            "seed": getattr(ra, "seed", None),
            "population_size": getattr(ra, "population_size", None),
            "n_iterations": getattr(ra, "n_iterations", None),
            "external_validate": getattr(ra, "external_validate", None),
            "materials_db": getattr(ra, "materials_db", None),
        }
    path = out / "external_versions.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
