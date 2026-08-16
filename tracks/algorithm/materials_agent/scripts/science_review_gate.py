#!/usr/bin/env python
"""Science-review gate (L0 mechanical + L1 AI dual-role) for 科学意义材料.

See experiments/reviews/科学抽检标准_AI可执行.md
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.agents.evidence_selector import is_boilerplate_text
from materials_agent.config import load_config, load_ontology
from materials_agent.topic_focus import extract_topic_materials, topic_property_tokens

import importlib.util

_ahr_spec = importlib.util.spec_from_file_location(
    "ai_human_review", ROOT / "scripts" / "ai_human_review.py"
)
_ahr = importlib.util.module_from_spec(_ahr_spec)
assert _ahr_spec.loader is not None
_ahr_spec.loader.exec_module(_ahr)
_decision = _ahr._decision
_rule_score_A = _ahr._rule_score_A
_rule_score_B = _ahr._rule_score_B
adjudicate = _ahr.adjudicate
stratified_sample = _ahr.stratified_sample

app = typer.Typer(add_completion=False)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _quote_in_chunk(quote: str, chunk_text: str) -> bool:
    q = _fold(quote)
    c = _fold(chunk_text)
    if len(q) < 20 or not c:
        return False
    if q in c:
        return True
    # tolerate truncation: probe middle window
    if len(q) > 80:
        mid = q[20:80]
        return mid in c
    return q[:40] in c


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(t) > 3}


def _claim_quote_overlap(gap: dict, quotes: list[str]) -> bool:
    title = f"{gap.get('title') or ''} {gap.get('description') or ''}"
    t_tok = _tokens(title)
    if not t_tok or not quotes:
        return False
    for q in quotes:
        q_tok = _tokens(q)
        if not q_tok:
            continue
        j = len(t_tok & q_tok) / max(1, len(t_tok))
        if j >= 0.08:
            return True
        # keyword hit
        for w in list(t_tok)[:12]:
            if w in _fold(q):
                return True
    return False


def _gap_topic_aligned(gap: dict, topic_mats: list[str]) -> bool:
    if not topic_mats:
        return True
    gid = str(gap.get("id") or "")
    if gid in {"gap-limitations", "gap-method-balance", "gap-default"}:
        return True
    if gid.startswith("gap-missing-link"):
        return True
    blob = f"{gid} {gap.get('title') or ''} {gap.get('description') or ''}".lower()
    return any(m.lower() in blob for m in topic_mats)


def _property_hit(gap: dict, quotes: list[str], props: set[str]) -> bool:
    if not props:
        return True
    blob = _fold(
        f"{gap.get('title') or ''} {gap.get('description') or ''} " + " ".join(quotes)
    )
    return any(p in blob for p in props)


def evaluate_l0(
    gaps: list[dict],
    chunks_by_id: dict[str, dict],
    topic: str,
    ontology: dict | None = None,
) -> dict[str, Any]:
    topic_mats = extract_topic_materials(topic, ontology)
    props = topic_property_tokens(topic, ontology)
    per_gap: list[dict[str, Any]] = []
    hard_fail = 0
    soft = {"S1": 0, "S2": 0, "S3": 0, "S4": 0}

    for g in gaps:
        issues: list[str] = []
        ev = g.get("evidence_chain") or []
        quotes = [str(e.get("quote_or_basis") or "") for e in ev]

        if len(ev) < 1:
            issues.append("H1:empty_evidence")
        for i, e in enumerate(ev):
            loc = str(e.get("location") or "")
            if loc not in {"fulltext", "chunk"}:
                issues.append(f"H2:span{i}_location={loc}")
            prov = e.get("provenance") or {}
            if not prov.get("pdf_hash") or not prov.get("chunk_id"):
                issues.append(f"H3:span{i}_missing_provenance")
            cid = prov.get("chunk_id")
            ch = chunks_by_id.get(cid) if cid else None
            quote = str(e.get("quote_or_basis") or "")
            if not ch or not _quote_in_chunk(quote, ch.get("text") or ""):
                issues.append(f"H4:span{i}_quote_not_in_chunk")
            if is_boilerplate_text(quote, prov.get("section")):
                issues.append(f"H5:span{i}_boilerplate")

        next_s = str(g.get("suggested_next_step") or "").strip()
        fals = str(g.get("falsification_test") or "").strip()
        if len(next_s) < 20 or len(fals) < 20 or "more research" in next_s.lower():
            issues.append("H6:weak_next_or_falsification")

        gtype = str(g.get("gap_type") or "")
        if gtype not in {"missing_link", "contradiction", "underexplored", "method_gap"}:
            issues.append(f"H7:bad_type={gtype}")
        if gtype == "contradiction":
            s = set(g.get("supporting_paper_ids") or [])
            c = set(g.get("contradicting_paper_ids") or [])
            if not s or not c or (s & c):
                issues.append("H8:contradiction_structure")

        hard_ok = not any(x.startswith("H") for x in issues)
        if not hard_ok:
            hard_fail += 1

        s1 = _gap_topic_aligned(g, topic_mats)
        s2 = _property_hit(g, quotes, props)
        s3 = _claim_quote_overlap(g, quotes)
        s4 = float(g.get("actionability") or 0) >= 0.35
        soft["S1"] += int(s1)
        soft["S2"] += int(s2)
        soft["S3"] += int(s3)
        soft["S4"] += int(s4)
        if not s1:
            issues.append("S1:topic_misaligned")
        if not s2:
            issues.append("S2:no_property_cue")
        if not s3:
            issues.append("S3:weak_claim_quote_overlap")
        if not s4:
            issues.append("S4:low_actionability")

        per_gap.append(
            {
                "gap_id": g.get("id"),
                "gap_type": gtype,
                "hard_ok": hard_ok,
                "issues": issues,
            }
        )

    n = max(1, len(gaps))
    rates = {
        "S1_topic_align": round(soft["S1"] / n, 4),
        "S2_property_cue": round(soft["S2"] / n, 4),
        "S3_claim_quote": round(soft["S3"] / n, 4),
        "S4_actionability": round(soft["S4"] / n, 4),
    }
    passed = (
        hard_fail == 0
        and rates["S1_topic_align"] >= 0.80
        and rates["S2_property_cue"] >= 0.60
        and rates["S3_claim_quote"] >= 0.60
        and rates["S4_actionability"] >= 1.0
    )
    return {
        "pass": passed,
        "gaps_total": len(gaps),
        "hard_fail_count": hard_fail,
        "soft_rates": rates,
        "targets": {
            "S1": 0.80,
            "S2": 0.60,
            "S3": 0.60,
            "S4": 1.0,
        },
        "topic_materials": topic_mats,
        "per_gap": per_gap,
    }


def _science_l1_decision(scores: dict[str, int]) -> str:
    """Map dual-role scores to keep/revise/reject for science gate.

    Hard zeros (evidence / falsifiability / type) → reject.
    Soft zeros (novelty honesty / overclaim) → revise, not reject.
    """
    hard_dims = ("evidence_fit", "falsifiability", "type_purity")
    total = sum(int(scores.get(k, 0)) for k in ("evidence_fit", "falsifiability", "type_purity", "novelty_honesty", "non_overclaim"))
    if any(int(scores.get(k, 0)) == 0 for k in hard_dims) or total <= 3:
        return "reject"
    if (
        int(scores.get("novelty_honesty", 0)) == 0
        or int(scores.get("non_overclaim", 0)) == 0
        or total <= 5
    ):
        return "revise"
    return "keep"


def evaluate_l1(
    gaps: list[dict],
    known: list[dict],
    n: int,
    seed: int,
) -> dict[str, Any]:
    sample_n = min(max(n, 3), len(gaps)) if gaps else 0
    if len(gaps) < 3:
        sample_n = len(gaps)
    sample = stratified_sample(gaps, n=sample_n, seed=seed) if gaps else []
    rows = []
    keep = revise = reject = 0
    for g in sample:
        sa = _rule_score_A(g, known)
        sb = _rule_score_B(g, known)
        final, _legacy, disagreements = adjudicate(sa, sb)
        decision = _science_l1_decision(final)
        if decision == "keep":
            keep += 1
        elif decision == "revise":
            revise += 1
        else:
            reject += 1
        rows.append(
            {
                "gap_id": g.get("id"),
                "gap_type": g.get("gap_type"),
                "decision": decision,
                "scores": final,
                "disagreements": disagreements,
                "total": sum(final.values()),
            }
        )
    sampled = max(1, len(sample))
    keep_rate = keep / sampled
    warning = None
    if len(gaps) < 3:
        warning = "gaps_total<3"
    # Integer 2/3: for n=3, keep>=2 passes (float 0.666… must not fail 0.67).
    keep_ok = keep * 3 >= len(sample) * 2 if sample else False
    passed = (
        len(sample) >= 1
        and reject == 0
        and keep_ok
        and (len(sample) >= 3 or len(gaps) < 3)
    )
    return {
        "pass": passed,
        "seed": seed,
        "sample_size": len(sample),
        "keep": keep,
        "revise": revise,
        "reject": reject,
        "keep_rate": round(keep_rate, 4),
        "sample_warning": warning,
        "rows": rows,
    }


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    l0 = report["L0"]
    l1 = report["L1"]
    lines = [
        f"# Science review {report['date']}",
        "",
        f"Run: `{report['run']}`",
        f"Config: `{report['config']}`",
        f"production_verification: {report.get('production_verification', 'n/a')}",
        f"**science_review_status: {report['status']}**",
        "",
        "## L0 mechanical",
        f"- pass: {l0['pass']}",
        f"- hard_fail_count: {l0['hard_fail_count']} / {l0['gaps_total']}",
        f"- soft_rates: {json.dumps(l0['soft_rates'], ensure_ascii=False)}",
        "",
        "| gap_id | hard_ok | issues |",
        "|--------|---------|--------|",
    ]
    for row in l0["per_gap"]:
        issues = "; ".join(row["issues"]) if row["issues"] else "—"
        lines.append(f"| {row['gap_id']} | {row['hard_ok']} | {issues} |")
    lines += [
        "",
        "## L1 AI dual-role sample",
        f"- pass: {l1['pass']}",
        f"- keep/revise/reject: {l1['keep']}/{l1['revise']}/{l1['reject']} (keep_rate={l1['keep_rate']})",
        f"- seed: {l1['seed']}",
        "",
        "| gap_id | decision | total | notes |",
        "|--------|----------|-------|-------|",
    ]
    for row in l1["rows"]:
        notes = "; ".join(row.get("disagreements") or []) or "—"
        lines.append(
            f"| {row['gap_id']} | {row['decision']} | {row['total']} | {notes} |"
        )
    lines += [
        "",
        f"Overall: {'accept' if report['status'] == 'PASS' else 'revise evidence / gap filters'}",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


@app.command()
def main(
    config: Path = typer.Option(ROOT / "configs/production.yaml", "-c", "--config"),
    run: Path = typer.Option(ROOT / "outputs/production", "--run"),
    n: int = typer.Option(5, "--n", help="L1 sample size (capped by gap count)"),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    cfg = load_config(config)
    run_dir = run if run.is_absolute() else ROOT / run
    gaps_path = run_dir / "gaps.json"
    chunks_path = run_dir / "evidence_chunks.json"
    known_path = run_dir / "known_pairs.json"
    verify_path = run_dir / "production_verification.json"
    if not gaps_path.is_file():
        raise SystemExit(f"missing {gaps_path}")

    gaps = _load(gaps_path)
    chunks = _load(chunks_path) if chunks_path.is_file() else []
    chunks_by_id = {c["chunk_id"]: c for c in chunks if isinstance(c, dict) and c.get("chunk_id")}
    known = _load(known_path) if known_path.is_file() else []
    verify_status = "n/a"
    if verify_path.is_file():
        verify_status = str((_load(verify_path) or {}).get("status") or "n/a")

    l0 = evaluate_l0(gaps, chunks_by_id, cfg.topic, load_ontology(cfg.ontology_path))
    l1 = evaluate_l1(gaps, known, n=n, seed=seed)
    status = "PASS" if (l0["pass"] and l1["pass"]) else "FAIL"
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report = {
        "status": status,
        "date": date,
        "run": str(run_dir.relative_to(ROOT)).replace("\\", "/"),
        "config": str(config).replace("\\", "/"),
        "topic": cfg.topic,
        "production_verification": verify_status,
        "L0": l0,
        "L1": l1,
        "one_liner": (
            f"science_review={status} | L0_hard_fail={l0['hard_fail_count']} | "
            f"L1 keep={l1['keep']}/{l1['sample_size']} reject={l1['reject']} | seed={seed}"
        ),
    }

    out_json = run_dir / "science_review.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    reviews = ROOT / "experiments" / "reviews"
    reviews.mkdir(parents=True, exist_ok=True)
    md_path = reviews / f"science-review-{date}-{run_dir.name}.md"
    _write_markdown(md_path, report)

    print(json.dumps({"status": status, "one_liner": report["one_liner"], "json": str(out_json), "md": str(md_path)}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    app()
