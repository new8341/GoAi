#!/usr/bin/env python3
"""Write submissions/semi_final/scibase_usage.md from local Sci-Base cache search."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]  # materials_agent → algorithm → tracks → AI_kaiyuan
sys.path.insert(0, str(ROOT))

from materials_agent.config import AppConfig, RetrievalConfig
from materials_agent.tools.retrievers import SciBaseRetriever
from materials_agent.tools.scibase_client import load_cache_rows, resolve_scibase_cache_path


def main() -> int:
    cfg = AppConfig(
        topic="SnSe lattice thermal conductivity vacancy engineering",
        max_papers=5,
        retrieval=RetrievalConfig(
            backend="scibase",
            allow_backend_fallback=False,
            min_relevance=0.02,
            scibase_prefer_cache=True,
            scibase_streaming=False,
        ),
        output_dir="outputs/_scibase_smoke",
    )
    cache = resolve_scibase_cache_path(cfg)
    rows = load_cache_rows(cache)
    audit: list = []
    papers = SciBaseRetriever().search(
        ["SnSe thermoelectric vacancy lattice thermal"],
        cfg,
        audit,
    )
    lines = [
        "# Sci-Base 使用证明",
        "",
        "> Dataset: https://huggingface.co/datasets/opendatalab/Sci-Base",
        "",
        "## 接入方式",
        "",
        "- Retriever: `backend: scibase` / hybrid `sciverse_scibase`",
        "- Cache: `data/scibase/materials_cache.jsonl`（自 HF `paper` split 流式扫描构建）",
        f"- Cache rows: **{len(rows)}**",
        "- Build: `py -3 scripts/build_scibase_cache.py --max-scan 1500 --max-keep 80`",
        "",
        "## 主题检索抽样",
        "",
    ]
    for p in papers:
        lines.append(f"- `{p.id}` | score={p.relevance_score} | {p.title[:140]}")
        if p.doi:
            lines.append(f"  - doi: `{p.doi}`")
        lines.append(
            "  - source label: `scibase` → evidence `retrieval_database=scibase`"
        )
    lines += [
        "",
        "## 合规",
        "",
        "- 结构/解析格式：CC-BY-4.0；正文保留原 OA 许可。",
        "- 全库 TB 级：竞赛路径使用材料子集缓存，不下载整库。",
        "",
    ]
    out = REPO / "submissions" / "semi_final" / "scibase_usage.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} hits={len(papers)} cache={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
