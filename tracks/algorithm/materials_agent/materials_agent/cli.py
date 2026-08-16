from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from materials_agent.config import load_config
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.routes.route_a import RouteASearcher

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "configs" / "default.yaml"


@app.command("survey")
def survey(
    config: Path = typer.Option(_default_config_path(), "--config", "-c", help="YAML config"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Override topic"),
    max_papers: Optional[int] = typer.Option(None, "--max-papers", help="Override paper count"),
    route_a: bool = typer.Option(False, "--route-a", help="Also run Route A SPR search"),
) -> None:
    """Run optimized literature survey agent."""
    cfg = load_config(config)
    if topic:
        cfg.topic = topic
    if max_papers:
        cfg.max_papers = max_papers
    if route_a:
        cfg.route_a.enabled = True

    console.rule("[bold]Materials Literature Survey Agent (optimized)")
    console.print(f"Topic: [cyan]{cfg.topic}")
    console.print(
        f"Backend: {cfg.retrieval.backend} | LLM: "
        f"{'ON' if cfg.llm.available else 'OFF (heuristic)'} | "
        f"rewrite={cfg.retrieval.rewrite_queries} review={cfg.pipeline.review_gaps}"
    )

    agent = LiteratureSurveyAgent(cfg)
    bundle = agent.run()
    out = agent.save(bundle)
    console.print(f"[green]Saved survey outputs → {out.resolve()}")
    console.print(f"Queries: {bundle.query_variants}")
    fulltext_papers = sum(1 for paper in bundle.papers if paper.full_text)
    fulltext_gaps = sum(
        1
        for gap in bundle.gaps
        if any(span.location in {"fulltext", "chunk"} for span in gap.evidence_chain)
    )
    console.print(
        f"Fulltext: {fulltext_papers}/{len(bundle.papers)} papers | "
        f"Gap fulltext evidence: {fulltext_gaps}/{len(bundle.gaps)}"
    )
    if bundle.consistency:
        console.print(
            f"Consistency: {'[green]PASS' if bundle.consistency.ok else '[red]FAIL'} "
            f"({len(bundle.consistency.issues)} issues)"
        )

    table = Table(title="Research Gaps")
    table.add_column("ID")
    table.add_column("Type")
    table.add_column("Review")
    table.add_column("Title")
    table.add_column("Next step")
    for g in bundle.gaps:
        table.add_row(
            g.id,
            g.gap_type,
            g.review_status,
            g.title[:40],
            (g.suggested_next_step or "")[:40],
        )
    console.print(table)

    if cfg.route_a.enabled:
        console.rule("[bold]Route A — SPR search")
        searcher = RouteASearcher(cfg, bundle)
        cands = searcher.run()
        route_out = searcher.save(cands, out)
        console.print(f"[green]Saved Route A outputs → {route_out.resolve()}")
        if cands:
            console.print(
                f"Top: ({cands[0].novelty_label}) {cands[0].hypothesis}"
            )


@app.command("version")
def version() -> None:
    from materials_agent import __version__

    console.print(__version__)


if __name__ == "__main__":
    app()
