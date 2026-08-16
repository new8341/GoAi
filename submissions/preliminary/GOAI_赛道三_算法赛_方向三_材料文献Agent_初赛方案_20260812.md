# GOAI 赛道三 · 算法赛 · 方向三 · 初赛合订文档

> 文件名建议上传为：`GOAI_赛道三_算法赛_方向三_材料文献Agent_初赛方案_20260812.md`  
> 生成日期：2026-08-12 · 门户：https://goaihz.com

---

## 目录

1. 方案说明  
2. 技术路线概述  
3. 可行性与证据摘要  
4. 开源计划与边界  

（以下正文与 `01`–`04` 单文件一致，便于单文件上传。）

---

# 一、方案说明

本队选择**算法赛题 · 方向三**：基于大规模材料科学文献，构建能自主检索、阅读、推理并产出**可证伪**科学发现线索的智能体。

核心科学问题：

1. 非结构化文献 → 可审计结构化知识（带原文证据）；  
2. 系统识别 Research Gap，并强制下一步实验 + 可证伪条件；  
3. 在 Gap 上用**搜索 × LLM**提出构效假说（路线 A），并用 Materials Project 外验。

切口主题：**SnSe 空位工程与晶格热导**。

**基本任务流水线：** Query → 检索（OpenAlex/Sciverse）→ 合法 OA PDF → GROBID → 抽取 → Known → Gap（全文证据回源）→ 评审 → 报告 + 审计。  

**路线 A：** SEED → SCORE/PRUNE → MUTATE → MP 外验。  

**交付：** CLI + 黑盒/白盒双 UI + 三门禁（verify / science / objective 分文件）。  

**可行性（摘要）：** `production_sciverse` 上 verify∩science∩objective PASS（LLM-off 证据金标）；Route A MP pass×5 且已点亮 LLM 角色轨迹。详见第三节。  

**开源：** 计划开源代码与文档；不入库密钥与受限 PDF。详见第四节。

---

# 二、技术路线概述

详见同目录 `02_技术路线概述.md`（架构图、逐步模块表、门禁表、配置分轨、最小复现命令）。提交单文件时评委亦可打开该文件；合订场景下技术要点为：

- 生产禁止静默假后端（`allow_backend_fallback: false`）；  
- Gap 证据强制 quote⊂source + provenance，禁 boilerplate；  
- `objective_review` 不得覆盖 `production_verification.json`；  
- Sciverse 金标叙事 = 证据链（LLM off），勿与 LLM 发现混说。

---

# 三、可行性与证据摘要

| 层 | 状态 |
|----|------|
| demo_local smoke | 可跑 |
| production_sciverse | verify / science / objective = **PASS**；papers=5 fulltext=3；topic_hit=1.0；boilerplate=0；backend=sciverse |
| production_route_a | OK；MP pass×5；含 llm_seed_refine / llm_score / llm_focus_mutate |

勿夸大：`production_sciverse_llm` 曾遇 RateLimit，不能当 LLM 发现材料。

复现：`scripts/reproduce_production_sciverse.ps1` + `run_route_a.py`；门户本地 UI `/?run=production_sciverse`。

---

# 四、开源计划与边界

- 开源：流水线代码、配置、文档、门禁与双 UI；拟 Apache-2.0。  
- 不开源：`.env`、受限 PDF、Qdrant/模型大缓存。  
- 数据：OpenAlex / Unpaywall OA / Sciverse / MP — 均按各平台条款；提交包不含原始 PDF 与密钥。

---

# 五、上传检查

- [ ] 已登录 https://goaihz.com  
- [ ] 本合订或 01–04 已上传  
- [ ] 未夹带密钥/PDF  
- [ ] 提交成功页截图存档  
