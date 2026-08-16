#!/usr/bin/env python
"""Score automatic gaps against frozen human gold standard."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

app = typer.Typer(add_completion=False)

TIER_TO_SCORE = {"low": 0.35, "mid": 0.55, "high": 0.75}


def _load(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _match(auto: dict, gold: dict) -> bool:
    key = str(gold.get("match_key") or "").lower()
    gid = str(auto.get("id") or "").lower()
    title = str(auto.get("title") or "").lower()
    desc = str(auto.get("description") or "").lower()
    if key == gid:
        return True
    if key and key in gid:
        return True
    # keyword overlap on title/desc
    tokens = [t for t in key.replace("–", " ").replace("-", " ").split() if len(t) > 3]
    if not tokens:
        return False
    blob = f"{title} {desc}"
    hits = sum(1 for t in tokens if t in blob)
    return hits >= max(2, len(tokens) // 2)


def score(gaps: list[dict], gold_items: list[dict]) -> dict:
    matched = 0
    type_ok = 0
    evidence_ok = 0
    action_ok = 0
    novelty_abs_err: list[float] = []
    true_pos = 0
    false_pos_risk = 0
    details: list[dict] = []

    auto_by_id = {str(g.get("id")): g for g in gaps}
    for gitem in gold_items:
        key = gitem["match_key"]
        auto = auto_by_id.get(key)
        if auto is None:
            for g in gaps:
                if _match(g, gitem):
                    auto = g
                    break
        if auto is None:
            # gold negative examples may not appear in auto set — expected
            if not gitem.get("is_true_gap"):
                details.append({"match_key": key, "status": "absent_ok_negative"})
                continue
            details.append({"match_key": key, "status": "missing_auto"})
            continue

        matched += 1
        if gitem.get("is_true_gap"):
            true_pos += 1
        else:
            false_pos_risk += 1

        type_hit = auto.get("gap_type") == gitem.get("correct_type")
        type_ok += int(type_hit)

        has_ev = bool(auto.get("evidence_chain"))
        evidence_ok += int(has_ev == bool(gitem.get("evidence_ok")))

        act = len(str(auto.get("suggested_next_step") or "")) >= 20
        action_ok += int(act == bool(gitem.get("actionability_ok")))

        tier = str(gitem.get("novelty_tier") or "mid")
        target = TIER_TO_SCORE.get(tier, 0.55)
        nov = float(auto.get("novelty") or 0.5)
        novelty_abs_err.append(abs(nov - target))

        details.append(
            {
                "match_key": key,
                "auto_id": auto.get("id"),
                "type_ok": type_hit,
                "auto_type": auto.get("gap_type"),
                "gold_type": gitem.get("correct_type"),
                "auto_novelty": nov,
                "gold_tier": tier,
            }
        )

    n = max(1, matched)
    report = {
        "n_gold": len(gold_items),
        "n_matched": matched,
        "coverage": round(matched / max(1, len(gold_items)), 3),
        "type_accuracy": round(type_ok / n, 3),
        "evidence_agreement": round(evidence_ok / n, 3),
        "actionability_agreement": round(action_ok / n, 3),
        "novelty_mae": round(sum(novelty_abs_err) / max(1, len(novelty_abs_err)), 3)
        if novelty_abs_err
        else None,
        "true_gap_matches": true_pos,
        "negative_leaks": false_pos_risk,
        "details": details,
    }
    return report


@app.command()
def main(
    gaps: Path = typer.Option(ROOT / "outputs/demo/gaps.json", "--gaps"),
    gold: Path = typer.Option(
        ROOT / "experiments/gold_gaps/gold_set_v1.json", "--gold"
    ),
    out: Path = typer.Option(ROOT / "outputs/demo/gold_score.json", "--out"),
) -> None:
    gap_rows = _load(gaps)
    if isinstance(gap_rows, dict):
        gap_rows = gap_rows.get("gaps") or []
    gold_doc = _load(gold)
    items = gold_doc["items"] if isinstance(gold_doc, dict) else gold_doc
    report = score(gap_rows, items)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Gold standard score",
        "",
        f"- gold items: **{report['n_gold']}**",
        f"- matched auto gaps: **{report['n_matched']}**",
        f"- coverage: **{report['coverage']}**",
        f"- type accuracy: **{report['type_accuracy']}**",
        f"- evidence agreement: **{report['evidence_agreement']}**",
        f"- actionability agreement: **{report['actionability_agreement']}**",
        f"- novelty MAE vs tier: **{report['novelty_mae']}**",
        "",
    ]
    md_path = out.with_suffix(".md")
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "details"}, ensure_ascii=False, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    app()
