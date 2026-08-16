# 路线 A · 构效关系清单、证据链与解释文档（0816）

> 对应手册：构效清单 + 证据链 + 解释文档。  
> 数据：`outputs/ablation_route_a/`、`outputs/production_route_a/`、`outputs/production_sciverse/`。

## 1. 搜索算法 ↔ 实现映射（手册：GA / MCTS / BO 等）

本系统采用**遗传式种群搜索（GA-style）**，而非仅用 LLM 生成搜索代码：

| 经典组件 | 本仓库角色 | 实现 |
|----------|------------|------|
| 初始种群 | SEED | Gap / ontology 模板播种；LLM 可 refine 假说文本 |
| 适应度 | SCORE | 启发式 + **LLM 科学合理性打分**（`llm_score`） |
| 选择/剪枝 | PRUNE | 低分淘汰；LLM 软剪枝（`llm_prune_soft`） |
| 交叉/变异 | MUTATE / FOCUS | 规则邻域变异 + LLM 聚焦变异（`llm_focus_mutate`） |
| 外验门 | validate | Materials Project + **OQMD**（`mp_oqmd`） |

与 MCTS/贝叶斯优化的关系：当前主叙事为 **GA 种群迭代**；LLM 负责假设生成与中间评估（对应手册「深度融合」），外验负责可证伪打脸。同 seed=42 消融见 [`ablation_route_a.md`](ablation_route_a.md)。

## 2. 方法（搜索 × LLM）

| 角色 | 规则路径 | LLM 路径 |
|------|----------|----------|
| SEED | `seed_template` | `llm_seed_refine` |
| SCORE | 启发式 | `llm_score` |
| PRUNE / MUTATE | `rule_mutate` | `llm_prune_soft` / `llm_focus_mutate` |
| 外验 | MP + OQMD（公式门后） | 同左 |

## 3. 构效关系清单（读法）

对每个候选记录：`material_motif` / `property_target` / `hypothesis` / `novelty_label`（known vs candidate_new）/ `gap_alignment` / `score` / `external_validation` / `role_trace` / 支撑文献 ID。

**解释原则：**

1. 假说单句、可证伪。  
2. `known`：不作「首次发现」。  
3. `candidate_new`：须外验或 falsification。  
4. 领域：SnSe 热电 κ_L / 空位散射（见 [`science_significance.md`](science_significance.md)）。

## 4. 证据链

1. `production_sciverse*/gaps.json`：`quote_or_basis` + `retrieval_database`（`sciverse` / `scibase`）。  
2. `route_a_external_validation.json`（MP）与 `route_a_external_validation_mp_oqmd.json`（双库）。  
3. `route_a_spr_report.md` 排名表。

## 5. 加分项：材料数据库验证

- Materials Project：真 API + 公式门  
- OQMD：公开 formationenergy API 交叉验证（见 [`route_a_mp_oqmd.md`](route_a_mp_oqmd.md)）  
- NOMAD：鼓励项，复赛披露中保留扩展位（未强制接入）
