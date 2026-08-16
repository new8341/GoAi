"""Export survey run artifacts to LaTeX + BibTeX (handbook A04)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from materials_agent.evidence_attribution import annotate_retrieval_databases, gap_databases_summary
from materials_agent.models import (
    ConsistencyReport,
    ExtractedRecord,
    KnownPair,
    Paper,
    ResearchGap,
)


def _latex_escape(text: str) -> str:
    s = text or ""
    unicode_map = {
        "κ": r"$\kappa$",
        "α": r"$\alpha$",
        "β": r"$\beta$",
        "γ": r"$\gamma$",
        "Δ": r"$\Delta$",
        "μ": r"$\mu$",
        "σ": r"$\sigma$",
        "…": "...",
        "–": "--",
        "—": "---",
        "‐": "-",
        "‑": "-",
        "′": "'",
        "″": "''",
        "“": "``",
        "”": "''",
        "‘": "`",
        "’": "'",
    }
    for src, dst in unicode_map.items():
        s = s.replace(src, dst)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    # Protect already-inserted math dollars from the $ escape pass.
    parts = re.split(r"(\$[^$]*\$)", s)
    out: list[str] = []
    for part in parts:
        if part.startswith("$") and part.endswith("$") and len(part) > 1:
            out.append(part)
            continue
        out.append("".join(repl.get(ch, ch) for ch in part))
    return "".join(out)


def _find_exe(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    local = Path.home() / "AppData" / "Local" / "Programs"
    candidates = [
        local / "tectonic" / "tectonic.exe",
        local / "MiKTeX" / "miktex" / "bin" / "x64" / f"{name}.exe",
        Path(r"C:\Program Files\MiKTeX\miktex\bin\x64") / f"{name}.exe",
        Path(r"C:\Program Files\tectonic") / "tectonic.exe",
    ]
    for path in candidates:
        if path.name.lower() == f"{name}.exe".lower() and path.is_file():
            return str(path)
        if name == "tectonic" and path.name.lower() == "tectonic.exe" and path.is_file():
            return str(path)
    return None


def _bib_key(paper_id: str) -> str:
    key = re.sub(r"[^A-Za-z0-9]", "", paper_id)
    return key or "paper"


def _load_run(run_dir: Path) -> dict[str, Any]:
    def load(name: str, default: Any) -> Any:
        path = run_dir / name
        if not path.is_file():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    papers = [Paper.model_validate(p) for p in load("papers.json", [])]
    gaps = [ResearchGap.model_validate(g) for g in load("gaps.json", [])]
    extractions = [ExtractedRecord.model_validate(e) for e in load("extractions.json", [])]
    known_raw = load("known_pairs.json", [])
    known = [KnownPair.model_validate(k) for k in known_raw]
    queries = load("queries.json", [])
    consistency = None
    if (run_dir / "consistency.json").is_file():
        consistency = ConsistencyReport.model_validate(load("consistency.json", {}))
    meta = {
        "topic": load("bundle.json", {}).get("topic") if (run_dir / "bundle.json").is_file() else "",
        "subfield": load("bundle.json", {}).get("subfield")
        if (run_dir / "bundle.json").is_file()
        else "",
    }
    if not meta["topic"] and (run_dir / "report.md").is_file():
        first = (run_dir / "report.md").read_text(encoding="utf-8").splitlines()[:1]
        if first and first[0].startswith("#"):
            meta["topic"] = first[0].lstrip("# ").replace("Literature Survey Report:", "").strip()
    annotate_retrieval_databases(papers, gaps, extractions)
    return {
        "papers": papers,
        "gaps": gaps,
        "extractions": extractions,
        "known": known,
        "queries": queries if isinstance(queries, list) else [],
        "consistency": consistency,
        "topic": meta["topic"] or "materials survey",
        "subfield": meta["subfield"] or "materials",
    }


def build_bibtex(papers: list[Paper]) -> str:
    lines: list[str] = []
    for p in papers:
        key = _bib_key(p.id)
        title = (p.title or p.id).replace("{", "").replace("}", "")
        authors = " and ".join(p.authors) if p.authors else "Unknown"
        year = p.year or 2024
        note = f"Retrieved via literature database: {p.source or 'unknown'}"
        entry = [
            f"@article{{{key},",
            f"  title = {{{title}}},",
            f"  author = {{{authors}}},",
            f"  year = {{{year}}},",
            f"  note = {{{note}}},",
        ]
        if p.doi:
            entry.append(f"  doi = {{{p.doi}}},")
        if p.url:
            entry.append(f"  url = {{{p.url}}},")
        entry.append(f"  howpublished = {{Database: {p.source or 'unknown'}}},")
        entry.append("}")
        lines.append("\n".join(entry))
    return "\n\n".join(lines) + ("\n" if lines else "")


def build_report_tex(
    *,
    topic: str,
    subfield: str,
    papers: list[Paper],
    extractions: list[ExtractedRecord],
    gaps: list[ResearchGap],
    known: list[KnownPair],
    queries: list[str],
    consistency: ConsistencyReport | None,
) -> str:
    body: list[str] = [
        r"\documentclass[11pt,a4paper]{article}",
        r"\usepackage[margin=1in]{geometry}",
        r"\usepackage{iftex}",
        r"\ifPDFTeX",
        r"  \usepackage[T1]{fontenc}",
        r"  \usepackage[utf8]{inputenc}",
        r"\else",
        r"  \usepackage{fontspec}",
        r"\fi",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage{hyperref}",
        r"\usepackage{url}",
        r"\title{" + _latex_escape(f"Literature Survey Report: {topic}") + "}",
        r"\author{GOAI Track 3 Materials Agent}",
        r"\date{\today}",
        r"\begin{document}",
        r"\maketitle",
        r"\begin{itemize}",
        rf"\item Subfield: {_latex_escape(subfield)}",
        rf"\item Papers screened: {len(papers)}",
        rf"\item Research Gaps: {len(gaps)}",
        rf"\item Known dense pairs: {len(known)}",
        r"\end{itemize}",
        r"\section{Scope and method}",
        r"Pipeline: query rewrite $\rightarrow$ multi-query retrieve $\rightarrow$ "
        r"evidence-grounded extract $\rightarrow$ gap identify $\rightarrow$ "
        r"gap review $\rightarrow$ consistency check $\rightarrow$ report.",
        r"\subsection{Query variants}",
        r"\begin{itemize}",
    ]
    for q in queries:
        body.append(rf"\item {_latex_escape(q)}")
    if not queries:
        body.append(r"\item (none recorded)")
    body.append(r"\end{itemize}")

    body += [
        r"\section{Screened literature}",
        r"\begin{longtable}{llrlp{5.2cm}l}",
        r"\toprule ID & Year & Rel. & Database & Title & DOI \\ \midrule",
        r"\endfirsthead",
        r"\toprule ID & Year & Rel. & Database & Title & DOI \\ \midrule",
        r"\endhead",
    ]
    for p in papers:
        body.append(
            f"{_latex_escape(p.id)} & {p.year or '-'} & {p.relevance_score:.2f} & "
            f"{_latex_escape(p.source or 'unknown')} & {_latex_escape(p.title[:80])} & "
            f"{_latex_escape(p.doi or '-')} \\\\"
        )
    body.append(r"\bottomrule\end{longtable}")

    body.append(r"\section{Known dense regions}")
    if known:
        body.append(r"\begin{itemize}")
        for k in known[:20]:
            body.append(
                rf"\item {_latex_escape(k.material)} / {_latex_escape(k.property)} "
                rf"(count={k.count})"
            )
        body.append(r"\end{itemize}")
    else:
        body.append(r"No frequent material--property pairs above threshold.")

    body.append(r"\section{Structured knowledge extractions}")
    for e in extractions:
        body.append(rf"\subsection{{{_latex_escape(e.paper_id)}}}")
        body.append(
            rf"Materials: {_latex_escape(', '.join(e.materials) or '---')}; "
            rf"Properties: {_latex_escape(', '.join(e.properties) or '---')}."
        )
        if e.evidence:
            body.append(r"\begin{itemize}")
            for ev in e.evidence:
                db = ev.retrieval_database or "unknown"
                body.append(
                    rf"\item Database: \texttt{{{_latex_escape(db)}}}. "
                    + _latex_escape(ev.quote_or_basis[:220])
                )
            body.append(r"\end{itemize}")

    body.append(r"\section{Research Gap inventory}")
    for g in gaps:
        dbs = ", ".join(gap_databases_summary(g)) or "unknown"
        body.append(rf"\subsection{{{_latex_escape(g.id)}: {_latex_escape(g.title)}}}")
        body.append(rf"Databases used: \texttt{{{_latex_escape(dbs)}}}.")
        body.append(_latex_escape(g.description))
        body.append(r"\paragraph{Evidence chain}")
        body.append(r"\begin{itemize}")
        for ev in g.evidence_chain:
            db = ev.retrieval_database or "unknown"
            cite = _bib_key(ev.paper_id)
            body.append(
                rf"\item Database: \texttt{{{_latex_escape(db)}}}; "
                rf"cite~\cite{{{cite}}}. "
                + _latex_escape(f"{ev.claim}: {ev.quote_or_basis[:200]}")
            )
        if not g.evidence_chain:
            body.append(r"\item (no evidence spans)")
        body.append(r"\end{itemize}")
        if g.suggested_next_step:
            body.append(
                r"\paragraph{Suggested next step} " + _latex_escape(g.suggested_next_step)
            )
        if g.falsification_test:
            body.append(
                r"\paragraph{Falsification} " + _latex_escape(g.falsification_test)
            )

    body.append(r"\section{Consistency check}")
    if consistency:
        status = "PASS" if consistency.ok else "FAIL"
        body.append(rf"Status: \textbf{{{status}}}; issues: {len(consistency.issues)}.")
    else:
        body.append("Not run.")

    body += [
        r"\bibliographystyle{plain}",
        r"\bibliography{references}",
        r"\end{document}",
        "",
    ]
    return "\n".join(body)


def try_compile_pdf(tex_dir: Path, tex_name: str = "report.tex") -> Path | None:
    """Compile with tectonic or pdflatex if available; else return None."""
    tex_path = tex_dir / tex_name
    if not tex_path.is_file():
        return None
    pdf = tex_dir / "report.pdf"
    tectonic = _find_exe("tectonic")
    if tectonic:
        try:
            subprocess.run(
                [tectonic, "-X", "compile", tex_name],
                cwd=tex_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if pdf.is_file():
                return pdf
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            pass

    pdflatex = _find_exe("pdflatex")
    if pdflatex:
        bibtex = _find_exe("bibtex")
        try:
            for cmd in (
                [pdflatex, "-interaction=nonstopmode", tex_name],
                ([bibtex, "report"] if bibtex else None),
                [pdflatex, "-interaction=nonstopmode", tex_name],
                [pdflatex, "-interaction=nonstopmode", tex_name],
            ):
                if not cmd:
                    continue
                subprocess.run(
                    cmd,
                    cwd=tex_dir,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            if pdf.is_file():
                return pdf
        except (subprocess.TimeoutExpired, OSError):
            return None
    return None


def export_survey_latex(
    run_dir: Path | str,
    *,
    compile_pdf: bool = True,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    dest = Path(out_dir) if out_dir else run_dir
    dest.mkdir(parents=True, exist_ok=True)
    data = _load_run(run_dir)
    tex = build_report_tex(
        topic=data["topic"],
        subfield=data["subfield"],
        papers=data["papers"],
        extractions=data["extractions"],
        gaps=data["gaps"],
        known=data["known"],
        queries=data["queries"],
        consistency=data["consistency"],
    )
    bib = build_bibtex(data["papers"])
    tex_path = dest / "report.tex"
    bib_path = dest / "references.bib"
    tex_path.write_text(tex, encoding="utf-8")
    bib_path.write_text(bib, encoding="utf-8")
    # Persist annotated gaps back when writing into the run dir
    if dest.resolve() == run_dir.resolve():
        (run_dir / "gaps.json").write_text(
            json.dumps([g.model_dump() for g in data["gaps"]], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    pdf_path = None
    compile_note = "skipped"
    if compile_pdf:
        pdf = try_compile_pdf(dest)
        if pdf:
            pdf_path = str(pdf)
            compile_note = "ok"
        else:
            compile_note = (
                "no_engine_or_failed; install tectonic or pdflatex+bibtex and re-run"
            )
    return {
        "run_dir": str(run_dir),
        "tex": str(tex_path),
        "bib": str(bib_path),
        "pdf": pdf_path,
        "compile": compile_note,
        "papers": len(data["papers"]),
        "gaps": len(data["gaps"]),
    }
