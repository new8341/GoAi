"""Build expert human-review packs: standards + concrete check objects per run."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from materials_agent.agents.evidence_selector import is_boilerplate_text
from materials_agent.topic_focus import extract_topic_materials, topic_property_tokens

ROOT = Path(__file__).resolve().parents[1]
STANDARDS_PATH = ROOT / "configs" / "expert_human_review_standards.json"


def load_standards() -> dict[str, Any]:
    return json.loads(STANDARDS_PATH.read_text(encoding="utf-8"))


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def _quote_in_text(quote: str, text: str) -> bool:
    q, t = _fold(quote), _fold(text)
    if len(q) < 16 or not t:
        return False
    if q in t:
        return True
    return len(q) > 60 and q[20:70] in t


def _std_index(standards: dict[str, Any]) -> dict[str, dict]:
    return {s["id"]: s for s in standards.get("standards") or []}


def _check(
    standard: dict[str, Any],
    *,
    object_type: str,
    object_id: str,
    display: dict[str, Any],
    machine_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "check_id": f"{object_type}:{object_id}:{standard['id']}",
        "standard_id": standard["id"],
        "category": standard["category"],
        "level": standard["level"],
        "title": standard["title"],
        "question": standard["question"],
        "pass_criteria": standard["pass_criteria"],
        "fail_signals": standard["fail_signals"],
        "object_type": object_type,
        "object_id": object_id,
        "display": display,
        "machine_hint": machine_hint or {},
        "human_verdict": None,
        "human_notes": "",
    }


def build_expert_review_pack(run_dir: Path, run_id: str | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir)
    run_id = run_id or run_dir.name
    standards_doc = load_standards()
    by_id = _std_index(standards_doc)

    def S(sid: str) -> dict[str, Any]:
        return by_id[sid]

    papers = []
    gaps = []
    chunks: dict[str, dict] = {}
    verify = {}
    consistency = {}
    metrics = {}
    science = {}
    fulltext_index: list[dict] = []
    topic = ""
    if (run_dir / "papers.json").is_file():
        papers = json.loads((run_dir / "papers.json").read_text(encoding="utf-8"))
    if (run_dir / "gaps.json").is_file():
        gaps = json.loads((run_dir / "gaps.json").read_text(encoding="utf-8"))
    if (run_dir / "evidence_chunks.json").is_file():
        rows = json.loads((run_dir / "evidence_chunks.json").read_text(encoding="utf-8"))
        chunks = {c["chunk_id"]: c for c in rows if c.get("chunk_id")}
    if (run_dir / "production_verification.json").is_file():
        verify = json.loads((run_dir / "production_verification.json").read_text(encoding="utf-8"))
    if (run_dir / "consistency.json").is_file():
        consistency = json.loads((run_dir / "consistency.json").read_text(encoding="utf-8"))
    if (run_dir / "optimization_metrics.json").is_file():
        metrics = json.loads((run_dir / "optimization_metrics.json").read_text(encoding="utf-8"))
    if (run_dir / "science_review.json").is_file():
        science = json.loads((run_dir / "science_review.json").read_text(encoding="utf-8"))
    if (run_dir / "fulltext_index.json").is_file():
        fulltext_index = json.loads((run_dir / "fulltext_index.json").read_text(encoding="utf-8"))
    if (run_dir / "bundle.json").is_file():
        bundle = json.loads((run_dir / "bundle.json").read_text(encoding="utf-8"))
        topic = str(bundle.get("topic") or "")
    if not topic and papers:
        topic = "unknown topic"

    topic_mats = extract_topic_materials(topic)
    props = topic_property_tokens(topic)
    ft_map = {r.get("paper_id"): r for r in fulltext_index if isinstance(r, dict)}
    n_papers = max(1, len(papers))
    n_ft = sum(1 for p in papers if p.get("full_text") or (ft_map.get(p.get("id")) or {}).get("fulltext_source") not in {None, "none", ""})

    run_checks = [
        _check(
            S("R1"),
            object_type="run",
            object_id=run_id,
            display={"label": "production_verification", "value": verify.get("status")},
            machine_hint={"pass": verify.get("status") == "PASS", "detail": verify},
        ),
        _check(
            S("R2"),
            object_type="run",
            object_id=run_id,
            display={"label": "consistency", "value": consistency.get("ok")},
            machine_hint={"pass": bool(consistency.get("ok")), "issues": consistency.get("issues") or []},
        ),
        _check(
            S("R3"),
            object_type="run",
            object_id=run_id,
            display={"label": "science_review", "value": science.get("status") or "not_run"},
            machine_hint={
                "pass": science.get("status") == "PASS" if science else None,
                "one_liner": science.get("one_liner"),
            },
        ),
        _check(
            S("R4"),
            object_type="run",
            object_id=run_id,
            display={
                "label": "optimization_metrics",
                "topic_hit_rate": metrics.get("topic_hit_rate"),
                "gap_align": metrics.get("gap_material_alignment"),
            },
            machine_hint={
                "pass": bool((metrics.get("pass_flags") or {}).get("topic_hit_rate"))
                and bool((metrics.get("pass_flags") or {}).get("gap_material_alignment"))
                if metrics
                else None,
                "metrics": metrics or None,
            },
        ),
        _check(
            S("R5"),
            object_type="run",
            object_id=run_id,
            display={"papers": len(papers), "fulltext_est": n_ft, "ratio": round(n_ft / n_papers, 3)},
            machine_hint={"pass": (n_ft / n_papers) >= 0.5},
        ),
        _check(
            S("X1"),
            object_type="run",
            object_id=run_id,
            display={"gaps_json_count": len(gaps)},
            machine_hint={"note": "打开用户端「研究空白」页对比条数与标题"},
        ),
        _check(
            S("X2"),
            object_type="run",
            object_id=run_id,
            display={"report": "report.md"},
            machine_hint={"note": "对照报告 Gap 列表与 gaps.json"},
        ),
        _check(
            S("X3"),
            object_type="run",
            object_id=run_id,
            display={"backend_claim": "见 audit retrieve.tool / papers.source"},
            machine_hint={"note": "调试端查看 audit.json retrieve 条目"},
        ),
    ]

    paper_objects = []
    for p in papers:
        pid = str(p.get("id") or "")
        blob = f"{p.get('title') or ''} {p.get('abstract') or ''}".lower()
        mat_hit = any(m.lower() in blob for m in topic_mats) if topic_mats else True
        prop_hit = any(x in blob for x in props) if props else True
        ft = ft_map.get(pid) or {}
        src = p.get("fulltext_source") or ft.get("fulltext_source") or ("fulltext" if p.get("full_text") else "none")
        checks = [
            _check(
                S("P1"),
                object_type="paper",
                object_id=pid,
                display={"title": p.get("title"), "year": p.get("year")},
                machine_hint={"pass": mat_hit, "topic_materials": topic_mats},
            ),
            _check(
                S("P2"),
                object_type="paper",
                object_id=pid,
                display={"title": p.get("title")},
                machine_hint={"pass": prop_hit, "property_tokens": sorted(props)},
            ),
            _check(
                S("P3"),
                object_type="paper",
                object_id=pid,
                display={"doi": p.get("doi"), "url": p.get("url") or p.get("oa_url")},
                machine_hint={"pass": bool(p.get("doi") or p.get("url") or p.get("oa_url"))},
            ),
            _check(
                S("P4"),
                object_type="paper",
                object_id=pid,
                display={"fulltext_source": src},
                machine_hint={
                    "pass": src in {"mineru", "grobid", "grobid_fusion", "none", ""}
                    or src != "local_cache",
                    "fulltext_source": src,
                },
            ),
        ]
        paper_objects.append(
            {
                "id": pid,
                "title": p.get("title"),
                "year": p.get("year"),
                "doi": p.get("doi"),
                "source": p.get("source"),
                "fulltext_source": src,
                "abstract_preview": ((p.get("abstract") or "")[:280]),
                "checks": checks,
            }
        )

    gap_objects = []
    for g in gaps:
        gid = str(g.get("id") or "")
        title = str(g.get("title") or "")
        desc = str(g.get("description") or "")
        gtype = str(g.get("gap_type") or "")
        ev_chain = g.get("evidence_chain") or []
        next_s = str(g.get("suggested_next_step") or "")
        fals = str(g.get("falsification_test") or "")
        overclaim = any(
            x in (title + desc).lower()
            for x in ("discover", "首次证明", "paradigm", "confirmed discovery")
        )
        s_ids = set(g.get("supporting_paper_ids") or [])
        c_ids = set(g.get("contradicting_paper_ids") or [])
        evidence_objs = []
        for i, e in enumerate(ev_chain):
            quote = str(e.get("quote_or_basis") or "")
            prov = e.get("provenance") or {}
            cid = prov.get("chunk_id")
            ch = chunks.get(cid) if cid else None
            in_chunk = _quote_in_text(quote, (ch or {}).get("text") or "")
            noise = is_boilerplate_text(quote, prov.get("section"))
            evid_id = f"{gid}#e{i}"
            e_checks = [
                _check(
                    S("E1"),
                    object_type="evidence",
                    object_id=evid_id,
                    display={"quote_preview": quote[:180]},
                    machine_hint={"note": "专家判断是否像论文原句"},
                ),
                _check(
                    S("E2"),
                    object_type="evidence",
                    object_id=evid_id,
                    display={"chunk_id": cid, "paper_id": e.get("paper_id")},
                    machine_hint={"pass": in_chunk, "quote_in_chunk": in_chunk},
                ),
                _check(
                    S("E3"),
                    object_type="evidence",
                    object_id=evid_id,
                    display={
                        "paper_id": e.get("paper_id"),
                        "chunk_id": cid,
                        "pdf_hash": (prov.get("pdf_hash") or "")[:16] + "…",
                    },
                    machine_hint={
                        "pass": bool(e.get("paper_id") and cid and prov.get("pdf_hash")),
                    },
                ),
                _check(
                    S("E4"),
                    object_type="evidence",
                    object_id=evid_id,
                    display={"section": prov.get("section")},
                    machine_hint={"pass": not noise, "boilerplate": noise},
                ),
                _check(
                    S("E5"),
                    object_type="evidence",
                    object_id=evid_id,
                    display={"claim": e.get("claim"), "gap_title": title},
                    machine_hint={"note": "摘录是否支撑 Gap 主张"},
                ),
            ]
            evidence_objs.append(
                {
                    "id": evid_id,
                    "paper_id": e.get("paper_id"),
                    "claim": e.get("claim"),
                    "quote": quote,
                    "location": e.get("location"),
                    "confidence": e.get("confidence"),
                    "provenance": {
                        "chunk_id": cid,
                        "pdf_hash": prov.get("pdf_hash"),
                        "parser": prov.get("parser"),
                        "section": prov.get("section"),
                        "char_start": prov.get("char_start"),
                        "char_end": prov.get("char_end"),
                    },
                    "chunk_preview": ((ch or {}).get("text") or "")[:400],
                    "checks": e_checks,
                }
            )

        g_checks = [
            _check(S("G1"), object_type="gap", object_id=gid, display={"title": title, "description": desc[:240]}),
            _check(
                S("G2"),
                object_type="gap",
                object_id=gid,
                display={"title": title},
                machine_hint={
                    "pass": (not topic_mats)
                    or any(m.lower() in (title + desc + gid).lower() for m in topic_mats)
                    or gid.startswith("gap-missing-link")
                    or gid in {"gap-method-balance"},
                },
            ),
            _check(S("G3"), object_type="gap", object_id=gid, display={"description": desc[:240]}),
            _check(
                S("G4"),
                object_type="gap",
                object_id=gid,
                display={"overlaps_known": g.get("overlaps_known"), "novelty": g.get("novelty")},
                machine_hint={"overlaps_known": g.get("overlaps_known"), "novelty": g.get("novelty")},
            ),
            _check(
                S("T1"),
                object_type="gap",
                object_id=gid,
                display={"type": gtype, "supporting": list(s_ids), "contradicting": list(c_ids)},
                machine_hint={
                    "pass": gtype != "contradiction" or (bool(s_ids) and bool(c_ids) and not (s_ids & c_ids)),
                    "na": gtype != "contradiction",
                },
            ),
            _check(S("T2"), object_type="gap", object_id=gid, display={"type": gtype}),
            _check(
                S("T3"),
                object_type="gap",
                object_id=gid,
                display={"type": gtype, "description": desc[:200]},
                machine_hint={
                    "pass": gtype != "missing_link"
                    or any(k in desc.lower() for k in ("corpus", "screened", "within this")),
                    "na": gtype != "missing_link",
                },
            ),
            _check(S("T4"), object_type="gap", object_id=gid, display={"type": gtype}),
            _check(
                S("A1"),
                object_type="gap",
                object_id=gid,
                display={"next_step": next_s},
                machine_hint={
                    "pass": len(next_s) >= 20 and "more research" not in next_s.lower(),
                },
            ),
            _check(
                S("A2"),
                object_type="gap",
                object_id=gid,
                display={"falsification": fals},
                machine_hint={"pass": len(fals) >= 20},
            ),
            _check(S("A3"), object_type="gap", object_id=gid, display={"next_step": next_s}),
            _check(
                S("N1"),
                object_type="gap",
                object_id=gid,
                display={"title": title},
                machine_hint={"pass": not overclaim, "overclaim_lexicon_hit": overclaim},
            ),
            _check(
                S("N2"),
                object_type="gap",
                object_id=gid,
                display={"novelty": g.get("novelty"), "overlaps_known": g.get("overlaps_known")},
                machine_hint={
                    "warn": bool(g.get("overlaps_known")) and float(g.get("novelty") or 0) > 0.7,
                },
            ),
            _check(S("D1"), object_type="gap", object_id=gid, display={"title": title}),
            _check(S("D2"), object_type="gap", object_id=gid, display={"next_step": next_s}),
            _check(S("D3"), object_type="gap", object_id=gid, display={"paper_count": len(papers)}),
        ]
        gap_objects.append(
            {
                "id": gid,
                "title": title,
                "description": desc,
                "gap_type": gtype,
                "novelty": g.get("novelty"),
                "actionability": g.get("actionability"),
                "review_status": g.get("review_status"),
                "overlaps_known": g.get("overlaps_known"),
                "supporting_paper_ids": list(s_ids),
                "contradicting_paper_ids": list(c_ids),
                "suggested_next_step": next_s,
                "falsification_test": fals,
                "checks": g_checks,
                "evidence": evidence_objs,
            }
        )

    pack = {
        "version": standards_doc.get("version"),
        "run_id": run_id,
        "topic": topic,
        "topic_materials": topic_mats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standards_doc": {
            "title": standards_doc.get("title"),
            "purpose": standards_doc.get("purpose"),
            "categories": standards_doc.get("categories"),
            "standards": standards_doc.get("standards"),
            "verdict_options": standards_doc.get("verdict_options"),
        },
        "summary": {
            "papers": len(papers),
            "gaps": len(gaps),
            "run_checks": len(run_checks),
            "paper_checks": sum(len(p["checks"]) for p in paper_objects),
            "gap_checks": sum(len(g["checks"]) for g in gap_objects),
            "evidence_checks": sum(len(e["checks"]) for g in gap_objects for e in g["evidence"]),
            "total_checks": 0,
        },
        "objects": {
            "run": {"id": run_id, "checks": run_checks},
            "papers": paper_objects,
            "gaps": gap_objects,
        },
        "instructions": {
            "user": [
                "打开「专家核对」页，先完成运行层核对对象。",
                "再按 Gap 逐条：先看标准徽标 → 读主张 → 核证据 quote → 填 pass/fail/unsure。",
                "必须项(must)优先；expert 项留给领域判断。",
                "完成后可下载 JSON 判决，或复制到 experiments/reviews/。",
            ],
            "debug": [
                "除用户端内容外，请核对 provenance、chunk_preview、machine_hint。",
                "对 E2：用 chunk_id 对照 evidence_chunks / 全文面板做反向搜索。",
                "对 X3：打开 audit.json 的 retrieve 条目确认后端。",
            ],
        },
    }
    pack["summary"]["total_checks"] = (
        pack["summary"]["run_checks"]
        + pack["summary"]["paper_checks"]
        + pack["summary"]["gap_checks"]
        + pack["summary"]["evidence_checks"]
    )
    return pack


def write_expert_review_pack(run_dir: Path, run_id: str | None = None) -> Path:
    pack = build_expert_review_pack(run_dir, run_id=run_id)
    out = Path(run_dir) / "expert_review_pack.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
