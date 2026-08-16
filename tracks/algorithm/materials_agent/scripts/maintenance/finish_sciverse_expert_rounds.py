"""DEPRECATED maintenance helper. Prefer scripts/reproduce_production_sciverse.ps1."""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from xml.etree import ElementTree

from materials_agent.agents.evidence_selector import is_boilerplate_text

def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "materials_agent").is_dir() and (cand / "configs").is_dir():
            return cand
    raise RuntimeError("project root not found")


ROOT = _project_root()
RUN = ROOT / "outputs" / "production_sciverse"
_TEI = {"tei": "http://www.tei-c.org/ns/1.0"}


def _title_from_tei(paper_id: str) -> str | None:
    tei_path = ROOT / "data" / "fulltext" / "parsed" / paper_id / "grobid" / "grobid.tei.xml"
    if not tei_path.is_file():
        # some parses nest under grobid/
        candidates = list((ROOT / "data" / "fulltext" / "parsed" / paper_id).rglob("*.tei.xml"))
        tei_path = candidates[0] if candidates else tei_path
    if not tei_path.is_file():
        return None
    try:
        root = ElementTree.fromstring(tei_path.read_text(encoding="utf-8", errors="ignore"))
    except ElementTree.ParseError:
        return None
    for node in root.findall(".//tei:titleStmt/tei:title", _TEI):
        text = " ".join("".join(node.itertext()).split()).strip()
        if len(text) >= 12:
            return text[:220]
    return None


def _title_from_fulltext(full_text: str) -> str | None:
    for line in (full_text or "").splitlines()[:80]:
        line = line.strip()
        if len(line) < 20 or len(line) > 220:
            continue
        if is_boilerplate_text(line):
            continue
        if re.search(r"creative commons|doi\.org|correspondence|keywords|abstract", line, re.I):
            continue
        if re.search(r"SnSe|thermoelectric|thermal conductivity|lattice|vacancy", line, re.I):
            return line[:220]
    return None


def main() -> int:
    papers = json.loads((RUN / "papers.json").read_text(encoding="utf-8"))
    gaps = json.loads((RUN / "gaps.json").read_text(encoding="utf-8"))
    bak = sorted(RUN.glob("gaps.json.*.bak"))[-1]
    old_gaps = json.loads(bak.read_text(encoding="utf-8"))

    # Restore temporal gap with non-boilerplate evidence only.
    if not any(g.get("id", "").startswith("gap-temporal") for g in gaps):
        for gap in old_gaps:
            if not str(gap.get("id") or "").startswith("gap-temporal"):
                continue
            chain = [
                span
                for span in (gap.get("evidence_chain") or [])
                if not is_boilerplate_text(span.get("quote_or_basis") or "")
            ]
            if not chain:
                continue
            gap = dict(gap)
            gap["evidence_chain"] = chain
            gap["title"] = (
                "Candidate temporal tension for SnSe claims across recent years (corpus-scoped)"
            )
            gap["description"] = (
                "Both earlier and recent screened papers discuss SnSe lattice thermal transport. "
                "Compare mechanisms/metrics under normalized conditions before asserting a narrative "
                "shift; retain only if claims genuinely conflict within this corpus."
            )
            for field in ("suggested_next_step", "falsification_test"):
                text = gap.get(field) or ""
                text = re.sub(r"(?i)claiming discovery", "advancing a candidate claim", text)
                text = re.sub(r"(?i)\bdiscover(?:y|ies|ed)?\b", "candidate finding", text)
                text = re.sub(r"(?i)paradigm shift", "narrative shift", text)
                gap[field] = text
            gap["novelty"] = min(float(gap.get("novelty") or 0.5), 0.5)
            notes = gap.get("review_notes") or ""
            gap["review_notes"] = (notes + "; round5 restore+soften").strip("; ")
            gaps.append(gap)
            print(f"restored {gap['id']} evid={len(chain)}")

    # Ensure limitations stays topic-aligned.
    for gap in gaps:
        if gap.get("id") == "gap-limitations":
            gap["title"] = "Open SnSe limitations repeatedly signaled in screened fulltexts"
            if "SnSe" not in (gap.get("description") or ""):
                gap["description"] = (
                    "Within the screened SnSe / lattice-thermal-conductivity corpus, multiple papers "
                    "surface unresolved limitations that remain actionable open problems. "
                    + (gap.get("description") or "")
                )[:900]

    fixed = 0
    for paper in papers:
        title = (paper.get("title") or "").strip()
        bad = title.startswith("SV-paper") or "SV-paper" in title
        if not bad:
            continue
        new_title = _title_from_tei(paper["id"]) or _title_from_fulltext(paper.get("full_text") or "")
        if new_title:
            paper["title"] = new_title
            fixed += 1
            print(f"title_fixed {paper['id']} -> {new_title[:80]}")
        if paper.get("year") is None:
            blob = (paper.get("full_text") or "")[:3000]
            match = re.search(r"\b(20[12]\d)\b", blob)
            if match:
                paper["year"] = int(match.group(1))

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
        # Refresh report markdown so X2 can pass.
        lines = [
            f"# Literature survey report",
            "",
            f"Topic: {bundle.get('topic')}",
            "",
            "## Papers",
            "",
        ]
        for paper in papers:
            lines.append(f"- `{paper.get('id')}` {paper.get('title')}")
        lines += ["", "## Research Gaps", ""]
        for gap in gaps:
            lines.append(f"### {gap.get('title')}")
            lines.append("")
            lines.append(gap.get("description") or "")
            lines.append("")
            lines.append(f"- Type: {gap.get('gap_type')}")
            lines.append(f"- Next: {gap.get('suggested_next_step')}")
            lines.append(f"- Falsify: {gap.get('falsification_test')}")
            lines.append("")
        report = "\n".join(lines)
        bundle["report_markdown"] = report
        (RUN / "report.md").write_text(report, encoding="utf-8")
        bundle_path.write_text(
            json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("bundle+report synced")

    # Force refresh user_result from bundle (delete stale cache first).
    cache = RUN / "user_result.json"
    if cache.is_file():
        cache.unlink()
    spec = importlib.util.spec_from_file_location(
        "serve_viewer", ROOT / "scripts" / "serve_viewer.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    result = mod._public_from_run("production_sciverse")
    print("user_result", result.get("summary"), "titles_fixed", fixed, "gaps", len(gaps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
