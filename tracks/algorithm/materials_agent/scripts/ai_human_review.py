#!/usr/bin/env python
"""
AI 仿真人工抽检：分层抽样 + 双角色独立打分 + 分歧裁决。

无 LLM 时用规则量表仿真 A（严谨）/ B（怀疑）；
有 LLM 时两套 system prompt 独立打分，裁决偏保守。
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.llm import LLMClient

app = typer.Typer(add_completion=False)
DIMS = ("evidence_fit", "falsifiability", "type_purity", "novelty_honesty", "non_overclaim")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stratified_sample(gaps: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_type: dict[str, list[dict]] = defaultdict(list)
    for g in gaps:
        by_type[str(g.get("gap_type") or "underexplored")].append(g)
    for v in by_type.values():
        rng.shuffle(v)

    picked: list[dict] = []
    types = list(by_type.keys())
    # round-robin across types
    while len(picked) < min(n, len(gaps)):
        progress = False
        for t in types:
            if by_type[t] and len(picked) < n:
                picked.append(by_type[t].pop())
                progress = True
        if not progress:
            break
    return picked


def _rule_score_A(g: dict, known: list[dict]) -> dict[str, int]:
    """严谨派：证据与可证伪优先。"""
    from materials_agent.agents.evidence_selector import is_boilerplate_text

    ev = g.get("evidence_chain") or []
    quote_ok = sum(1 for e in ev if len(str(e.get("quote_or_basis") or "")) >= 40)
    noise = sum(
        1
        for e in ev
        if is_boilerplate_text(
            str(e.get("quote_or_basis") or ""),
            (e.get("provenance") or {}).get("section"),
        )
    )
    clean = max(0, len(ev) - noise)
    if not ev or clean == 0:
        evidence_fit = 0
    elif noise:
        evidence_fit = 1 if quote_ok >= 1 else 0
    else:
        evidence_fit = 2 if quote_ok >= 1 else 1
    scores = {
        "evidence_fit": evidence_fit,
        "falsifiability": 2
        if (g.get("suggested_next_step") and g.get("falsification_test") and len(str(g.get("falsification_test"))) > 40)
        else (1 if g.get("suggested_next_step") else 0),
        "type_purity": 2
        if g.get("gap_type") in {"missing_link", "contradiction", "underexplored", "method_gap"}
        else 0,
        "novelty_honesty": 1,
        "non_overclaim": 2,
    }
    title = (g.get("title") or "") + (g.get("description") or "")
    if any(x in title.lower() for x in ("discover", "首次证明", "confirmed discovery", "paradigm")):
        scores["non_overclaim"] = 0
    if g.get("gap_type") == "contradiction":
        if not (g.get("supporting_paper_ids") and g.get("contradicting_paper_ids")):
            scores["type_purity"] = 0
        else:
            scores["type_purity"] = 2
    # known overlap honesty
    if g.get("overlaps_known") and float(g.get("novelty") or 0) > 0.7:
        scores["novelty_honesty"] = 0
    elif g.get("overlaps_known"):
        scores["novelty_honesty"] = 1
    else:
        scores["novelty_honesty"] = 2
    return scores


def _rule_score_B(g: dict, known: list[dict]) -> dict[str, int]:
    """怀疑派：对新颖性与过宣称更苛刻。"""
    scores = _rule_score_A(g, known)
    # harsher novelty
    if float(g.get("novelty") or 0) >= 0.6 and g.get("overlaps_known"):
        scores["novelty_honesty"] = 0
    if "paradigm" in (g.get("title") or "").lower():
        scores["non_overclaim"] = min(scores["non_overclaim"], 1)
        scores["novelty_honesty"] = min(scores["novelty_honesty"], 1)
    # method_gap without experimental cue in next step → revise pressure
    next_s = str(g.get("suggested_next_step") or "").lower()
    if g.get("gap_type") == "method_gap" and not any(
        x in next_s for x in ("experiment", "synthesis", "database", "materials project", "oqmd")
    ):
        scores["falsifiability"] = min(scores["falsifiability"], 1)
    # single-paper contradiction mirrored ids: acceptable but not perfect for B
    if g.get("gap_type") == "contradiction":
        s, c = set(g.get("supporting_paper_ids") or []), set(g.get("contradicting_paper_ids") or [])
        if s == c and len(s) == 1:
            scores["evidence_fit"] = min(scores["evidence_fit"], 1)
    return scores


def _decision(scores: dict[str, int]) -> str:
    total = sum(scores.values())
    if any(v == 0 for v in scores.values()) or total <= 3:
        return "reject"
    if total <= 5:
        return "revise"
    return "keep"


def _llm_score(llm: LLMClient, role: str, g: dict, papers_by_id: dict) -> dict[str, int] | None:
    paper_bits = []
    for pid in (g.get("supporting_paper_ids") or [])[:3]:
        p = papers_by_id.get(pid) or {}
        paper_bits.append({"id": pid, "title": p.get("title"), "abstract": (p.get("abstract") or "")[:400]})
    system = (
        "You are Reviewer A: a strict materials scientist. Penalize weak evidence and unfalsifiable gaps."
        if role == "A"
        else "You are Reviewer B: a skeptical methodologist. Penalize novelty inflation, known-as-new, and overclaim."
    )
    payload = llm.chat_json(
        system=system
        + " Score each dimension 0/1/2. Return JSON "
        '{"evidence_fit":0,"falsifiability":0,"type_purity":0,"novelty_honesty":0,"non_overclaim":0,"notes":"..."}',
        user=json.dumps({"gap": g, "papers": paper_bits}, ensure_ascii=False)[:6000],
        step="review",
        validator=lambda d: all(k in d for k in DIMS),
    )
    if not payload:
        return None
    out = {}
    for k in DIMS:
        try:
            out[k] = max(0, min(2, int(payload[k])))
        except Exception:
            out[k] = 0
    out["_notes"] = str(payload.get("notes") or "")
    return out


def adjudicate(a: dict[str, int], b: dict[str, int]) -> tuple[dict[str, int], str, list[str]]:
    final = {}
    disagreements = []
    for k in DIMS:
        va, vb = int(a[k]), int(b[k])
        final[k] = min(va, vb)  # conservative
        if va != vb:
            disagreements.append(f"{k}: A={va} B={vb} -> {final[k]}")
    return final, _decision(final), disagreements


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    gaps: Path = typer.Option(ROOT / "outputs/demo/gaps.json", "--gaps"),
    known: Path = typer.Option(ROOT / "outputs/demo/known_pairs.json", "--known"),
    papers: Path = typer.Option(ROOT / "outputs/demo/papers.json", "--papers"),
    config: Path = typer.Option(ROOT / "configs/demo_local.yaml", "-c", "--config"),
    n: int = typer.Option(10, "--n", help="sample size"),
    seed: int = typer.Option(42, "--seed"),
    use_llm: bool = typer.Option(False, "--use-llm"),
) -> None:
    if ctx.invoked_subcommand is not None:
        return
    run_review(gaps, known, papers, config, n, seed, use_llm)


def run_review(
    gaps: Path,
    known: Path,
    papers: Path,
    config: Path,
    n: int,
    seed: int,
    use_llm: bool,
) -> None:
    gap_list = _load_json(gaps)
    known_list = _load_json(known) if known.exists() else []
    paper_list = _load_json(papers) if papers.exists() else []
    papers_by_id = {p["id"]: p for p in paper_list if isinstance(p, dict) and "id" in p}

    sample = stratified_sample(gap_list, n=n, seed=seed)
    llm = None
    if use_llm:
        cfg = load_config(config)
        llm = LLMClient(cfg.llm)
        if not llm.enabled:
            print("WARN: --use-llm set but no API key; falling back to rule reviewers")
            llm = None

    rows = []
    for g in sample:
        if llm:
            sa = _llm_score(llm, "A", g, papers_by_id) or _rule_score_A(g, known_list)
            sb = _llm_score(llm, "B", g, papers_by_id) or _rule_score_B(g, known_list)
            mode = "llm+fallback"
        else:
            sa = _rule_score_A(g, known_list)
            sb = _rule_score_B(g, known_list)
            mode = "rules"

        # strip notes keys for scoring
        sa_s = {k: int(sa[k]) for k in DIMS}
        sb_s = {k: int(sb[k]) for k in DIMS}
        final, decision, disag = adjudicate(sa_s, sb_s)
        rows.append(
            {
                "gap_id": g.get("id"),
                "gap_type": g.get("gap_type"),
                "title": g.get("title"),
                "reviewer_A": sa_s,
                "reviewer_B": sb_s,
                "final_scores": final,
                "final_total": sum(final.values()),
                "decision": decision,
                "disagreements": disag,
                "mode": mode,
                "A_notes": sa.get("_notes", ""),
                "B_notes": sb.get("_notes", ""),
            }
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
    out_dir = ROOT / "experiments" / "reviews" / f"round_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "created_utc": stamp,
        "seed": seed,
        "n_requested": n,
        "n_sampled": len(rows),
        "use_llm": bool(llm),
        "counts": {
            "keep": sum(1 for r in rows if r["decision"] == "keep"),
            "revise": sum(1 for r in rows if r["decision"] == "revise"),
            "reject": sum(1 for r in rows if r["decision"] == "reject"),
        },
        "items": rows,
    }
    (out_dir / "scores.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        f"# AI 仿真人工抽检报告 · round_{stamp}",
        "",
        f"- seed: `{seed}` · sampled: **{len(rows)}** · mode: `{'llm' if llm else 'rules'}`",
        f"- keep/revise/reject: **{summary['counts']['keep']}** / **{summary['counts']['revise']}** / **{summary['counts']['reject']}**",
        "",
        "> 本报告为 AI/规则双人审仿真，不替代领域专家终审。",
        "",
        "| Gap | Type | A合计 | B合计 | Final | Decision | 分歧 |",
        "|-----|------|-------|-------|-------|----------|------|",
    ]
    for r in rows:
        ta = sum(r["reviewer_A"].values())
        tb = sum(r["reviewer_B"].values())
        disag = "; ".join(r["disagreements"][:2]) or "—"
        lines.append(
            f"| `{r['gap_id']}` | {r['gap_type']} | {ta} | {tb} | {r['final_total']} | "
            f"**{r['decision']}** | {disag.replace('|', '/')} |"
        )
    lines += [
        "",
        "## 制度说明",
        "",
        "- 评审 A：证据与可证伪优先（严谨派）",
        "- 评审 B：新颖性膨胀与过宣称敏感（怀疑派）",
        "- 裁决：逐维取 min(A,B)（保守），再按总分映射 keep/revise/reject",
        "",
        "协议详见 `experiments/human_review_checklist.md`。",
        "",
    ]
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_dir}")
    print(json.dumps(summary["counts"], ensure_ascii=False))


if __name__ == "__main__":
    app()
