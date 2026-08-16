# 初赛方案说明  
## GOAI 赛道三 · 算法赛 · 方向三：材料科学文献驱动的科学发现智能体

> 定稿供提交 · 2026-08-12  
> 对应手册：算法赛初赛「方案说明文档、技术路线概述（可附初步实验）」  
> 代码仓库相对路径：`tracks/algorithm/materials_agent/`

---

## 1. 所选方向与科学问题理解

本队选择**算法赛题 · 方向三**：基于大规模材料科学文献，构建能自主检索、阅读、推理并产出**可证伪**科学发现线索的智能体。

核心科学问题不是「用 LLM 写综述」，而是：

1. **如何把非结构化文献沉淀为可审计的结构化知识**（材料–性质–方法–局限，带原文证据）；  
2. **如何系统识别 Research Gap**（缺失连接、矛盾结论、未充分探索、方法缺口），并强制「下一步实验 + 可证伪条件」；  
3. **如何在 Gap 上用搜索算法与 LLM 深度融合**提出可验证的构效假说（进阶**路线 A**），并用外部材料库交叉验证。

切口主题（当前竞赛主跑）：**SnSe 空位工程与晶格热导（κ_L）**——问题边界清晰，便于证据链验收与科学抽检。

---

## 2. 技术方案（总览）

### 2.1 基本任务（~50%）：文献调研 Agent

```text
Query 改写 → 多源检索（**Sciverse + Hugging Face Sci-Base** / OpenAlex / S2）
  → 合法 OA PDF 下载（Unpaywall）→ GROBID 解析（生产默认；Sci-Base 行已含 MinerU 结构化 content_list）
  → 切块索引 → 知识抽取 → Known 密集区
  → Gap 发现 + 全文证据回源（quote⊂source + provenance）
  → Gap 评审 → 主题贴合监控 → 结构化报告 + 审计
```

**生产纪律：**

- 仅合法开放获取全文；不绕过付费墙；不提交受限 PDF。  
- **Sci-Base 必用：** 配置 `production_sciverse_scibase.yaml`（`backend: sciverse_scibase`）；本地材料子集缓存 `data/scibase/materials_cache.jsonl` 由 HF `opendatalab/Sci-Base` 流式构建（全库 TB 级，不做整库下载）。证据链 `retrieval_database` 标明 `sciverse` / `scibase`。  
- Gap 证据禁止用摘要/许可协议页脚冒充正文。  
- 工程验收 `verify_production`、科学门禁 `science_review_gate`、客观专家包 `objective_review` **分文件、互不冒充**。

### 2.2 进阶路线（选定 A，~50%）：构效关系发现

- **SEED**：由 Gap / 材料–性质词表播种假说种群；  
- **SCORE / PRUNE**：LLM 参与合理性打分与软剪枝（无额度时规则路径可降级并写 audit）；  
- **FOCUS / MUTATE**：邻近构效空间变异；  
- **外验**：Materials Project 对 Top-K 候选做稳定性 / e_hull 类交叉验证（`allow_offline_fallback: false`）。

### 2.3 方法对标（学纪律，不复制算力）

| 公开范式 | 本仓库落点 |
|----------|------------|
| ScienceAgentBench / CASP 独立评估 | 分步产物 + 三门禁 |
| GNoME 生成–过滤–验证 | Route A + MP 外验 |
| Claude Science / Kosmos 可追溯 | EvidenceSpan + audit + 双 UI |
| 赛题推荐 Sciverse / Sci-Base / AI-Ready 全文 | `SciverseRetriever` + `SciBaseRetriever`（HF）+ GROBID；诚实禁止静默假后端 |

---

## 3. 系统与交付形态

| 能力 | 说明 |
|------|------|
| CLI | `run_survey` / `verify_production` / `science_review_gate` / `run_route_a` |
| 黑盒 UI | `http://127.0.0.1:8765/?run=production_sciverse` |
| 白盒 UI | `/debug/?run=...`（audit / provenance） |
| 配置分轨 | `demo_local` ≠ `production` ≠ `production_sciverse` ≠ **`production_sciverse_scibase`** ≠ `production_route_a` |
| 复现剧本 | `scripts/reproduce_production_sciverse.ps1` |

---

## 4. 可行性（摘要）

截至 2026-08-12（详见同目录 `03_可行性与证据摘要.md`）：

- 离线 smoke：`demo_local` 端到端可跑；  
- 生产证据链：`production_sciverse` 上 **verify ∩ science ∩ objective(must) = PASS**（Sciverse 检索，LLM off 证据金标）；  
- Route A：同一 SnSe 主题，MP 外验 pass，且已出现 `llm_seed_refine` / `llm_score` / `llm_focus_mutate` 角色轨迹；  
- 双 Web 界面与专家核对标准已落地。

---

## 5. 科学意义

推动材料领域「文献 → 可证伪假说 → 计算/实验验证」的知识生产自动化，沉淀**可复用的证据链 Agent 范式**：评委可独立核对 quote 是否在全文、Gap 是否贴题、外验是否诚实降级——而不是一次性聊天式综述。

---

## 6. 开源与合规

见同目录 [`04_开源计划与边界.md`](04_开源计划与边界.md)。计划开源代码与流水线文档；**不入库** API 密钥与未授权全文。

---

## 7. 复赛预期（不作为初赛完成承诺）

1. 稳定 LLM-in-the-loop 消融对照（额度允许时）；  
2. Gap 金标准 coverage 扩标与真人 L2 抽检归档；  
3. 完整 `compliance/` 披露与容器化一键复现说明。
