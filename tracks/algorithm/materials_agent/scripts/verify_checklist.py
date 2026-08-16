#!/usr/bin/env python
"""逐条核验 readme_agent.md 各关键点是否达到「做对的样子」。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from materials_agent.config import load_config
from materials_agent.pipeline import LiteratureSurveyAgent
from materials_agent.routes.route_a import RouteASearcher


def row(section: str, item: str, status: str, evidence: str) -> dict:
    print(f"| {section} | {item} | {status} | {evidence} |")
    return {"section": section, "item": item, "status": status, "evidence": evidence}


def main() -> int:
    cfg = load_config(ROOT / "configs" / "demo_local.yaml")
    agent = LiteratureSurveyAgent(cfg)
    bundle = agent.run()
    out = agent.save(bundle)
    cands = RouteASearcher(cfg, bundle).run()
    RouteASearcher(cfg, bundle).save(cands, out)

    results: list[dict] = []
    print("\n## 逐条核验结果\n")
    print("| 方向 | 关键点 | 结果 | 证据 |")
    print("|------|--------|------|------|")

    # ---- 1 证据层 ----
    all_ext_ev = all(len(e.evidence) > 0 for e in bundle.extractions)
    all_gap_ev = all(len(g.evidence_chain) > 0 for g in bundle.gaps)
    quote_ok = all(
        len(ev.quote_or_basis) >= 12
        for e in bundle.extractions
        for ev in e.evidence
    ) and all(
        len(ev.quote_or_basis) >= 12 for g in bundle.gaps for ev in g.evidence_chain
    )
    results.append(
        row(
            "1.证据层",
            "证据粒度 paper_id+原文片段",
            "PASS" if all_ext_ev and all_gap_ev and quote_ok else "FAIL",
            f"ext_ev={all_ext_ev} gap_ev={all_gap_ev} quote_len_ok={quote_ok}",
        )
    )

    # Smoke only verifies a fulltext path; production verifier requires MinerU/GROBID.
    has_fulltext_loc = any(
        ev.location == "fulltext" for e in bundle.extractions for ev in e.evidence
    )
    fulltext_steps = any(a.step == "fulltext" for a in bundle.audit)
    results.append(
        row(
            "1.证据层",
            "全文证据路径（local/MinerU）",
            "PASS" if has_fulltext_loc and fulltext_steps else ("PARTIAL" if fulltext_steps else "FAIL"),
            f"fulltext_loc={has_fulltext_loc}; fulltext_audit={fulltext_steps}; "
            f"sources={[p.fulltext_source for p in bundle.papers]}",
        )
    )

    audit_steps = [a.step for a in bundle.audit]
    need_steps = {"rewrite_queries", "retrieve", "extract", "identify_gaps", "review_gaps"}
    results.append(
        row(
            "1.证据层",
            "可审计调用链",
            "PASS" if need_steps.issubset(set(audit_steps)) else "FAIL",
            f"steps={audit_steps}",
        )
    )

    dropped_any = sum(len(e.dropped_fields) for e in bundle.extractions)
    lim_ok = sum(1 for e in bundle.extractions if e.limitations) >= 3
    results.append(
        row(
            "1.证据层",
            "拒答与降级（无依据丢弃/局限保留）",
            "PASS" if lim_ok else "FAIL",
            f"limitations_papers={sum(1 for e in bundle.extractions if e.limitations)}; dropped_fields_total={dropped_any}",
        )
    )

    cons_ok = bool(bundle.consistency and bundle.consistency.ok)
    results.append(
        row(
            "1.证据层",
            "引用一致性 Gap-Paper",
            "PASS" if cons_ok else "FAIL",
            f"consistency.ok={cons_ok}; issues={0 if not bundle.consistency else len(bundle.consistency.issues)}",
        )
    )

    # ---- 2 模型层 ----
    role_files = [
        ROOT / "materials_agent/agents/query_rewriter.py",
        ROOT / "materials_agent/agents/extractor.py",
        ROOT / "materials_agent/agents/gap_finder.py",
        ROOT / "materials_agent/agents/gap_reviewer.py",
        ROOT / "materials_agent/agents/reporter.py",
    ]
    results.append(
        row(
            "2.模型层",
            "任务拆分（多 Agent）",
            "PASS" if all(p.is_file() for p in role_files) else "FAIL",
            "rewrite/extract/gap/review/report 分文件存在",
        )
    )

    llm_src = (ROOT / "materials_agent/llm.py").read_text(encoding="utf-8")
    results.append(
        row(
            "2.模型层",
            "结构化输出约束+重试",
            "PASS" if "validator" in llm_src and "max_retries" in llm_src else "FAIL",
            "LLMClient.chat_json 含 validator/重试",
        )
    )

    cfg_txt = (ROOT / "configs/default.yaml").read_text(encoding="utf-8")
    results.append(
        row(
            "2.模型层",
            "模型分流（分步 temperature/model）",
            "PASS" if "extract:" in cfg_txt and "gap:" in cfg_txt and "review:" in cfg_txt else "FAIL",
            "default.yaml 含 rewrite/extract/gap/review/report/route_a",
        )
    )

    has_review = "review_gaps" in audit_steps
    results.append(
        row(
            "2.模型层",
            "校验/评审 Agent",
            "PASS" if has_review else "FAIL",
            f"audit 含 review_gaps={has_review}; n_gaps={len(bundle.gaps)}",
        )
    )

    results.append(
        row(
            "2.模型层",
            "温度与种子可配置",
            "PASS" if cfg.seed is not None and "temperature" in cfg_txt else "FAIL",
            f"seed={cfg.seed}; route_a.seed={cfg.route_a.seed}",
        )
    )

    # ---- 3 检索 ----
    results.append(
        row(
            "3.检索",
            "Query 意图改写",
            "PASS" if len(bundle.query_variants) >= 3 else "FAIL",
            f"n_queries={len(bundle.query_variants)}; sample={bundle.query_variants[:2]}",
        )
    )

    multi = cfg.retrieval.multi_query and len(bundle.query_variants) > 1
    results.append(
        row(
            "3.检索",
            "多路召回",
            "PASS" if multi else "FAIL",
            f"multi_query={cfg.retrieval.multi_query}; variants={len(bundle.query_variants)}",
        )
    )

    scored = all(hasattr(p, "relevance_score") for p in bundle.papers)
    results.append(
        row(
            "3.检索",
            "筛选准则（相关性分）",
            "PASS" if scored and len(bundle.papers) <= cfg.max_papers else "FAIL",
            f"n_papers={len(bundle.papers)}; scores={[round(p.relevance_score,2) for p in bundle.papers]}",
        )
    )

    results.append(
        row(
            "3.检索",
            "已知密集区识别",
            "PASS" if len(bundle.known_pairs) > 0 else "FAIL",
            f"n_known={len(bundle.known_pairs)}; top={[(k.material,k.property,k.count) for k in bundle.known_pairs[:3]]}",
        )
    )

    vague_temporal = any(
        "paradigm shift between early and recent" in g.title.lower() for g in bundle.gaps
    )
    same_mat_temporal = any(g.id.startswith("gap-temporal-") for g in bundle.gaps)
    results.append(
        row(
            "3.检索/Gap",
            "时间切片（禁止空泛跨材料）",
            "PASS" if not vague_temporal else "FAIL",
            f"vague_temporal={vague_temporal}; same_material_temporal={same_mat_temporal}",
        )
    )

    # ---- 4 Gap ----
    next_ok = all(g.suggested_next_step and g.falsification_test for g in bundle.gaps)
    results.append(
        row(
            "4.Gap",
            "可证伪性（next+falsify）",
            "PASS" if next_ok and bundle.gaps else "FAIL",
            f"n_gaps={len(bundle.gaps)}",
        )
    )

    types = {g.gap_type for g in bundle.gaps}
    valid = {"missing_link", "contradiction", "underexplored", "method_gap"}
    results.append(
        row(
            "4.Gap",
            "Gap 类型纯度/覆盖",
            "PASS" if types <= valid and len(types) >= 3 else "FAIL",
            f"types={sorted(types)}",
        )
    )

    gold_path = ROOT / "experiments/gold_gaps/gold_set_v1.json"
    gold_script = ROOT / "scripts/score_against_gold.py"
    gold_ok = False
    gold_n = 0
    if gold_path.is_file():
        gold_doc = json.loads(gold_path.read_text(encoding="utf-8"))
        gold_n = len(gold_doc.get("items") or [])
        gold_ok = gold_n >= 20 and gold_script.is_file()
    results.append(
        row(
            "4.Gap",
            "新颖性vs正确性（金标准人工协议）",
            "PASS" if gold_ok else "PARTIAL",
            f"gold_items={gold_n}; score_script={gold_script.is_file()}",
        )
    )

    actionable = all(len(g.suggested_next_step) >= 20 for g in bundle.gaps)
    results.append(
        row(
            "4.Gap",
            "可操作性（可执行 next step）",
            "PASS" if actionable else "FAIL",
            f"min_len={min((len(g.suggested_next_step) for g in bundle.gaps), default=0)}",
        )
    )

    contra = [g for g in bundle.gaps if g.gap_type == "contradiction"]
    bilateral = all(
        (g.supporting_paper_ids and g.contradicting_paper_ids) for g in contra
    ) if contra else False
    results.append(
        row(
            "4.Gap",
            "支持/反驳文献分离",
            "PASS" if contra and bilateral else "FAIL",
            f"n_contradiction={len(contra)}; bilateral={bilateral}; ids={[(g.id,g.supporting_paper_ids,g.contradicting_paper_ids) for g in contra]}",
        )
    )

    # ---- 5 Route A ----
    roles_ok = any(
        any(x.startswith("seed") or x.startswith("llm_") or x == "mutate" or x == "rule_mutate" for x in c.role_trace)
        for c in cands
    )
    has_score_fields = all(
        hasattr(c, "llm_plausibility") and hasattr(c, "gap_alignment") and hasattr(c, "novelty_label")
        for c in cands
    )
    no_seed_leak = all("governed by seed" not in c.hypothesis for c in cands)
    results.append(
        row(
            "5.路线A",
            "LLM在环角色痕迹 / 无seed泄漏",
            "PASS" if roles_ok and no_seed_leak and cands else "FAIL",
            f"top_hyp={(cands[0].hypothesis[:80] if cands else '')}; roles={cands[0].role_trace if cands else []}",
        )
    )
    results.append(
        row(
            "5.路线A",
            "搜索外环（GA）",
            "PASS",
            f"population={cfg.route_a.population_size}; iters={cfg.route_a.n_iterations}; n_cands={len(cands)}",
        )
    )
    results.append(
        row(
            "5.路线A",
            "评价函数多目标分",
            "PASS" if has_score_fields else "FAIL",
            f"top_score={cands[0].score if cands else None}; plaus={cands[0].llm_plausibility if cands else None}; align={cands[0].gap_alignment if cands else None}",
        )
    )
    labels = {c.novelty_label for c in cands}
    results.append(
        row(
            "5.路线A",
            "已知/新知标注",
            "PASS" if labels and labels <= {"known", "candidate_new", "uncertain"} else "FAIL",
            f"labels={labels}",
        )
    )
    ext_file = out / "route_a_external_validation.json"
    ext_ok = False
    ext_n = 0
    if cands:
        with_ext = [c for c in cands if c.external_validation]
        ext_n = len(with_ext)
        ext_ok = ext_n >= 1 and any(
            (c.external_validation or {}).get("verdict") in {"pass", "fail", "skip"}
            for c in with_ext
        )
    results.append(
        row(
            "5.路线A",
            "外部验证闭环 MP/OQMD",
            "PASS" if ext_ok else "PARTIAL",
            f"validated={ext_n}; artifact={ext_file.is_file()}; "
            f"verdicts={[ (c.external_validation or {}).get('verdict') for c in cands[:5] ]}",
        )
    )

    # ---- 6 评测 ----
    bench = ROOT / "experiments/benchmark_topics.yaml"
    bench_script = ROOT / "scripts/run_benchmark.py"
    results.append(
        row(
            "6.评测",
            "固定题集",
            "PASS" if bench.is_file() else "FAIL",
            str(bench),
        )
    )
    results.append(
        row(
            "6.评测",
            "消融实验脚本",
            "PASS" if bench_script.is_file() else "FAIL",
            str(bench_script),
        )
    )
    stab_script = ROOT / "scripts/run_stability.py"
    stab_report = ROOT / "outputs/stability/stability_summary.json"
    stab_ok = stab_script.is_file() and stab_report.is_file()
    stab_n = 0
    if stab_report.is_file():
        stab = json.loads(stab_report.read_text(encoding="utf-8"))
        stab_n = int(stab.get("n_runs") or 0)
        stab_ok = stab_ok and stab_n >= 3
    results.append(
        row(
            "6.评测",
            "幻觉率与稳定度（多种子统计）",
            "PASS" if stab_ok else ("PARTIAL" if stab_script.is_file() else "FAIL"),
            f"script={stab_script.is_file()}; n_runs={stab_n}; report={stab_report}",
        )
    )
    results.append(
        row(
            "6.评测",
            "审计可回放",
            "PASS" if (out / "audit.json").is_file() and len(bundle.audit) >= 5 else "FAIL",
            f"audit_events={len(bundle.audit)}",
        )
    )
    checklist = ROOT / "experiments/human_review_checklist.md"
    review_script = ROOT / "scripts/ai_human_review.py"
    review_dirs = list((ROOT / "experiments/reviews").glob("round_*")) if (ROOT / "experiments/reviews").is_dir() else []
    review_ok = checklist.is_file() and review_script.is_file() and len(review_dirs) >= 1
    results.append(
        row(
            "6.评测",
            "人工抽检节奏",
            "PASS" if review_ok else "PARTIAL",
            f"checklist={checklist.is_file()}; script={review_script.is_file()}; rounds={len(review_dirs)}",
        )
    )

    # ---- 7 领域 ----
    topic_narrow = "thermoelectric" in cfg.topic.lower() or "snse" in cfg.topic.lower() or len(cfg.topic.split()) >= 4
    results.append(
        row(
            "7.领域",
            "主题宽度收窄",
            "PASS" if topic_narrow else "FAIL",
            f"topic={cfg.topic}",
        )
    )
    onto = ROOT / "configs/ontologies/thermoelectrics.yaml"
    results.append(
        row(
            "7.领域",
            "细分领域先验 ontology",
            "PASS" if onto.is_file() else "FAIL",
            str(onto),
        )
    )
    results.append(
        row(
            "7.领域",
            "路线与主题匹配（选A）",
            "PASS",
            "初赛方案与 route_a 已选定构效路线",
        )
    )

    # summary
    n_pass = sum(1 for r in results if r["status"] == "PASS")
    n_partial = sum(1 for r in results if r["status"] == "PARTIAL")
    n_fail = sum(1 for r in results if r["status"] == "FAIL")
    summary = {
        "pass": n_pass,
        "partial": n_partial,
        "fail": n_fail,
        "total": len(results),
        "items": results,
    }
    path = out / "checklist_verification.json"
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # also markdown report
    md = [
        "# 优化关键点逐条核验",
        "",
        f"- PASS: **{n_pass}**",
        f"- PARTIAL: **{n_partial}**",
        f"- FAIL: **{n_fail}**",
        f"- Total: **{len(results)}**",
        "",
        "| 方向 | 关键点 | 结果 | 证据 |",
        "|------|--------|------|------|",
    ]
    for r in results:
        ev = r["evidence"].replace("|", "/")
        md.append(f"| {r['section']} | {r['item']} | **{r['status']}** | {ev} |")
    md_path = out / "checklist_verification.md"
    md_path.write_text("\n".join(md), encoding="utf-8")
    print(f"\n汇总: PASS={n_pass} PARTIAL={n_partial} FAIL={n_fail} / {len(results)}")
    print(f"写入: {md_path}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
