"""DEPRECATED maintenance helper. Prefer a clean survey + reproduce script.

Re-ground production gaps with fixed evidence selector (maintenance only).
Default is dry-run (print before/after). Pass --write to mutate outputs.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from materials_agent.agents.evidence_selector import ground_gap_evidence, is_boilerplate_text
from materials_agent.config import load_config
from materials_agent.models import DocumentChunk, ExtractedRecord, Paper, ResearchGap
from materials_agent.tools.index.file_index import FileEvidenceIndex

def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "materials_agent").is_dir() and (cand / "configs").is_dir():
            return cand
    raise RuntimeError("project root not found")


ROOT = _project_root()
OUT = ROOT / "outputs" / "production"


def _summarize(gaps: list[ResearchGap]) -> None:
    for g in gaps:
        noise = sum(1 for e in g.evidence_chain if is_boilerplate_text(e.quote_or_basis))
        prov = sum(1 for e in g.evidence_chain if e.provenance)
        print(
            f"  {g.id}: evid={len(g.evidence_chain)} prov={prov}/{len(g.evidence_chain)} "
            f"noise={noise} status={g.review_status}"
        )
        for e in g.evidence_chain[:2]:
            q = e.quote_or_basis[:90].replace("\n", " ")
            print(f"    {e.paper_id} {'PROV' if e.provenance else 'NO_PROV'} {q}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually overwrite gaps.json / bundle.json / user_result.json (creates .bak first).",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=OUT,
        help="Run directory to re-ground (default: outputs/production).",
    )
    args = parser.parse_args()
    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    if not run_dir.is_dir():
        print(f"run dir not found: {run_dir}")
        return 1

    papers = [Paper.model_validate(p) for p in json.loads((run_dir / "papers.json").read_text(encoding="utf-8"))]
    gaps = [ResearchGap.model_validate(g) for g in json.loads((run_dir / "gaps.json").read_text(encoding="utf-8"))]
    exts = [
        ExtractedRecord.model_validate(e)
        for e in json.loads((run_dir / "extractions.json").read_text(encoding="utf-8"))
    ]
    chunks = [
        DocumentChunk.model_validate(c)
        for c in json.loads((run_dir / "evidence_chunks.json").read_text(encoding="utf-8"))
    ]
    idx_path = run_dir / "_tmp_reground_index.json"
    index = FileEvidenceIndex(idx_path)
    index.upsert(chunks)

    print("before:")
    _summarize(gaps)

    cfg = load_config(ROOT / "configs" / "production.yaml")
    grounded = ground_gap_evidence(
        gaps,
        papers,
        index,
        cfg.evidence_retrieval,
        cfg.quality,
        [],
        extractions=exts,
    )
    print("after:")
    _summarize(grounded)

    if not args.write:
        print("dry-run only; re-run with --write to persist (backup *.bak will be created).")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for name in ("gaps.json", "bundle.json", "user_result.json"):
        path = run_dir / name
        if path.is_file():
            bak = run_dir / f"{name}.{stamp}.bak"
            shutil.copy2(path, bak)
            print(f"backup -> {bak.name}")

    (run_dir / "gaps.json").write_text(
        json.dumps([g.model_dump() for g in grounded], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if (run_dir / "bundle.json").is_file():
        bundle = json.loads((run_dir / "bundle.json").read_text(encoding="utf-8"))
        bundle["gaps"] = [g.model_dump() for g in grounded]
        (run_dir / "bundle.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")

    if (run_dir / "user_result.json").is_file():
        user = json.loads((run_dir / "user_result.json").read_text(encoding="utf-8"))
        if "gaps" in user:
            user["gaps"] = [
                {
                    "id": g.id,
                    "title": g.title,
                    "description": g.description,
                    "type": g.gap_type,
                    "novelty": g.novelty,
                    "actionability": g.actionability,
                    "review_status": g.review_status,
                    "supporting_paper_ids": g.supporting_paper_ids,
                    "contradicting_paper_ids": g.contradicting_paper_ids,
                    "suggested_next_step": g.suggested_next_step,
                    "falsification_test": g.falsification_test,
                    "evidence": [
                        {
                            "paper_id": e.paper_id,
                            "claim": e.claim,
                            "quote": e.quote_or_basis,
                            "confidence": e.confidence,
                            "location": e.location,
                        }
                        for e in g.evidence_chain
                    ],
                }
                for g in grounded
            ]
            (run_dir / "user_result.json").write_text(
                json.dumps(user, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    print(f"wrote grounded gaps into {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
