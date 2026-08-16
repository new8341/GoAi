# 系统说明 · 材料文献调研 Agent + 路线 A

> 0816 手册：基本任务须附「系统说明」。队伍：和昆仑。

## 1. 系统目标

构建可复现的材料科学文献调研智能体，并在 Research Gap 上运行构效关系（SPR）搜索（路线 A），经公开材料库交叉验证。

## 2. 模块与数据流

```text
configs/*.yaml
  → LiteratureSurveyAgent
       rewrite → retrieve(Sciverse + Sci-Base / OpenAlex)
       → OA PDF → GROBID（Sci-Base 可直接用 content_list）
       → chunk/index → extract → known → gaps(+evidence) → review
       → report.md + report.tex/bib/pdf + external_versions.json
  → RouteASearcher（SEED/SCORE/PRUNE/MUTATE × LLM + MP validate）
```

| 模块 | 路径 | 职责 |
|------|------|------|
| 配置 | `configs/production_sciverse_scibase.yaml` 等 | topic、seed、backend、门禁阈值 |
| 流水线 | `materials_agent/pipeline.py` | 调研端到端 |
| Sci-Base | `tools/scibase_client.py` + `SciBaseRetriever` | HF `opendatalab/Sci-Base` 材料缓存检索 |
| 证据归因 | `evidence_attribution.py` | Gap/主张标注 `retrieval_database` |
| 报告 | `agents/reporter.py` + `export/latex_report.py` | MD + LaTeX/PDF |
| 路线 A | `routes/route_a.py` | 搜索环 + novelty + 外验 |
| 材料库 | `tools/materials_db.py` | MP/OQMD；非法 motif 拒绝 |
| 验收 | `scripts/verify_production.py` 等 | PASS 契约 |

## 3. 推荐工具落地情况

| 手册推荐 | 本系统 |
|----------|--------|
| Sciverse | `backend: sciverse` / hybrid `sciverse_scibase`；审计禁止静默假后端 |
| MinerU / GROBID | 生产主路径 **GROBID 0.8.0**；Sci-Base 行为 MinerU 深解析产物 |
| Sciverse MCP/Skill | **已接官方** `sciverse-mcp-server`（`mcp.json.example`）；批量金标仍走 REST + `audit.json` |
| Sci-Base (HF) | **已接入**：`opendatalab/Sci-Base` → `data/scibase/materials_cache.jsonl`；见 `scripts/build_scibase_cache.py` |
| Materials Project | Route A 外验（`MP_API_KEY`） |

## 4. 复现入口

见 `submissions/semi_final/REPRODUCE.md` 与仓库 `使用说明.md`「复赛最短复现」。种子默认 `42`。

## 5. 产出物清单（对齐 0816）

| 手册项 | 本仓库落点 |
|--------|------------|
| 调研报告 PDF+LaTeX | `outputs/production_sciverse/report.{pdf,tex}` + `references.bib` |
| Gap + 交叉引用 + 证据链 | `gaps.json` / `report.md` |
| 系统说明 | 本文档 |
| 构效清单 + 证据 + 解释 | `route_a_spr_*` + `route_a_explanation.md` |
