# 完整技术报告（复赛稿 · 和昆仑）

> 对应手册「最终：完整技术报告 + 可复现代码/容器」的**可提交草稿**。  
> 依据：`document/AI_for_reserach0816.md`（材料·路线 A）。

## 1. 问题与方向

算法赛 · 方向三：材料文献驱动科学发现智能体；进阶 **路线 A（构效关系）**。  
主题：SnSe 空位工程与晶格热导 κ_L——可证伪、可外验、证据链可审计。

## 2. 系统架构

```text
Query → Sciverse + Sci-Base 检索 → OA/解析全文（GROBID；Sci-Base content_list）
  → 抽取 / Known → Research Gap（quote⊂source + Database 标签）
  → 报告 PDF+LaTeX → Route A（GA 式种群 × LLM）→ MP/OQMD 外验
```

细节见 `system_description.md`、`DEPENDENCIES.md`。

## 3. 基本任务结果（方向内 50%）

| 项 | 落点 |
|----|------|
| 金标跑次 | `outputs/production_sciverse`（LLM-off 证据链） |
| Sci-Base | `outputs/production_sciverse_scibase`（enrich）+ `experiments/scibase/` |
| 报告 | `report.pdf` / `.tex` / `.bib` |
| 系统说明 | `system_description.md` |
| 引用自查 | `citation_audit.md` |

## 4. 路线 A 结果（方向内 50%）

| 分项 | 证据 |
|------|------|
| 方法创新 30% | GA 映射 + LLM-in-the-loop；`ablation_route_a.md` |
| 可信验证 30% | MP pass；`route_a_mp_oqmd.md` 双库 |
| 科学意义 20% | `science_significance.md`；L2 已签字归档 `l2-signed-20260816-production_sciverse_scibase.md`（4/4） |
| 工程复现 20% | `REPRODUCE.md`、CI、Dockerfile、稳定度 demo |

## 5. 合规与开源

公开仓库：https://github.com/new8341/GoAi  

见仓库根 `compliance/`：API/闭源、数据来源、依赖、PRIOR_WORK、开源计划。  
容器：`docker-compose.yml`（GROBID/Qdrant）+ `Dockerfile`（应用镜像）。

## 6. 局限与后续

- 全量 Sci-Base 为 TB 级：使用材料子集缓存，非整库下载。  
- 完整 hybrid 重解析依赖本机 Docker/GROBID（见 `SUPPORT_NEEDED.md`）。  
- 金标准 **coverage=0.667**（`gold_set_v2_hybrid`）：可并列汇报 type_accuracy=1.0。  
- 官方 MCP：`sciverse-mcp-server` 已接入配置/探针；批量跑次仍以 REST audit 为主。  
- 决赛：海报/路演/一页纸见 `one_pager.md`。
