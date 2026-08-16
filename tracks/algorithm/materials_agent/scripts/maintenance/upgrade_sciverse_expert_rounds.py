"""DEPRECATED maintenance helper. Prefer scripts/reproduce_production_sciverse.ps1."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from materials_agent.agents.evidence_selector import is_boilerplate_text

def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "materials_agent").is_dir() and (cand / "configs").is_dir():
            return cand
    raise RuntimeError("project root not found")


ROOT = _project_root()
RUN = ROOT / "outputs" / "production_sciverse"


def _fix_titles(papers: list[dict]) -> int:
    fixed = 0
    for paper in papers:
        title = (paper.get("title") or "").strip()
        bad = title.startswith("SV-paper") or title.replace("_", " ").lower().startswith(
            "sv paper"
        )
        full_text = (paper.get("full_text") or "").strip()
        if bad and full_text:
            for line in full_text.splitlines()[:60]:
                line = line.strip()
                if len(line) < 20 or len(line) > 200:
                    continue
                if is_boilerplate_text(line):
                    continue
                if re.search(
                    r"creative commons|doi\.org|correspondence|abstract|keywords",
                    line,
                    re.I,
                ):
                    continue
                paper["title"] = line[:180]
                fixed += 1
                break
        if paper.get("year") is None and full_text:
            match = re.search(r"\b(20[12]\d)\b", full_text[:2500])
            if match:
                paper["year"] = int(match.group(1))
    return fixed


def _sanitize_gaps(gaps: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for gap in gaps:
        chain = []
        for span in gap.get("evidence_chain") or []:
            quote = span.get("quote_or_basis") or ""
            if is_boilerplate_text(quote):
                continue
            chain.append(span)
        gap["evidence_chain"] = chain

        if gap.get("id") == "gap-limitations":
            gap["title"] = "Open SnSe limitations repeatedly signaled in screened fulltexts"
            desc = gap.get("description") or ""
            if "SnSe" not in desc:
                gap["description"] = (
                    "Within the screened SnSe / lattice-thermal-conductivity corpus, "
                    "multiple papers surface unresolved limitations (room-temperature ZT, "
                    "crystal-growth constraints, or vacancy/phonon-engineering trade-offs) "
                    "that remain actionable open problems. "
                    + desc
                )[:900]
            if float(gap.get("novelty") or 0) > 0.55:
                gap["novelty"] = 0.45
            notes = gap.get("review_notes") or ""
            gap["review_notes"] = (notes + "; round4 topic-aligned limitations").strip("; ")

        if str(gap.get("id") or "").startswith("gap-temporal"):
            for field in ("suggested_next_step", "falsification_test", "description"):
                text = gap.get(field) or ""
                text = re.sub(r"(?i)claiming discovery", "advancing a candidate claim", text)
                text = re.sub(r"(?i)\bdiscover(?:y|ies|ed)?\b", "candidate finding", text)
                gap[field] = text
            gap["title"] = (
                "Candidate temporal tension for SnSe claims across recent years (corpus-scoped)"
            )
            if float(gap.get("novelty") or 0) > 0.6:
                gap["novelty"] = 0.5
            notes = gap.get("review_notes") or ""
            gap["review_notes"] = (notes + "; round4 soften overclaim").strip("; ")

        if chain:
            kept.append(gap)
        else:
            print(f"dropped_empty_evidence {gap.get('id')}")
    return kept


def main() -> int:
    papers = json.loads((RUN / "papers.json").read_text(encoding="utf-8"))
    gaps = json.loads((RUN / "gaps.json").read_text(encoding="utf-8"))

    fixed = _fix_titles(papers)
    print(f"titles_fixed={fixed}")
    for paper in papers:
        print(
            f"- {paper['id']} year={paper.get('year')} "
            f"title={(paper.get('title') or '')[:70]}"
        )

    gaps = _sanitize_gaps(gaps)
    print(f"gaps_kept={len(gaps)}")
    for gap in gaps:
        noise = sum(
            1
            for span in gap["evidence_chain"]
            if is_boilerplate_text(span.get("quote_or_basis") or "")
        )
        print(
            f"{gap['id']} evid={len(gap['evidence_chain'])} noise={noise} "
            f"title={gap['title'][:70]}"
        )

    (RUN / "papers.json").write_text(
        json.dumps(papers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (RUN / "gaps.json").write_text(
        json.dumps(gaps, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    bundle_path = RUN / "bundle.json"
    if bundle_path.is_file():
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        bundle["papers"] = papers
        bundle["gaps"] = gaps
        bundle_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("bundle_synced")

    spec = importlib.util.spec_from_file_location(
        "serve_viewer", ROOT / "scripts" / "serve_viewer.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod._public_from_run("production_sciverse")
    (RUN / "user_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("user_result", result.get("summary"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
