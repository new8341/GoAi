from __future__ import annotations

import json
from pathlib import Path

from math import ceil

from materials_agent.agents.consistency import check_consistency
from materials_agent.agents.extractor import extract_knowledge
from materials_agent.agents.gap_finder import identify_gaps
from materials_agent.agents.gap_reviewer import review_gaps
from materials_agent.agents.known_map import build_known_pairs
from materials_agent.agents.query_rewriter import rewrite_queries
from materials_agent.agents.reporter import write_report
from materials_agent.config import AppConfig, load_ontology
from materials_agent.evidence_attribution import annotate_retrieval_databases
from materials_agent.llm import LLMClient
from materials_agent.models import AuditEvent, DocumentChunk, SurveyBundle
from materials_agent.tools.chunking import chunk_paper
from materials_agent.tools.fulltext import attach_fulltext, dump_fulltext_index
from materials_agent.tools.index import EvidenceIndex, get_evidence_index
from materials_agent.tools.literature_archive import archive_retrieved_literature
from materials_agent.tools.retrievers import get_retriever

ROOT = Path(__file__).resolve().parents[1]


class LiteratureSurveyAgent:
    """
    Survey pipeline:
    rewrite → retrieve → fulltext/parse → archive → chunk/index →
    extract → known map → gaps(+evidence) → review → optimization_metrics →
    report → consistency → template report refresh → save.
    """

    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.llm = LLMClient(cfg.llm)
        self.retriever = get_retriever(cfg.retrieval.backend)
        self.ontology = load_ontology(cfg.ontology_path)
        self.evidence_index: EvidenceIndex | None = None
        self.chunks: list[DocumentChunk] = []
        self.literature_archive_dir: Path | None = None

    def run(self) -> SurveyBundle:
        audit: list[AuditEvent] = [
            AuditEvent(
                step="init",
                tool="config",
                input_summary=self.cfg.topic,
                output_summary="pipeline start",
                meta={
                    "seed": self.cfg.seed,
                    "llm": self.llm.enabled,
                    "llm_provider": self.cfg.llm.provider,
                    "backend": self.cfg.retrieval.backend,
                    "ontology_keys": list(self.ontology.keys())[:12],
                },
            )
        ]

        queries = rewrite_queries(
            self.cfg.topic,
            self.cfg.subfield,
            self.ontology,
            self.llm,
            audit,
            enabled=self.cfg.retrieval.rewrite_queries,
        )

        # retriever implementations accept ontology kw where available
        search_fn = self.retriever.search
        target_n = self.cfg.max_papers
        need_ratio = float(self.cfg.quality.min_fulltext_paper_ratio or 0.0)
        # Oversample when fulltext ratio is gated: many OA links still 403/HTML.
        if need_ratio > 0 and self.cfg.fulltext.download_oa:
            self.cfg.max_papers = max(target_n, min(30, int(target_n * 3)))
        try:
            papers = search_fn(queries, self.cfg, audit, self.ontology)  # type: ignore[call-arg]
        except TypeError:
            papers = search_fn(queries, self.cfg, audit)
        finally:
            self.cfg.max_papers = target_n

        papers = attach_fulltext(papers, self.cfg, audit)
        if need_ratio > 0 and papers:
            with_ft = [p for p in papers if (p.full_text or "").strip()]
            without = [p for p in papers if p.id not in {x.id for x in with_ft}]
            min_ft = max(1, int(ceil(target_n * need_ratio)))
            selected = with_ft[: max(min_ft, target_n)]
            if len(selected) < target_n:
                selected = selected + without[: target_n - len(selected)]
            papers = selected[:target_n]
            source_counts: dict[str, int] = {}
            for paper in papers:
                key = paper.fulltext_source or "none"
                source_counts[key] = source_counts.get(key, 0) + 1
            n_kept_ft = sum(1 for p in papers if (p.full_text or "").strip())
            audit.append(
                AuditEvent(
                    step="fulltext_select",
                    tool="prefer_parsed_oa",
                    input_summary=f"pool={len(with_ft)+len(without)} target={target_n}",
                    output_summary=(
                        f"kept={len(papers)} with_fulltext={n_kept_ft} "
                        f"fulltext_ratio={round(n_kept_ft / max(1, len(papers)), 4)}"
                    ),
                    meta={
                        "min_ft": min_ft,
                        "pool_fulltext": len(with_ft),
                        "kept": len(papers),
                        "kept_fulltext": n_kept_ft,
                        "fulltext_ratio": round(n_kept_ft / max(1, len(papers)), 4),
                        "source_counts": source_counts,
                    },
                )
            )
        self.literature_archive_dir = archive_retrieved_literature(
            papers, self.cfg, audit, queries=queries
        )
        self.chunks = [
            chunk
            for paper in papers
            for chunk in chunk_paper(paper, self.cfg.fulltext.chunking)
        ]
        self.evidence_index = get_evidence_index(self.cfg)
        if self.chunks and self.cfg.fulltext.index.upsert_on_parse:
            self.evidence_index.upsert(self.chunks)
        audit.append(
            AuditEvent(
                step="index_fulltext",
                tool=type(self.evidence_index).__name__,
                input_summary=f"{len(papers)} papers",
                output_summary=f"{len(self.chunks)} chunks",
                meta={
                    "requested_backend": self.cfg.fulltext.index.backend,
                    "actual_backend": type(self.evidence_index).__name__,
                    "degraded": (
                        self.cfg.fulltext.index.backend == "qdrant"
                        and type(self.evidence_index).__name__ != "QdrantEvidenceIndex"
                    ),
                },
            )
        )

        extractions = []
        if self.cfg.pipeline.extract:
            extractions = extract_knowledge(
                papers, self.llm, self.cfg.quality, audit, self.ontology
            )

        known = []
        if self.cfg.pipeline.build_known_table:
            known = build_known_pairs(extractions, audit, ontology=self.ontology)

        gaps = []
        if self.cfg.pipeline.identify_gaps:
            gaps = identify_gaps(
                self.cfg.topic,
                papers,
                extractions,
                known,
                self.llm,
                self.cfg.quality,
                audit,
                self.evidence_index,
                self.cfg.evidence_retrieval,
            )

        if self.cfg.pipeline.review_gaps and gaps:
            gaps = review_gaps(
                gaps, papers, known, self.llm, self.cfg.quality, audit, topic=self.cfg.topic
            )

        from materials_agent.topic_focus import compute_optimization_metrics

        metrics = compute_optimization_metrics(
            self.cfg.topic, papers, gaps, extractions, self.ontology
        )
        audit.append(
            AuditEvent(
                step="optimization_metrics",
                tool="topic_focus",
                input_summary=self.cfg.topic,
                output_summary=(
                    f"topic_hit={metrics['topic_hit_rate']} "
                    f"gap_align={metrics['gap_material_alignment']} "
                    f"boilerplate={metrics['evidence_boilerplate_rate']} "
                    f"provenance={metrics['provenance_coverage']}"
                ),
                meta=metrics,
            )
        )

        report = ""
        consistency = None
        db_stats = annotate_retrieval_databases(papers, gaps, extractions)
        audit.append(
            AuditEvent(
                step="annotate_retrieval_databases",
                tool="evidence_attribution",
                input_summary=self.cfg.topic,
                output_summary=(
                    f"labeled={db_stats['spans_labeled']} "
                    f"gaps_with_db={db_stats['gaps_with_database']}/{db_stats['gaps']}"
                ),
                meta=db_stats,
            )
        )
        # draft report first without consistency, then check, then optionally refresh section
        if self.cfg.pipeline.write_report:
            report = write_report(
                self.cfg.topic,
                self.cfg.subfield,
                papers,
                extractions,
                gaps,
                known,
                queries,
                None,
                self.llm,
                audit,
            )

        if self.cfg.pipeline.check_consistency:
            consistency = check_consistency(
                papers, extractions, gaps, report, audit, self.cfg.quality
            )
            # rebuild report with consistency section (template path; skip second LLM polish)
            if self.cfg.pipeline.write_report:
                from materials_agent.agents.reporter import _render_heuristic_report

                report = _render_heuristic_report(
                    self.cfg.topic,
                    self.cfg.subfield,
                    papers,
                    extractions,
                    gaps,
                    known,
                    queries,
                    consistency,
                )
                audit.append(
                    AuditEvent(
                        step="write_report",
                        tool="template_with_consistency",
                        input_summary=self.cfg.topic,
                        output_summary=f"{len(report)} chars",
                    )
                )

        for call in self.llm.call_audit:
            audit.append(
                AuditEvent(
                    step=f"llm_{call['step']}",
                    tool=call["provider"],
                    input_summary=f"model={call['model']}",
                    output_summary=call["status"],
                    meta={
                        key: value
                        for key, value in call.items()
                        if key not in {"step", "provider", "model", "status"}
                        and value
                    },
                )
            )

        return SurveyBundle(
            topic=self.cfg.topic,
            subfield=self.cfg.subfield,
            papers=papers,
            extractions=extractions,
            gaps=gaps,
            known_pairs=known,
            query_variants=queries,
            consistency=consistency,
            report_markdown=report,
            audit=audit if self.cfg.pipeline.audit_log else [],
        )

    def save(self, bundle: SurveyBundle, output_dir: str | Path | None = None) -> Path:
        out = Path(output_dir or self.cfg.output_dir)
        if not out.is_absolute():
            out = ROOT / out
        out.mkdir(parents=True, exist_ok=True)
        from materials_agent.topic_focus import REQUIRED_METRIC_KEYS, compute_optimization_metrics

        metrics = compute_optimization_metrics(
            bundle.topic,
            bundle.papers,
            bundle.gaps,
            bundle.extractions,
            self.ontology,
        )
        missing = REQUIRED_METRIC_KEYS - set(metrics)
        if missing:
            raise ValueError(f"optimization_metrics missing keys: {sorted(missing)}")
        (out / "optimization_metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "report.md").write_text(bundle.report_markdown, encoding="utf-8")
        (out / "gaps.json").write_text(
            json.dumps([g.model_dump() for g in bundle.gaps], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "extractions.json").write_text(
            json.dumps([e.model_dump() for e in bundle.extractions], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "papers.json").write_text(
            json.dumps(
                [p.model_dump(exclude={"raw"}) for p in bundle.papers],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (out / "known_pairs.json").write_text(
            json.dumps([k.model_dump() for k in bundle.known_pairs], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "queries.json").write_text(
            json.dumps(bundle.query_variants, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if bundle.consistency:
            (out / "consistency.json").write_text(
                bundle.consistency.model_dump_json(indent=2),
                encoding="utf-8",
            )
        (out / "audit.json").write_text(
            json.dumps([a.model_dump() for a in bundle.audit], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out / "bundle.json").write_text(
            bundle.model_dump_json(indent=2),
            encoding="utf-8",
        )
        dump_fulltext_index(bundle.papers, out)
        (out / "parse_manifest.json").write_text(
            json.dumps(
                [
                    {
                        "paper_id": paper.id,
                        "manifest": paper.raw.get("parse_manifest", {}),
                    }
                    for paper in bundle.papers
                    if paper.raw.get("parse_manifest")
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (out / "evidence_chunks.json").write_text(
            json.dumps([chunk.model_dump() for chunk in self.chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if self.literature_archive_dir is not None:
            (out / "literature_archive.json").write_text(
                json.dumps(
                    {
                        "archive_dir": str(self.literature_archive_dir),
                        "relative": str(
                            self.literature_archive_dir.relative_to(
                                Path(__file__).resolve().parents[1]
                            )
                        ).replace("\\", "/"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        from materials_agent.export.latex_report import export_survey_latex
        from materials_agent.export.versions import dump_external_versions

        dump_external_versions(out, self.cfg)
        try:
            export_survey_latex(out, compile_pdf=False)
        except Exception as exc:  # noqa: BLE001 — deliver MD even if LaTeX fails
            (out / "latex_export_error.txt").write_text(str(exc), encoding="utf-8")
        return out
