#!/usr/bin/env python3
"""Enrich an existing gold survey run with Sci-Base hits (no GROBID required).

Copies production_sciverse → production_sciverse_scibase and appends Sci-Base
papers + evidence labels for handbook database disclosure.
"""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import AppConfig, RetrievalConfig, load_config
from materials_agent.models import AuditEvent, EvidenceSpan, ResearchGap
from materials_agent.tools.retrievers import SciBaseRetriever
from materials_agent.export.versions import dump_external_versions


def main() -> int:
    src = ROOT / "outputs" / "production_sciverse"
    dst = ROOT / "outputs" / "production_sciverse_scibase"
    if not src.is_dir():
        print(f"missing source run: {src}", file=sys.stderr)
        return 1

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(
        src,
        dst,
        ignore=shutil.ignore_patterns("*.pdf", "pdfs", "__pycache__"),
    )
    # Still try to copy report.pdf if present
    for name in ("report.pdf", "report.tex", "references.bib", "report.md"):
        p = src / name
        if p.is_file():
            shutil.copy2(p, dst / name)

    cfg = load_config(ROOT / "configs" / "production_sciverse_scibase.yaml")
    cfg.output_dir = str(dst.relative_to(ROOT)).replace("\\", "/")
    audit: list[AuditEvent] = []
    papers = SciBaseRetriever().search(
        [cfg.topic, "SnSe thermoelectric vacancy lattice thermal"],
        cfg,
        audit,
    )

    papers_path = dst / "papers.json"
    existing = []
    if papers_path.is_file():
        existing = json.loads(papers_path.read_text(encoding="utf-8"))
    # append scibase papers
    seen = {p.get("id") for p in existing if isinstance(p, dict)}
    added = []
    for p in papers:
        if p.id in seen:
            continue
        row = p.model_dump()
        existing.append(row)
        added.append(row)
        seen.add(p.id)
    papers_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    enrich = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "post_hoc_scibase_enrich",
        "source_run": "outputs/production_sciverse",
        "scibase_added": len(added),
        "scibase_paper_ids": [a["id"] for a in added],
        "note": (
            "Sci-Base rows from HF materials cache; full hybrid re-parse with GROBID "
            "requires Docker. Evidence DB labels for new papers: scibase."
        ),
        "audit": [a.model_dump() for a in audit],
    }
    (dst / "scibase_enrichment.json").write_text(
        json.dumps(enrich, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Append section to report.md
    report = dst / "report.md"
    block = [
        "",
        "## Sci-Base enrichment (opendatalab/Sci-Base)",
        "",
        f"- Added **{len(added)}** papers from Sci-Base materials cache.",
        "- Database label for these rows: `scibase`.",
        "",
    ]
    for a in added[:8]:
        block.append(f"- `{a['id']}` | {a.get('title','')[:120]}")
        if a.get("doi"):
            block.append(f"  - doi: `{a['doi']}` · Database: `scibase`")
    block.append("")
    if report.is_file():
        report.write_text(
            report.read_text(encoding="utf-8") + "\n".join(block),
            encoding="utf-8",
        )
    else:
        report.write_text("\n".join(["# Survey report (Sci-Base enrich)", ""] + block), encoding="utf-8")

    dump_external_versions(dst, cfg, profile_name="production_sciverse_scibase")

    # pointer for submissions
    usage = ROOT.parents[2] / "submissions" / "semi_final" / "scibase_usage.md"
    if usage.is_file():
        extra = (
            f"\n## Gold enrich run\n\n"
            f"- Output: `outputs/production_sciverse_scibase/`\n"
            f"- Added papers: **{len(added)}**\n"
            f"- Mode: post-hoc enrich (Docker/GROBID not required for this step)\n"
        )
        text = usage.read_text(encoding="utf-8")
        if "## Gold enrich run" not in text:
            usage.write_text(text.rstrip() + "\n" + extra, encoding="utf-8")

    print(json.dumps({"dst": str(dst), "added": len(added)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
