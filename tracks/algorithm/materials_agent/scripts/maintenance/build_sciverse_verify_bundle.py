"""DEPRECATED maintenance helper. Prefer scripts/reproduce_production_sciverse.ps1.

Build a Sciverse verification bundle preferring already-cached OA PDFs.
"""

from __future__ import annotations

import sys
from pathlib import Path

def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in (here, *here.parents):
        if (cand / "materials_agent").is_dir() and (cand / "configs").is_dir():
            return cand
    raise RuntimeError("project root not found")


ROOT = _project_root()
sys.path.insert(0, str(ROOT))

from materials_agent.agents.consistency import check_consistency
from materials_agent.agents.extractor import extract_knowledge
from materials_agent.agents.gap_finder import identify_gaps
from materials_agent.agents.gap_reviewer import review_gaps
from materials_agent.agents.known_map import build_known_pairs
from materials_agent.agents.reporter import _render_heuristic_report, write_report
from materials_agent.config import load_config
from materials_agent.models import AuditEvent, Paper, SurveyBundle
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.tools.chunking import chunk_paper
from materials_agent.tools.fulltext import attach_fulltext, dump_fulltext_index
from materials_agent.tools.index import get_evidence_index
from materials_agent.tools.retrievers import SciverseRetriever


def main() -> int:
    cfg = load_config(ROOT / "configs/production_sciverse.yaml")
    cfg.max_papers = 5
    cfg.quality.min_fulltext_paper_ratio = 0.4
    cfg.retrieval.archive_literature = False

    audit: list[AuditEvent] = []
    queries = [cfg.topic]
    papers = SciverseRetriever().search(queries, cfg, audit)
    print(f"retrieved={len(papers)}", flush=True)

    pdf_dir = ROOT / "data/fulltext/pdfs"
    existing = {
        p.stem: p
        for p in pdf_dir.glob("SV-*.pdf")
        if p.is_file() and p.stat().st_size > 1000
    }
    have = {p.id for p in papers}
    for stem, path in existing.items():
        if stem not in have:
            doi = stem.removeprefix("SV-paper_").replace("_", "/")
            papers.append(
                Paper(
                    id=stem,
                    title="",  # attach_fulltext backfills TEI/fulltext; never keep SV-paper stem
                    doi=doi,
                    source="sciverse",
                    pdf_path=str(path),
                )
            )
            print(f"injected_cached={stem}", flush=True)

    def rank(p: Paper) -> tuple[int, float]:
        stem_hit = 1 if (pdf_dir / f"{p.id}.pdf").is_file() else 0
        return (stem_hit, float(p.relevance_score or 0.0))

    papers = sorted(papers, key=rank, reverse=True)[:5]
    print("selected=" + ",".join(p.id for p in papers), flush=True)

    papers = attach_fulltext(papers, cfg, audit)
    for p in papers:
        print(
            f"fulltext {p.id} source={p.fulltext_source} has_text={bool(p.full_text)}",
            flush=True,
        )

    agent = LiteratureSurveyAgent(cfg)
    agent.chunks = [
        chunk for paper in papers for chunk in chunk_paper(paper, cfg.fulltext.chunking)
    ]
    agent.evidence_index = get_evidence_index(cfg)
    if agent.chunks and cfg.fulltext.index.upsert_on_parse:
        agent.evidence_index.upsert(agent.chunks)

    extractions = extract_knowledge(
        papers, agent.llm, cfg.quality, audit, agent.ontology
    )
    known = build_known_pairs(extractions, audit, ontology=agent.ontology)
    gaps = identify_gaps(
        cfg.topic,
        papers,
        extractions,
        known,
        agent.llm,
        cfg.quality,
        audit,
        agent.evidence_index,
        cfg.evidence_retrieval,
    )
    gaps = review_gaps(gaps, papers, known, agent.llm, cfg.quality, audit)
    report = write_report(
        cfg.topic,
        cfg.subfield,
        papers,
        extractions,
        gaps,
        known,
        queries,
        None,
        agent.llm,
        audit,
    )
    consistency = check_consistency(
        papers, extractions, gaps, report, audit, cfg.quality
    )
    report = _render_heuristic_report(
        cfg.topic,
        cfg.subfield,
        papers,
        extractions,
        gaps,
        known,
        queries,
        consistency,
    )
    bundle = SurveyBundle(
        topic=cfg.topic,
        subfield=cfg.subfield,
        query_variants=queries,
        papers=papers,
        extractions=extractions,
        known_pairs=known,
        gaps=gaps,
        report_markdown=report,
        consistency=consistency,
        audit=audit,
    )
    out = agent.save(bundle)
    dump_fulltext_index(papers, out)
    n_ft = sum(1 for p in papers if p.full_text)
    print(f"saved={out} fulltext={n_ft}/{len(papers)} gaps={len(gaps)}", flush=True)
    return 0 if n_ft >= 2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
