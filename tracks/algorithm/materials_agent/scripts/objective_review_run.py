"""Objective (non-domain-expert) auto-review for a survey run directory.

Judges engineering/evidence standards that can be checked without materials expertise.
Domain items (D*) and ambiguous scientific taste items stay unsure.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from materials_agent.agents.evidence import quote_in_source
from materials_agent.agents.evidence_selector import is_boilerplate_text
from materials_agent.expert_review_pack import build_expert_review_pack, write_expert_review_pack
from materials_agent.topic_focus import extract_topic_materials, topic_property_tokens


PARSER_OK = {"mineru", "grobid", "grobid_fusion"}
OVERCLAIM = ("discover", "首次证明", "paradigm", "confirmed discovery", "首次发现")


def _fold(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def _verdict(v: str, notes: str = "", *, auto: str = "objective") -> dict[str, Any]:
    return {
        "verdict": v,
        "notes": notes,
        "auto": auto,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _load(run_dir: Path, name: str) -> Any:
    path = run_dir / name
    if not path.is_file():
        return None
    if path.suffix == ".md":
        return path.read_text(encoding="utf-8")
    return json.loads(path.read_text(encoding="utf-8"))


def run_verify_like(run_dir: Path, *, min_ratio: float = 0.5) -> dict[str, Any]:
    papers = _load(run_dir, "papers.json") or []
    gaps = _load(run_dir, "gaps.json") or []
    index = _load(run_dir, "fulltext_index.json") or []
    paper_by_id = {p.get("id"): p for p in papers if isinstance(p, dict)}
    parsed = [
        e
        for e in index
        if e.get("fulltext_source") in PARSER_OK and e.get("pdf_hash")
    ]
    n = max(1, len(papers))
    ratio = len(parsed) / n
    fulltext_spans = 0
    invalid: list[str] = []
    for gap in gaps:
        for span in gap.get("evidence_chain") or []:
            loc = str(span.get("location") or "")
            if not loc.startswith("fulltext"):
                continue
            fulltext_spans += 1
            paper = paper_by_id.get(span.get("paper_id")) or {}
            source = paper.get("full_text") or paper.get("abstract") or ""
            prov = span.get("provenance") or {}
            if not prov.get("pdf_hash") or not prov.get("chunk_id"):
                invalid.append(f"{gap.get('id')}:missing_provenance")
            elif not quote_in_source(span.get("quote_or_basis") or "", source):
                invalid.append(f"{gap.get('id')}:quote_not_in_source")
    local_cache = any(e.get("fulltext_source") == "local_cache" for e in index)
    checks = [
        ("oa_papers_available", len(papers) > 0, f"papers={len(papers)}"),
        ("parsed_oa_ratio", ratio >= min_ratio, f"parsed={len(parsed)}/{len(papers)} threshold={min_ratio}"),
        ("no_local_cache_as_production", not local_cache, "ok" if not local_cache else "local_cache present"),
        ("fulltext_gap_spans", fulltext_spans > 0, f"count={fulltext_spans}"),
        ("verifiable_gap_spans", not invalid, "; ".join(invalid[:20])),
    ]
    passed = all(ok for _, ok, _ in checks)
    report = {
        "profile": "objective_review",
        "status": "PASS" if passed else "FAIL",
        "checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in checks],
        "output_dir": str(run_dir),
    }
    # U1: never overwrite production_verification.json (owned by verify_production).
    (run_dir / "objective_verify_shadow.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def auto_judge(run_dir: Path, pack: dict[str, Any]) -> dict[str, Any]:
    papers = {p["id"]: p for p in (pack.get("objects") or {}).get("papers") or []}
    gaps_raw = _load(run_dir, "gaps.json") or []
    chunks = {
        c.get("chunk_id"): c
        for c in (_load(run_dir, "evidence_chunks.json") or [])
        if c.get("chunk_id")
    }
    topic = pack.get("topic") or ""
    mats = extract_topic_materials(topic)
    props = topic_property_tokens(topic)
    verify = _load(run_dir, "production_verification.json") or {}
    consistency = _load(run_dir, "consistency.json") or {}
    metrics = _load(run_dir, "optimization_metrics.json") or {}
    science = _load(run_dir, "science_review.json") or {}
    report_md = _load(run_dir, "report.md") or ""
    flags = metrics.get("pass_flags") or {}
    n_papers = max(1, len(papers))
    n_ft = sum(
        1
        for p in papers.values()
        if (p.get("fulltext_source") or "") in PARSER_OK
    )
    ft_ratio = n_ft / n_papers

    verdicts: dict[str, dict[str, Any]] = {}

    def set_check(check_id: str, verdict: str, notes: str = "") -> None:
        verdicts[check_id] = _verdict(verdict, notes)

    # Run-level from pack objects
    for check in ((pack.get("objects") or {}).get("run") or {}).get("checks") or []:
        sid = check["standard_id"]
        cid = check["check_id"]
        hint = check.get("machine_hint") or {}
        if sid == "R1":
            st = verify.get("status")
            if st == "PASS":
                set_check(cid, "pass", "production_verification PASS")
            elif st == "FAIL":
                set_check(cid, "fail", json.dumps(verify.get("checks"), ensure_ascii=False)[:240])
            else:
                set_check(cid, "na", "verification missing before auto-run")
        elif sid == "R2":
            ok = consistency.get("ok")
            set_check(cid, "pass" if ok else "fail", f"consistency.ok={ok}")
        elif sid == "R3":
            st = science.get("status")
            if st == "PASS":
                set_check(cid, "pass", science.get("one_liner") or "science_review PASS")
            elif st == "FAIL":
                set_check(cid, "fail", science.get("one_liner") or "science_review FAIL")
            else:
                set_check(cid, "na", "science_review not present")
        elif sid == "R4":
            ok = bool(flags.get("topic_hit_rate")) and bool(flags.get("gap_material_alignment"))
            set_check(
                cid,
                "pass" if ok else "fail",
                f"topic_hit={metrics.get('topic_hit_rate')} gap_align={metrics.get('gap_material_alignment')}",
            )
        elif sid == "R5":
            set_check(
                cid,
                "pass" if ft_ratio >= 0.5 else "fail",
                f"fulltext_ratio={ft_ratio:.3f} ({n_ft}/{n_papers})",
            )
        elif sid == "X1":
            set_check(cid, "pass", f"gaps_json_count={len(gaps_raw)}")
        elif sid == "X2":
            titles = [g.get("title") or "" for g in gaps_raw]
            missing = [t for t in titles if t and t[:40] not in report_md]
            set_check(
                cid,
                "pass" if not missing else "fail",
                "report contains gap titles" if not missing else f"missing in report: {missing[:2]}",
            )
        elif sid == "X3":
            set_check(cid, "unsure", "backend claim needs audit manual glance")
        else:
            if hint.get("pass") is True:
                set_check(cid, "pass", "machine_hint.pass")
            elif hint.get("pass") is False:
                set_check(cid, "fail", "machine_hint.fail")
            else:
                set_check(cid, "unsure", "no objective rule")

    # Papers
    for paper in (pack.get("objects") or {}).get("papers") or []:
        pid = paper["id"]
        title = f"{paper.get('title') or ''} {paper.get('abstract_preview') or ''}"
        blob = title.lower()
        mat_hit = (not mats) or any(m.lower() in blob for m in mats)
        prop_hit = (not props) or any(x in blob for x in props)
        src = paper.get("fulltext_source") or ""
        for check in paper.get("checks") or []:
            sid, cid = check["standard_id"], check["check_id"]
            if sid == "P1":
                set_check(cid, "pass" if mat_hit else "fail", f"materials={mats}")
            elif sid == "P2":
                set_check(cid, "pass" if prop_hit else "fail", f"props={sorted(props)[:8]}")
            elif sid == "P3":
                ok = bool(paper.get("doi") or check.get("display", {}).get("url"))
                # also from display
                disp = check.get("display") or {}
                ok = bool(disp.get("doi") or disp.get("url") or paper.get("doi"))
                set_check(cid, "pass" if ok else "fail", f"doi={paper.get('doi')}")
            elif sid == "P4":
                if src in {"none", ""}:
                    set_check(cid, "na", "no fulltext")
                elif src == "local_cache":
                    set_check(cid, "fail", "local_cache")
                elif src in PARSER_OK:
                    set_check(cid, "pass", f"source={src}")
                else:
                    set_check(cid, "unsure", f"source={src}")

    # Gaps + evidence
    for gap in (pack.get("objects") or {}).get("gaps") or []:
        gid = gap["id"]
        gtype = gap.get("gap_type") or ""
        title = gap.get("title") or ""
        desc = gap.get("description") or ""
        next_s = gap.get("suggested_next_step") or ""
        fals = gap.get("falsification_test") or ""
        overclaim = any(x in (title + desc).lower() for x in OVERCLAIM)
        topic_hit = (not mats) or any(m.lower() in (title + desc + gid).lower() for m in mats)
        for check in gap.get("checks") or []:
            sid, cid = check["standard_id"], check["check_id"]
            hint = check.get("machine_hint") or {}
            if sid == "G1":
                # heuristic: too short / textbook-ish
                if len(title) < 12:
                    set_check(cid, "fail", "title too short")
                elif "is a thermoelectric" in (title + desc).lower():
                    set_check(cid, "fail", "looks like textbook statement")
                else:
                    set_check(cid, "unsure", "needs domain taste; structure ok")
            elif sid == "G2":
                allow = (
                    topic_hit
                    or gid.startswith("gap-missing-link")
                    or gid in {"gap-method-balance"}
                    or "limitation" in gtype.lower()
                )
                set_check(cid, "pass" if allow else "fail", f"mats={mats}; type={gtype}")
            elif sid == "G3":
                set_check(
                    cid,
                    "pass" if len(desc) >= 80 else "fail",
                    f"desc_len={len(desc)}",
                )
            elif sid in {"G4", "T2", "A3"}:
                set_check(cid, "unsure", "not fully objective")
            elif sid == "T1":
                if gtype != "contradiction":
                    set_check(cid, "na", "not contradiction")
                elif hint.get("pass") is True:
                    set_check(cid, "pass", "bilateral ids")
                else:
                    set_check(cid, "fail", str(hint))
            elif sid == "T3":
                if gtype != "missing_link":
                    set_check(cid, "na", "not missing_link")
                else:
                    ok = any(k in desc.lower() for k in ("corpus", "screened", "within this"))
                    set_check(cid, "pass" if ok else "fail", "corpus qualifier")
            elif sid == "T4":
                set_check(cid, "unsure", "open-question language is soft")
            elif sid == "A1":
                bad = "more research" in next_s.lower() or len(next_s) < 20
                set_check(cid, "fail" if bad else "pass", next_s[:120])
            elif sid == "A2":
                set_check(cid, "pass" if len(fals) >= 20 else "fail", fals[:120])
            elif sid == "N1":
                set_check(cid, "fail" if overclaim else "pass", "overclaim lexicon")
            elif sid == "N2":
                set_check(cid, "unsure", "novelty vs known needs judgment")
            elif sid.startswith("D"):
                set_check(cid, "unsure", "non-domain-expert auto review")
            else:
                if hint.get("pass") is True:
                    set_check(cid, "pass", "machine_hint")
                elif hint.get("pass") is False:
                    set_check(cid, "fail", "machine_hint")
                elif hint.get("na"):
                    set_check(cid, "na", "n/a for type")
                else:
                    set_check(cid, "unsure", "")

        for ev in gap.get("evidence") or []:
            quote = ev.get("quote") or ""
            prov = ev.get("provenance") or {}
            cid_chunk = prov.get("chunk_id")
            ch = chunks.get(cid_chunk) if cid_chunk else None
            in_chunk = bool(ch and quote_in_source(quote, ch.get("text") or ""))
            # also paper fulltext from pack display if needed
            noise = is_boilerplate_text(quote, prov.get("section"))
            for check in ev.get("checks") or []:
                sid, cid = check["standard_id"], check["check_id"]
                if sid == "E1":
                    # soft: very short or many bangs
                    if len(quote) < 24:
                        set_check(cid, "fail", "quote too short")
                    elif quote.count("!") > 2:
                        set_check(cid, "fail", "slogan-like")
                    else:
                        set_check(cid, "pass", "length/tone ok (not peer-reviewed)")
                elif sid == "E2":
                    set_check(
                        cid,
                        "pass" if in_chunk else "fail",
                        f"quote_in_chunk={in_chunk} chunk={cid_chunk}",
                    )
                elif sid == "E3":
                    ok = bool(ev.get("paper_id") and cid_chunk and prov.get("pdf_hash"))
                    set_check(cid, "pass" if ok else "fail", f"prov={prov}")
                elif sid == "E4":
                    set_check(cid, "fail" if noise else "pass", f"boilerplate={noise}")
                elif sid == "E5":
                    # overlap tokens between quote and gap title
                    qf, tf = _fold(quote), _fold(title)
                    overlap = sum(1 for w in mats if w.lower() in qf) + sum(
                        1 for w in list(props)[:6] if w in qf and w in tf
                    )
                    set_check(
                        cid,
                        "pass" if overlap or any(tok in qf for tok in tf.split()[:6] if len(tok) > 4) else "unsure",
                        f"overlap_score≈{overlap}",
                    )

    return verdicts


def summarize(verdicts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts = {"pass": 0, "fail": 0, "unsure": 0, "na": 0, "unset": 0}
    fails: list[str] = []
    for cid, row in verdicts.items():
        v = row.get("verdict") or "unset"
        counts[v] = counts.get(v, 0) + 1
        if v == "fail":
            fails.append(f"{cid}: {row.get('notes')}")
    must_fail = [f for f in fails if any(x in f for x in (":R1:", ":R2:", ":R5:", ":E2:", ":E3:", ":E4:", ":A1:", ":A2:", ":N1:", ":G2:", ":P1:", ":P3:"))]
    # check_id format object:id:SID
    must_fail = [f for f in fails if re.search(r":(R1|R2|R5|E2|E3|E4|A1|A2|N1|G2|P1|P3):", f)]
    status = "PASS" if not must_fail else "FAIL"
    return {"counts": counts, "must_fail": must_fail, "status": status, "fail_samples": fails[:20]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        default=ROOT / "outputs/user_jobs/20260810T155633Z-b775a5ec",
    )
    parser.add_argument("--min-fulltext-ratio", type=float, default=0.5)
    parser.add_argument("--skip-science", action="store_true")
    args = parser.parse_args()
    run_dir = args.run if args.run.is_absolute() else ROOT / args.run
    if not run_dir.is_dir():
        print(json.dumps({"error": f"run not found: {run_dir}"}, ensure_ascii=False))
        return 1

    run_id = str(run_dir.relative_to(ROOT / "outputs")).replace("\\", "/")
    verify = run_verify_like(run_dir, min_ratio=args.min_fulltext_ratio)

    science = None
    if not args.skip_science:
        try:
            from scripts.science_review_gate import main as science_main
            import typer

            # call underlying functions instead
            from materials_agent.config import load_config
            import scripts.science_review_gate as srg

            cfg = load_config(ROOT / "configs/production.yaml")
            # reuse gate entry via subprocess for isolation
            import subprocess

            proc = subprocess.run(
                [
                    "py",
                    "-3",
                    str(ROOT / "scripts/science_review_gate.py"),
                    "-c",
                    str(ROOT / "configs/production.yaml"),
                    "--run",
                    str(run_dir),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(ROOT)},
            )
            science = _load(run_dir, "science_review.json")
            if proc.returncode not in (0, 1) and science is None:
                science = {"status": "ERROR", "detail": proc.stderr[-500:]}
        except Exception as exc:  # noqa: BLE001
            science = {"status": "ERROR", "detail": str(exc)}

    pack = build_expert_review_pack(run_dir, run_id=run_id)
    write_expert_review_pack(run_dir, run_id=run_id)
    verdicts = auto_judge(run_dir, pack)
    summary = summarize(verdicts)

    out_json = {
        "run_id": run_id,
        "topic": pack.get("topic"),
        "reviewer": "auto-objective",
        "mode": "non-domain-expert objective QA",
        "verify": verify,
        "science_review": {
            "status": (science or {}).get("status"),
            "one_liner": (science or {}).get("one_liner"),
        },
        "summary": summary,
        "verdicts": verdicts,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    json_path = run_dir / "objective_review.json"
    json_path.write_text(json.dumps(out_json, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# Objective review {stamp}",
        "",
        f"- Run: `{run_id}`",
        f"- Topic: {pack.get('topic')}",
        f"- Reviewer: auto-objective (non-domain-expert)",
        f"- verify: **{verify.get('status')}**",
        f"- science_review: **{(science or {}).get('status') or 'n/a'}**",
        f"- objective must-status: **{summary['status']}**",
        f"- counts: `{json.dumps(summary['counts'], ensure_ascii=False)}`",
        "",
        "## Verify checks",
        "",
    ]
    for c in verify.get("checks") or []:
        md_lines.append(f"- {'PASS' if c['pass'] else 'FAIL'} `{c['name']}` — {c['detail']}")
    md_lines += ["", "## Must failures", ""]
    if summary["must_fail"]:
        for f in summary["must_fail"]:
            md_lines.append(f"- `{f}`")
    else:
        md_lines.append("- (none)")
    md_lines += ["", "## Notes", ""]
    md_lines.append("- D1–D3 and soft scientific taste items marked `unsure`.")
    md_lines.append("- E2 uses quote⊂chunk from evidence_chunks.json.")
    md_lines.append(f"- Full verdicts: `{json_path.as_posix()}`")
    md_path = ROOT / "experiments" / "reviews" / f"review-{stamp}-objective-{run_dir.name}.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(json.dumps({"run_id": run_id, "verify": verify.get("status"), "science": (science or {}).get("status"), "objective": summary, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" and verify.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
