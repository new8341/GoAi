# 材料文献 Agent 指南（readme_agent）

> **项目定位**：GOAI 赛道三 · 算法赛 · 方向三「材料科学文献驱动的科学发现智能体」  
> **仓库路径**：`tracks/algorithm/materials_agent/`  
> **官方手册**：仓库 `document/AI_for_reserach.pdf` · 官网 [goaihz.com](https://goaihz.com)

---

## 文档地图（先读这里）

| 章 | 内容 | 何时读 |
|----|------|--------|
| **一** | 公开赛讯与组织方口径（GOAI） | 对齐评委话语、写初赛方案 |
| **二** | 方法论归纳（赛题 + 前沿范式） | 定技术路线、避免「只会聊天」 |
| **三** | 世界级大赛与顶尖团队关键信息 | 对标国际标准、写方法出处 |
| **四** | 本项目路径（阶段 × 产出 × 命令） | 日常执行与排期 |
| **五** | 产出质量关键杠杆 | 改代码前先看改哪一层 |
| **六** | 优化尝试 · 检验结论 · 未达标项 | 知道现在站在哪 |
| **6.6** | 生产重跑意义与高分路径 | 环境打通后怎么冲分、别白跑 |
| **6.7** | 完成度快照（2026-08-02） | 生产 PASS 后还差什么 |
| **七** | 人工审核（关键点 / 知识 / 提质） | 抽检与金标准 |
| **八** | 名词解释（摘要） | 查术语 |
| **九** | 命令与文件索引 | 跑通与提交 |
| **附录 A** | 术语全表 | 检索中英文 |

---

# 一、公开赛讯归纳（组织方口径）

> 来源：GOAI 官网与启动宣传（如 InfoQ / 动点科技等对组委会通稿的转载）、赛道手册 PDF。赛程奖项以官网最终通知为准。

## 1.1 大赛共同标准（四大赛道通用）

公开表述反复强调同一套价值：

| 关键词 | 组织方含义 | 对本项目的直接要求 |
|--------|------------|-------------------|
| 可运行 | 不是概念 PPT | 有 CLI/流水线，能产出报告 |
| 可复现 | 别人能按说明重跑 | README、配置、种子、依赖披露 |
| 可验证 | 有评测/证据/运行痕迹 | `audit.json`、证据链、一致性检查 |
| 开放协作 | 开源与可复用 | 复赛可访问仓库 + 开源边界说明 |
| 真实问题 | 嵌入真实工作流，而非纯演示 | 窄而真的材料科学问题 + 可证伪 Gap |

口号语境：**Open. Share. Build.** · 「引领 AI 走进真实世界」——从「会回答」到「会执行/会发现」。

## 1.2 赛道三：前沿探索（AI for Research）

| 项 | 公开信息摘要 |
|----|----------------|
| 牵头/定位 | 聚焦 AI×科学；手册牵头单位含 Datawhale；鼓励「科学直觉 → 可计算问题」 |
| 两条路径 | **算法赛**（给定评测）与 **开放探索**（自建环境）独立评审、独立排名 |
| 算法三方向 | ① 虚拟细胞 ② 小分子–蛋白结合轨迹 ③ **材料文献驱动科学发现 Agent（本项目）** |
| 找什么样的人 | 不只是「会用 AI 跑实验」，而是能定义可检查信号、可延续环境/管线的人 |
| 初赛截止（宣传口径） | 赛道三约 **8.16**；决赛周约 **9.22–9.23 杭州**（以官网为准） |
| 组队 | 公开口径常见「不超过 3 人」（以手册/官网为准） |

## 1.3 材料方向公开要求（手册口径）

| 阶段 | 必做 |
|------|------|
| 结构 | **基本任务 50%**（文献调研 Agent）+ **进阶路线 50%**（A 构效 / B 模拟 / C 合成，本项目选 A） |
| 基本任务 | 检索筛选 → 知识抽取 → Research Gap → 结构化报告（交叉引用 + 证据链） |
| 推荐工具 | Sciverse（语义检索/证据片段）、MinerU（PDF 结构化）、Sci-Base；鼓励 MCP/Skill 接入形成审计链 |
| 路线 A 考点 | 搜索算法与 LLM **深度融合**（播种/中间评判/剪枝），非仅让 LLM 写搜索代码 |
| 加分 | Materials Project / OQMD / NOMAD 等交叉验证；实验闭环 |
| 算法赛统一评审 | 技术性能 45% · 科学意义 30% · 方法创新 20% · 开源贡献 5%（方向内分先归一化再跨向比） |

## 1.4 相邻赛道可借鉴的「工程话术」

公开对 **赛道一 Agent Infra** 的要求，对本赛道材料 Agent 同样适用：

- 多职能 Agent / Skill 化  
- 工具调用 + **结果验证** + **执行证据沉淀** + 安全/审计  
- 运行日志、Trace、指标作为「是否可信可复现」的证据  

→ 本仓库用 `audit.json`、一致性检查、AI 双人抽检对齐这套话语。

---

# 二、方法论归纳（赛题要求 × 公开前沿）

## 2.1 一句话总纲

**文献 Agent 的上限不在「更会写综述」，而在：AI-Ready 证据 → 可证伪缺口 → 可搜索假说 → 可复查审计。**

## 2.2 组织方与工具链隐含的方法路径

| 步骤 | 公开工具/口径 | 方法要点 |
|------|----------------|----------|
| 1. 文档 AI-Ready | MinerU、Sci-Base | PDF/图表/公式 → 结构化 Markdown/JSON，而非只 loader 全文糊进上下文 |
| 2. 可追溯检索 | Sciverse `meta-search` / `agentic-search` / `content` | 语义命中片段后，用 doc_id/offset 回读原文；回答必须带引用 |
| 3. 结构化科学对象 | 手册：成分/结构/工艺/性能 | 抽取要进字段，不能停在散文 |
| 4. Research Gap | 手册：准确率、新颖性、可操作性 | Gap 要可证伪、有下一步，区分 Known vs 候选新知 |
| 5. 进阶发现 | 路线 A：搜索×LLM | LLM 进搜索环（SEED/SCORE/PRUNE），外环 GA/MCTS/BO |
| 6. 验证闭环 | MP/OQMD/NOMAD | 假说必须可被数据库或实验打脸 |
| 7. 提交物 | 报告+系统说明+代码 | 复赛起可运行、可复现、依赖披露 |

## 2.3 前沿公开范式（可写进方案的「方法出处」）

| 范式 | 代表公开工作 | 可迁移到本项目的点 |
|------|--------------|-------------------|
| 任务级严评，勿夸端到端 | ScienceAgentBench（ICLR’25 等） | 先把「检索/抽取/Gap/验证」单任务做硬，再谈自动发现；用可执行指标而非观感 |
| 长程科研需世界模型/共享状态 | FutureHouse / Kosmos 等 AI Scientist | 用结构化状态（Known 表、Gap 库、audit）跨步骤共享，避免上下文漂移 |
| 环境工程重于堆工作流 | EurekAgent 等「environment engineering」论述 | 权限、产物、预算、人机回路；本仓库对应配置、输出契约、抽检制度 |
| Skill/契约拆分 | AlphaAgent 类材料文献分析 | 检索意图改写与报告生成解耦；证据对齐与可信边界 |
| 引用即一等公民 | Kosmos「结论可追溯到文献或代码」 | 每条主张挂 EvidenceSpan；无证据不入库 |

## 2.4 反模式（公开口径与手册共同反对）

| 反模式 | 为何减分 |
|--------|----------|
| 宏大标题 + LLM 聊天式综述 | 不可复查、不可证伪 |
| 只有最终分数/漂亮截图 | 缺运行证据与参照 |
| 事后定义成功标准 | 违反「发现信号预先定义」精神 |
| LLM 只写搜索代码、不进搜索环 | 路线 A 明确考察融合深度 |
| 把语料内 Known 当「全球首次」 | 新颖性不诚实 |

---

# 三、世界级大赛与顶尖团队关键信息（对标完善）

> 下列信息来自各组织/团队**公开发布**的竞赛说明、博客、论文与产品页。用于对标「什么叫严肃的科学 AI」，不是要求本队复制其算力或硬件。  
> **迁移原则**：学其**评价纪律与闭环结构**，落到本仓库可执行的证据链 / 评审 / 验证。

## 3.1 世界级赛事 / 评测实验：学什么

| 赛事或评测 | 组织方 | 关键公开信息 | 对本材料 Agent 的可迁移点 |
|------------|--------|--------------|---------------------------|
| **CASP**（蛋白结构预测社区实验） | CASP 组委会；DeepMind AlphaFold 在 CASP14 等届次取得突破 | **盲测**：预测时不见实验结构；独立评估者对照实验；推动领域真实进步而非刷公开榜 | ① 测试信息隔离（防泄漏）② 以独立协议评判，而非自说自话 ③ 「已解决」后转向更难切片（如 CASP17 聚焦免疫复合物、配体–蛋白等）→ 主题切在**仍难、可证伪**的 Gap |
| **ScienceAgentBench** | 学术社区（ICLR 等） | 从同行评审论文抽取真实工作流任务；专家多轮校验；统一可执行产出；强调**先评估子任务再谈端到端** | ① 流水线拆成可评测单元 ② 自动断言 + 人工金标准，勿只报观感 |
| **MLE-bench** | OpenAI 等公开基准 | 真实 Kaggle 工程题评 Agent；多种子、均值±误差；提供 grading 脚本 | ① 产出对齐可自动打分格式 ② 高方差必须多种子 ③ 人机基线可对比 |
| **Kaggle 类数据赛** | Kaggle / 主办方 | 固定提交格式、私有测试集、排行榜 | 复赛：模板固定；种子与复现说明写清 |
| **MinerU / 数据智能相关挑战** | OpenDataLab 等 | **AI-Ready 语料**、复杂文献解析、Agent 评测 | 全文解析质量是上限 → MinerU 优先 |
| **GOAI 赛道三** | GOAI 组委会 / Datawhale 等 | 可运行·可复现·可验证；材料方向证据链+路线 A | 本仓库主对齐对象（见 §一） |

### CASP 启示（浓缩）

- **盲评与实验锚定**：好方法必须在「未见真值」时仍成立。  
- **社区实验驱动领域**：公开协议 > 封闭刷分。  
- **突破后换更难题**：写作方案时可对标「不重复已饱和任务，攻坚文献→可证伪 Gap→可验证假说」。

## 3.2 顶尖科技团队：学什么

| 团队 / 产品 | 公开关键点 | 对本项目的映射 |
|-------------|-----------|----------------|
| **Google DeepMind · AlphaFold** | 在 CASP 盲测中用可量化指标证明突破 | 指标先于故事；Gap/假说必须可打分或可否证 |
| **Google DeepMind · GNoME** | 候选生成 → GNN 过滤 → **DFT 验证** → 回灌训练（主动学习飞轮）；对接 MP / OQMD | 路线 A：**假说 → MP/OQMD 过滤 → 留下可验证者** |
| **Google DeepMind · AlphaEvolve / AI co-scientist** | LLM 引导进化；自动评估器反馈；多 Agent 协作假设 | 与「LLM×搜索融合」同构：SEED/SCORE/PRUNE + 显式评价函数 |
| **Anthropic · Claude Science** | 协调 Agent + 领域 Skill；**独立 Reviewer Agent**；产出带 provenance | `gap_reviewer`、audit、双人抽检；复赛补 provenance 打包 |
| **FutureHouse / Edison · Kosmos** | 文献↔分析 Agent 共享**结构化世界模型**；结论必须引用文献或代码 | Known + Gap + audit = 轻量世界模型 |
| **Lila Sciences · AI Science Factory** | 假说→实验→学习的完整闭环；实验作可验证 reward | 周期内难上机器人实验室，可用 **DB 验证 / 实验协议否证** 模拟 |
| **OpenAI · MLE-bench** | 真实工程任务、自动打分、多种子 | 质量脚本 / 消融 / 稳定度的方法依据 |
| **上海 AI 实验室生态 · Sciverse / MinerU** | 科学数据 AI-Ready；语义检索 + 原文回读 | 复赛工具链主升级路径 |

## 3.3 跨来源共识 → 本仓库落点

| # | 国际共识 | 本仓库落点 | 状态 |
|---|----------|------------|------|
| 1 | 科学 AI 必须可独立评估 | `check_quality` / `verify_checklist` / 金标准 20 条 | 已有 |
| 2 | 先做实子任务，再谈端到端 | 分步流水线 + 消融 + 稳定度 | 已有 |
| 3 | 证据与 provenance 一等公民 | EvidenceSpan（含 fulltext）+ `audit.json` | 已有 |
| 4 | 生成与评审分离 | `gap_reviewer` + AI 双人抽检 | 已有 |
| 5 | 搜索/进化需显式评价与验证器 | Route A 多目标分 + 外部验证 | 已有 |
| 6 | 主动学习飞轮：预测→验证→回灌 | 抽检反馈 + DB 验证；扩真人金标准 | 部分 |
| 7 | 结构化共享状态支撑长程科研 | Known / Gap / queries / bundle | 已有 |
| 8 | 实验或等价验证提供可检验奖励 | falsification_test + MP/OQMD/offline | 已有 |

## 3.4 方案写作可用的对标句式（示例）

> 本工作对齐 GOAI「可运行、可复现、可验证」标准；方法上吸收 CASP/ScienceAgentBench 的独立评估纪律，DeepMind GNoME 的生成–验证飞轮，Claude Science / Kosmos 的评审 Agent 与可追溯 provenance，并将材料赛题推荐的 Sciverse/MinerU 证据链与路线 A「LLM×搜索融合」工程化落地。

（引用时注明公开来源；赛程奖项以 [goaihz.com](https://goaihz.com) 为准。）

---

# 四、本项目路径（执行地图）

## 4.1 选定路径

```
GOAI 赛道三 → 算法赛 → 方向三材料 Agent
  → 基本任务（文献调研流水线）
  → 路线 A（构效关系：进化搜索 × LLM 在环）
```

## 4.2 阶段路径（与公开赛程对齐）

| 阶段 | 时间（规划） | 公开提交物 | 本仓库对应动作 |
|------|--------------|------------|----------------|
| 初赛 | ~8.16 | 方案+技术路线（可附可行性） | `docs/proposal/`；demo 跑通；开源计划 |
| 复赛 | ~9.3 | 可运行代码、结果、科学意义、依赖披露 | 强化全文/Sciverse、MP 验证、稳定度报告 |
| 决赛 | ~9.22 | 路演/一页纸/最终仓库 | Demo + 抽检归档 + 金标准摘要 |

## 4.3 技术路径（已实现骨架）

```
topic + ontology
  → QueryRewriter（多意图）
  → Retriever（OpenAlex / local；Sciverse stub）
  → Extractor + 证据门控
  → KnownMap（材料–性能密集区）
  → GapFinder → GapReviewer（next + falsification）
  → Reporter + ConsistencyCheck
  → [可选] RouteASearcher（SEED/SCORE/PRUNE/MUTATE）
  → 质量门禁 / 逐条核验 / AI 双人抽检
```

## 4.4 推荐工作节奏（周为单位）

| 周焦点 | 做什么 | 完成定义 |
|--------|--------|----------|
| 主题与语料 | 收窄 topic；OpenAlex 实跑 | `report.md` 可读、ID 一致 |
| 证据与 Gap | 开 LLM；人工抽 10 条 | 抽检归档 1 轮 |
| 路线 A | 假说质量 + Known 标签 | 无 seed 泄漏；有 candidate-new |
| 金标准 | 双人标 20 条 | `experiments/gold_gaps/` 起步 |
| 复赛件 | MinerU/Sciverse/MP | PARTIAL 项逐项变 PASS |

---

# 五、产出质量关键杠杆（浓缩）

## 5.1 七层总览

| 层 | 一句话 | 优先度 |
|----|--------|--------|
| 证据 | 没有可追溯原文就没有发现 | P0 |
| 模型角色 | 拆分检索/抽取/Gap/评审/写作 | P0 |
| 检索 | 改写+多路+相关性过滤决定上限 | P0 |
| Gap | 可证伪、类型纯、双侧文献 | P0 |
| 路线 A | LLM 必须进搜索环 | P1 |
| 评测 | 题集、消融、抽检、金标准 | P1 |
| 领域 | 主题窄、ontology 深 | P1 |

## 5.2 各层「做对 vs 做错」（速查）

| 层 | 做对 | 做错 |
|----|------|------|
| 证据 | `paper_id`+原文片段；audit 可回放 | 只有标题或模型口吻 |
| 模型 | JSON Schema+重试；评审 Agent | 单次 chat 出全文 |
| 检索 | 多意图；噪声过滤；Known 表 | 一搜到底堆高引 |
| Gap | next+falsify；Known≠新知 | 「还需更多研究」 |
| 路线 A | SEED/SCORE/PRUNE；novelty 标签 | 假说堆砌或 seed 泄漏 |
| 评测 | 固定题集+消融+抽检归档 | 单次好运截图 |
| 领域 | SnSe 级细分主题 | 「AI 发现新材料」 |

更细的关键点表、否决项、提质十条见 **§七**（原展开内容已并入审核章，避免重复）。  
国际对标（CASP 盲评、GNoME 飞轮、Claude Science 评审 Agent）见 **§三**。

---

# 六、优化尝试 · 检验结论 · 未达标项

## 6.1 做过什么

1. 骨架：调研流水线 + Route A MVP  
2. 按杠杆优化：证据门控、改写、评审、Known、分步温度、消融题集  
3. 复查修复：Known 空表、局限误删、空泛 temporal、seed 泄漏、置信度虚高等  
4. 固化检验：`check_quality` / `verify_checklist` / `ai_human_review`

## 6.2 最新检验结论（离线 demo）

| 结果 | 数量 | 含义 |
|------|------|------|
| PASS | **33** | 含原 PARTIAL 五项已闭环 |
| PARTIAL | 0 | — |
| FAIL | 0 | 无硬性崩坏 |

辅助门禁：`check_quality.py` → **11/11 PASS**。  
报告：`outputs/demo/checklist_verification.md`。  
金标准打分：`outputs/demo/gold_score.json`。  
稳定度：`outputs/stability/stability_report.md`（seeds 41/42/43）。

**一句话**：五项冲满分动作已落地——全文证据、金标准 20 条、MP/OQMD（offline 默认可跑）、多种子稳定度、抽检制度均可复跑。

## 6.3 原 PARTIAL → 现已 PASS（落地对照）

| # | 项 | 落地内容 | 验证 |
|---|----|----------|------|
| 1 | 全文证据 | `tools/fulltext.py` + local/MinerU；抽取 `location=fulltext` | checklist 证据层 PASS |
| 2 | 人工金标准 | `experiments/gold_gaps/gold_set_v1.json`（20）+ `score_against_gold.py` | type_accuracy=1.0（匹配子集） |
| 3 | MP/OQMD 闭环 | `tools/materials_db.py`；Route A Top-K `external_validation` | `route_a_external_validation.json` |
| 4 | 多种子稳定度 | `scripts/run_stability.py`，N≥3 | `outputs/stability/` |
| 5 | 人工抽检制度 | checklist + `ai_human_review` + `experiments/reviews/round_*` | rounds≥1 |

有 Key 时：设 `MP_API_KEY` 并将 `route_a.materials_db` / `materials_db.provider` 改为 `materials_project` 或 `oqmd`；安装 MinerU 后对 `data/fulltext/pdfs/*.pdf` 可走真实解析。

优先级（后续增强）：真人覆盖抽检轮次 → 扩金标准至 50 → 接真 MP API → OA PDF+MinerU 批量。

## 6.4 查漏补缺：验收边界与后续行动（2026-07-29）

> **先澄清验收范围**：§6.2 的 `33/33 PASS` 是 `demo_local.yaml`（5 篇本地固定语料、LLM 关闭、默认 `offline` 材料库）上的**离线冒烟验收**，证明代码路径可重跑；它**不等同于** OpenAlex + LLM、OA PDF + MinerU、真实 MP/OQMD 或真人双人标注已经验收。以下表格将历史记录中原有的 5 个 PARTIAL 与当前实现逐项对齐，作为复赛前关闭清单。

| 优先级 | 缺口 / 风险 | 当前事实与证据 | 对评审的影响 | 可执行补缺动作 | 达标证据 |
|---|---|---|---|---|---|
| **P0** | 离线 PASS 被误读为生产 PASS | `verify_checklist.py` 固定读取 `demo_local.yaml`；检查项大量验证“文件/产物存在” | 易造成「真实工具链已接入」的过度表述 | 分成 `smoke` 与 `production` 两套核验；提交页显式标注运行配置、数据源和是否联网 | `verify_production.py --config configs/production.yaml` 的独立报告 |
| **P0** | 全文证据尚未是 OA PDF + MinerU 流程 | demo 的 `full_text` 预置在 `data/local_papers.json`，`fulltext_source=local_cache`；MinerU 仅在本地 PDF 存在时触发 | 在线 OpenAlex 路径仍可能只有摘要，不可称“MinerU 全文已验证” | 下载可公开 OA PDF → MinerU 解析 → 记录 PDF 哈希、页码/段落与解析版本 | `fulltext_index.json` 中 `source=mineru`；可回读 PDF 的引用样本 |
| **P0** | Gap 证据链没有优先使用全文 | `gap_finder._ev_for()` 当前取 `abstract/title`，即使 extraction 已是 `fulltext` | 核心 Research Gap 仍可能是摘要级证据 | 让 Gap Finder 复用 `paper_source_text()` 并保存全文片段 offset/chunk id | Gap `evidence_chain.location=fulltext` 且 quote 可在原文定位 |
| **P0** | MP/OQMD 闭环默认是离线词典 | `materials_db.py` 的 `offline_stub` 对已知 motif 返回结果；没有 Key 或空结果可回退 offline | 不能将 offline 判定称为材料数据库验证 | 增加 production 模式：指定 MP/OQMD 时无 Key、API 失败或空结果均 `error/skip`，不得回退为 PASS | 真实 API 响应、查询参数、material_id 与 e_hull 归档 |
| **P0** | 金标准覆盖率不足，匹配子集指标易偏高 | `gold_set_v1.json` 有 20 条，但 demo `gold_score.json` 仅匹配 6 条；`type_accuracy=1.0` 是按 matched 子集计算 | 不能用单一 type accuracy 证明整体校准质量 | 公布 coverage；设门槛（如匹配 ≥15/20）；由两位领域标注者独立标注后裁决冻结 | 双人标注表、分歧率、冻结版本、coverage 与全量指标 |
| **P0** | 默认线上配置未被验收 | `default.yaml` 使用 OpenAlex；LLM 开关虽开但无 Key 时会降级；当前验收未跑该配置 | 真实环境中的检索、超时、限流与 LLM 输出未知 | 增加脱敏 `production.yaml`，跑 OpenAlex、LLM-on 和无 Key 降级三种 profile | 三份可复跑报告、依赖/密钥说明和失败案例 |
| **P1** | Route A 的 LLM 在环未在 demo 中实际执行 | demo 配置 `llm.enabled=false`，角色轨迹可来自 `rule_mutate` | 仅证明规则进化搜索，未证明「LLM×搜索融合」 | LLM-on 运行中断言角色含 `llm_seed_refine`、`llm_score` 或 `llm_focus_mutate`；保留规则版作消融 | `role_trace`、模型/温度/seed、成本和失败率报告 |
| **P1** | AI 抽检不能替代真人审核 | 当前轮次可由规则/LLM 仿真产生，且不代表独立领域判断 | 人工审核制度的可信度有限 | 至少完成一轮领域人员双人抽检，保留匿名标注、裁决和改码记录 | 签署/匿名化审核表 + AI/人工分歧分析 |
| **P1** | 稳定度只测结构指标，未测幻觉/引用错误 | `run_stability.py` 统计 Gap 数、类型 Jaccard、Top score；固定离线数据的方差可为 0 | “多种子稳定”不能说明科学主张稳定或无幻觉 | 加入 quote-in-source 比率、Gap ID Jaccard、错误引用率、LLM-on 方差与成本统计 | N≥3 的均值±标准差、置信区间和异常样本 |
| **P1** | provenance 粒度不足 | `EvidenceSpan` 未保存页码、char offset、chunk hash；一致性检查主要核对 paper id | 审稿人难以快速回到精确原文 | 存 `source_url/pdf_hash/page/chunk_id/start/end`；验证 quote 是源文本子串 | 任意 Gap 一键回跳原文片段的演示 |
| **P1** | Sciverse 当前是 fallback stub | `SciverseRetriever` 记录“not configured; fallback openalex” | 不宜宣称 Sciverse 已接入 | 接入合法 API/MCP，或在提交材料明确列为“计划能力” | 真实 Sciverse 调用 trace 与 doc_id/offset |
| **P1** | 自动化回归与依赖披露不足 | 未建立针对全文、MP 客户端、金标准打分的 pytest；MinerU/API 配置未形成完整依赖清单 | 改动后容易回归，复赛复现实操风险高 | 增加单元/集成测试；补 `DEPENDENCIES.md`（可选工具、密钥、数据许可、降级行为） | CI/本地测试报告和一页安装复现说明 |
| **P2** | 基准与矛盾证据标准偏弱 | benchmark 未形成带阈值的全题集评分；当前 contradiction 可来自同一篇论文的正反陈述 | 科学评测强度不足 | 全题集评分、回归阈值；区分“篇内争议”与“跨论文矛盾”，后者要求不同 paper id | benchmark 结果表；跨文献双侧证据样例 |

**提交表述建议**：当前可写“离线可复现的端到端 demo 已通过 33 项冒烟检查”；在完成上表 P0 后，再写“真实全文/材料库/人工金标准闭环已验证”。不要把 `offline_stub`、预置全文或 AI 仿真抽检表述为真实外部验证或人工专家结论。

## 6.5 全文证据链升级（已实现，待外部环境验收）

> 本节记录 2026-07-29 的工程升级。**已实现**表示接口、质量门禁和可复跑脚本已写入仓库；**生产已验证**必须由带真实 OA PDF、MinerU、GROBID、Qdrant 的 `production.yaml` 运行结果证明，不能用 local demo 替代。

| 层 | 新增实现 | 关键产物 / 字段 | 运行边界 |
|---|---|---|---|
| OA 获取 | OpenAlex `oa_url` + Unpaywall DOI 补全；仅下载返回的 OA PDF | `fulltext_url`、`oa_status`、`oa_license`、PDF SHA-256 | `UNPAYWALL_EMAIL` 必填；不爬取付费墙 |
| 双解析 | MinerU 主解析 Markdown/JSON；GROBID 产出 TEI 与科学论文结构 | `data/fulltext/parsed/<paper>/`、parse manifest | MinerU CLI/API 与 GROBID 服务不可用时会写审计降级 |
| 分块 | 按 Markdown 章节、字符窗口和 overlap 切块 | `chunk_id`、`section`、`char_start/end`、`chunk_hash` | 页码依赖 GROBID 坐标扩展，当前优先保证字符定位 |
| 索引 | 文件索引保障离线可跑；Qdrant 按 `paper_id/section/page/pdf_hash` payload 检索 | `evidence_chunks.json`；Qdrant collection | Qdrant 不可达时退回文件索引，生产 verifier 不因此通过 |
| Gap 引证 | Gap Finder 后置 `EvidenceSelector`，优先以支撑论文过滤检索全文 chunk | `EvidenceSpan.provenance`：URL、hash、parser、chunk、offset | strict profile 无全文命中则拒绝，不再摘要冒充全文 |
| 校验 | quote-in-source、offset、provenance、全文覆盖率和无静默 MP fallback | `consistency.json`、`production_verification.json` | `demo_local.yaml` 保持宽松，`production.yaml` 启用严格门禁 |
| 部署 | `docker-compose.yml` 启动 GROBID/Qdrant；`.env.example`、`DEPENDENCIES.md` 披露依赖 | 环境变量与许可清单 | 不提交真实 key、下载的受限 PDF 或 Qdrant 持久化数据 |
| LLM 后端 | 默认 OpenAI-compatible；可选 Cursor SDK 一次性本地 Agent | `LLM_PROVIDER`、`CURSOR_*` 与 `audit.json` 的 agent/run ID | Cursor 为商业闭源服务；保留可复现 fallback，且 SDK 提示层禁止工具/文件修改 |

### 生产验收命令

```bash
cd tracks/algorithm/materials_agent
pip install -r requirements.txt
docker compose up -d grobid qdrant
# 配置 OPENALEX_EMAIL、UNPAYWALL_EMAIL、OPENAI_API_KEY、MP_API_KEY
# 可选 Cursor SDK：pip install ".[cursor-sdk]"；设 LLM_PROVIDER=cursor_sdk、CURSOR_API_KEY、CURSOR_MODEL
python scripts/run_survey.py survey -c configs/production.yaml
python scripts/verify_production.py -c configs/production.yaml
pytest tests -q
```

生产验收的最低通过条件：

1. `fulltext_index.json` 至少达到 `min_fulltext_paper_ratio`，且来源为 `mineru` / `grobid`（兼容旧跑次 `grobid_fusion`），不能是 `local_cache`。
2. 每个 Gap 全文引用都含 `paper_id + source_url + pdf_hash + parser + chunk_id + offset`，并能在保存的全文中精确找到 quote。
3. `materials_project` / `oqmd` 生产配置在无 Key、API 失败或空结果时返回 `error`，不得回退为 `offline_stub`。
4. `verify_production.py` 通过后，才可在提交物中表述为“生产全文证据链已验证”。

## 6.6 生产链路重跑：意义、边界与高分路径（2026-07-30）

### 6.6.1 重跑生产链路到底有什么意义

`demo_local` 的 `33/33 PASS` 只证明**代码路径可复现**；`production.yaml` 重跑证明的是另一件事：

| 对比项 | `demo_local` / checklist | `production` 重跑 |
|--------|--------------------------|-------------------|
| 数据 | 预置本地论文/摘要级全文 | OpenAlex + Unpaywall 真 OA PDF |
| 解析 | 可跳过或用 `local_cache` | **GROBID 主解析**（默认；MinerU 可选，非必须）必须产出可用全文 |
| 证据 | 宽松，可接受摘要/缓存 | 严格：`mineru`/`grobid`（兼容 `grobid_fusion`）+ provenance |
| 验收脚本 | `verify_checklist.py` | `verify_production.py` |
| 对评审表述 | 「离线冒烟已通过」 | 「生产全文证据链已验证」（仅当 verifier PASS） |

因此，**在 Docker/MinerU/密钥刚打通后立刻重跑 production，不是「再跑一遍同样的分」**，而是：

1. **关闭 P0 表述风险**：把「代码有接口」升级为「真实工具链可出证据」。
2. **暴露真实失败模式**：OA `403`、解析超时、Qdrant/GROBID 不可达、模型冷启动——这些在 demo 里永远测不到。
3. **产出可引用审计物**：`outputs/production/` 下的 `fulltext_index.json`、`parse_manifest.json`、`audit.json`、`production_verification.json`，是复赛答辩的硬证据。
4. **给后续冲分定基线**：先拿到「严格门禁下的真实分数/失败项」，再决定优化顺序；否则优化 demo 指标会对评审无效。

**边界（必须写进方案）**：

- 当前环境重跑若 `parsed_oa_ratio` 未过门槛，结论只能是「环境/解析仍失败」，**不能**写成「科学发现已生产验证」。
- GROBID / MinerU / Qdrant 齐备后，重跑才有评分意义；此前应优先修环境，而非反复调 LLM 温度。
- 一次 PASS 仍不够：至少保留 **配置名、日期、种子、依赖版本、失败样例**；多种子与金标准覆盖另算加分项。

### 6.6.2 评审维度 → 冲分杠杆（把力气花在刀刃上）

算法赛统一口径（方向内归一化）：**技术性能 45% · 科学意义 30% · 方法创新 20% · 开源贡献 5%**。

| 维度 | 评委要看什么 | 本仓库高分动作（按 ROI） |
|------|--------------|--------------------------|
| **技术性能 45%** | 可跑、可验、指标可复现 | ① `verify_production.py` PASS；② quote-in-source / provenance 全覆盖；③ 多种子稳定度含**引用正确率**；④ 金标准 **coverage≥15/20** 后再报 accuracy |
| **科学意义 30%** | Gap 真、可证伪、主题够窄 | ① 坚持 SnSe 级细分主题；② Gap 强制 `next_step` + `falsification`；③ 跨论文 contradiction 要求不同 `paper_id`；④ 领域双人抽检 ≥1 轮归档 |
| **方法创新 20%** | 不是「会聊天的综述」 | ① 路线 A：**LLM 进 SEED/SCORE/PRUNE**（`role_trace` 有 llm_*）；② EvidenceSelector 全文检索而非摘要糊弄；③ 可选 Cursor SDK 作后端但**披露 + 保留 OpenAI/offline fallback** |
| **开源贡献 5%** | 别人能复现 | ① `DEPENDENCIES.md` / `.env.example`；② smoke vs production 两套验收写清；③ 不提交密钥与受限 PDF |

### 6.6.3 推荐高分路径（有序执行，勿并行乱撞）

```text
阶段 0  环境基线（本阶段）
        docker compose up -d grobid qdrant
        MinerU: MINERU_MODEL_SOURCE=local + 本地 PDF-Extract-Kit
        run_survey -c production.yaml → verify_production.py
        产物: production_verification.json（记下 FAIL 项）

阶段 1  拿下「可验证」硬门槛（技术性能底座）
        目标: verify_production = PASS
        - 提高 OA 可解析率：过滤 403/非 PDF；扩 Unpaywall；缓存成功 PDF
        - MinerU CLI: mineru -b pipeline；记录 parser 版本与耗时
        - GROBID 健康: /api/isalive；融合写入 grobid_fusion
        - Qdrant collection 有 payload；audit 记录 backend=qdrant|file
        退出条件: parsed_oa_ratio≥阈值 且 Gap 全文 span≥1（strict）

阶段 2  科学意义与证据纯度
        - Gap 证据一律 EvidenceSelector(fulltext)；禁 abstract 冒充
        - 扩充/校准金标准；公布 matched coverage，不单报子集 accuracy
        - 领域双人抽检 10 条，归档 experiments/reviews/
        退出条件: 任意抽检 Gap 可一键回到 PDF 子串

阶段 3  方法创新可见（路线 A）
        - production 或独立 profile 开 route_a + LLM-on
        - 断言 role_trace 含 llm_seed_refine / llm_score / llm_focus_mutate
        - MP_API_KEY 真库验证；禁止 offline_stub 当 PASS
        - 规则版作消融对照，写进报告「融合深度」段落
        退出条件: Top-K 假说有 external_validation 真响应归档

阶段 4  稳健性与提交包装
        - run_stability：结构指标 + quote-in-source 率 + 错误引用率
        - 固定 seed / 模型名 / 成本粗估写入 audit
        - 提交话术：三分法——离线 smoke / 生产证据链 / 路线 A 消融
```

### 6.6.4 「下一周」最小冲分清单（可勾选）

| # | 动作 | 命令 / 产物 | 对应维度 |
|---|------|-------------|----------|
| 1 | ~~盯到 `verify_production` PASS~~ **已完成 2026-07-30**（`parsed=5/10`） | `outputs/production/production_verification.json` | 技术 45% |
| 1b | OA 直链卫生 + 仓库镜像候选（Europe PMC / OSTI servlet）；解析缓存复用 | `oa_download.py` / `fulltext.py` | 技术 45% |
| 2 | 抽样 3 条 Gap 人工核对 quote⊂原文 | 截图/笔记进 `experiments/reviews/`（见该目录 README） | 科学 30% |
| 3 | 配置可复现 LLM（建议 `OPENAI_API_KEY`；Cursor 本地桥在 Win 上可失败并自动 fallback）后跑 Route A | `configs` 开 `route_a` + `MP_API_KEY` | 方法 20% |
| 3b | ~~真 MP 外验~~ **已跑通 2026-07-31**（`outputs/production_route_a/`，provider=`materials_project`）；LLM 角色需 OpenAI 余额或可用兼容端点 | `scripts/run_route_a.py` | 方法 20% |
| 4 | 金标准 coverage 报告 | `score_against_gold.py` + coverage 字段 | 技术+科学 |
| 5 | 一页依赖披露 | 更新 `DEPENDENCIES.md`（MinerU 本地模型、GROBID、镜像源） | 开源 5% |

### 6.6.5 明确不要做的低 ROI 事

- 在 `verify_production` 仍 FAIL 时，大规模调 prompt / 温度「冲观感」。
- 把 `offline_stub`、demo `local_cache`、AI 仿真抽检写成「专家验证」或「数据库验证」。
- 为冲数量放宽主题（「AI 发现新材料」级空泛题）——科学意义会掉分。
- 只堆商业闭源模型、不留可复现 fallback——方法与开源两项双杀。

**一句话策略**：先用 **production 重跑** 把「可验证」钉死 → 再用金标准与双人抽检把「科学意义」钉死 → 最后用 **LLM×Route A + 真 MP** 展示方法深度。顺序反了会白优化。

## 6.7 完成度快照（2026-08-02）

> 完整对照表、功能清单、方法说明与优化优先级见专文：[`完成度与优化方向.md`](完成度与优化方向.md)。

| 项 | 状态 |
|----|------|
| 基本任务生产证据链 | ✅ `verify_production` PASS（`parsed=7/10`，MinerU×7，Gap 全文 span=20） |
| 路线 A 真 MP 外验 | ✅ `materials_project` Top-K pass |
| 路线 A LLM 进环 | ⚠️ 代码就绪；最近运行因额度/桥失败 → `llm_score_unavailable` |
| 用户黑盒 + 调试 UI | ✅ `serve_viewer.py` |
| 金标准 coverage | ⚠️ demo 上 coverage=0.3（6/20）；勿只报子集 accuracy=1.0 |
| 科学人工抽检 | ⚠️ 有轮次骨架；需补 ≥3 条可归档人工核对 |
| Sciverse | ⚪ 未实接（OpenAlex fallback） |

**当前总判**：基本任务生产侧已达标；冲分主缺口是 **LLM-in-the-loop 实跑** + **科学意义材料（抽检/coverage）**。

---

# 七、人工审核

## 7.1 关键点（否决 → 高权重 → 加分）

**一票否决**：证据真实性 · 可证伪性 · 非幻觉数值 · Known 当新知 · 过宣称  

**高权重**：类型纯度 · 支持/反驳分离 · 主题相关 · next 可操作 · 证据粒度 · 与 Known 一致  

**加分**：机制解释 · 负结果清晰 · 可延续 · 对齐路线 A · 审计可回放  

## 7.2 最小必要知识

| 层 | 内容 | 用途 |
|----|------|------|
| 半天 | 四类型 Gap、证据最低标准、Known 表、会打开 gaps/papers | 制度性抽检 |
| 一周 | ZT/κ/Seebeck、limitation 信号、DFT≠实验、ontology | 审得准 |
| 复赛 | MP 稳定性直觉、多种子统计、合规披露 | 加分项 |

## 7.3 大幅提质方法（性价比序）

1. 否决清单前置  
2. 双人对立审 + `min(A,B)`  
3. 按类型分层抽样  
4. 金标准闭环校准自动分  
5. 原文对照仪式  
6. 改码后短闭环（门禁→核验→抽检）  
7. 主题收窄  
8. Gap↔路线 A 联审  
9. 强模型用于「审」而非「自夸润色」  
10. 负结果入正册  

## 7.4 AI 仿真抽检（已落地）

协议：`experiments/human_review_checklist.md`  
脚本：`scripts/ai_human_review.py`  
归档：`experiments/reviews/round_*/`

```bash
python scripts/ai_human_review.py --gaps outputs/demo/gaps.json --n 10 --seed 42
# 有 Key：加 --use-llm -c configs/default.yaml
```

说明：AI 双人审是质量雷达，**不替代**领域专家终审。

### 人工金标准是什么

人（最好双人）按统一规则标好的 20–50 条 Gap「标准答案」（是否真 Gap、类型、证据、新颖、可操作），用来打分和校准自动系统；与「每轮抽 10 条质检」不同——金标准要**冻结成集合**。

---

# 八、专业术语名词解释（摘要版）

> 完整中英对照表较长，按主题检索；详细条目见文末 **附录 A**。

| 主题 | 必懂词 |
|------|--------|
| 赛题 | GOAI、算法赛、基本任务、路线 A、可复现、证据链 |
| 国际对标 | CASP、ScienceAgentBench、MLE-bench、GNoME、Claude Science、Kosmos |
| Gap | missing_link / contradiction / underexplored / method_gap、可证伪、Known、candidate-new |
| 系统 | Query 改写、多路召回、EvidenceSpan、audit、ontology、消融、金标准、provenance |
| 路线 A | SPR、SEED/SCORE/PRUNE、MP/OQMD、形成能、主动学习飞轮 |
| 热电 | ZT、κ、Seebeck、功率因子、DFT、SPS |
| 工具 | OpenAlex、Sciverse、MinerU、MCP、RAG、LLM temperature/seed |

易混：

- **Known 表** ≠ 人类全部知识（只反映当前语料高频共现）  
- **candidate-new** ≠ 已证实发现  
- **抽检** ≠ **金标准**（节奏 vs 冻结答案集）  
- **Agent 评审** ≠ **专家终审**  
- **对标 GNoME/CASP** ≠ 复制其算力；学评价纪律与闭环结构

---

# 九、命令与文件索引

## 9.1 常用命令

```bash
cd tracks/algorithm/materials_agent
pip install -r requirements.txt

# 离线 demo（含 Route A）
python scripts/run_survey.py survey -c configs/demo_local.yaml

# OpenAlex 在线
python scripts/run_survey.py survey -c configs/default.yaml --route-a

# 质量
python scripts/check_quality.py
python scripts/verify_checklist.py
python scripts/run_benchmark.py
python scripts/ai_human_review.py --gaps outputs/demo/gaps.json --n 10 --seed 42

# 冲满分五项
python scripts/score_against_gold.py
python scripts/run_stability.py -c configs/demo_local.yaml --seeds 41,42,43
# MP 真库：设 MP_API_KEY 后改 configs 中 materials_db.provider=materials_project

# 生产全文证据链：先配置 .env，再启动本地服务
docker compose up -d grobid qdrant
python scripts/run_survey.py survey -c configs/production.yaml
python scripts/verify_production.py -c configs/production.yaml
pytest tests -q
```

## 9.2 关键路径

| 用途 | 路径 |
|------|------|
| 本指南 | `readme_agent.md` |
| 工程说明 | `README.md` |
| 初赛方案 | `docs/proposal/materials_agent_preliminary.md` |
| 配置/本体 | `configs/demo_local.yaml`, `configs/default.yaml`, `configs/production.yaml` |
| 流水线 | `materials_agent/pipeline.py` |
| 全文工具链 | `tools/oa_download.py`, `tools/fulltext.py`, `tools/chunking.py`, `tools/index/` |
| 部署披露 | `docker-compose.yml`, `.env.example`, `DEPENDENCIES.md` |
| 抽检协议 | `experiments/human_review_checklist.md` |
| 金标准 | `experiments/gold_gaps/gold_set_v1.json` |
| 稳定度 | `outputs/stability/` |
| 产出 | `outputs/demo/`（smoke）与 `outputs/production/`（严格全文验收） |
| 官方手册 | `document/AI_for_reserach.pdf`（仓库根下） |

## 9.3 公开信息来源（便于方案引用）

| 来源 | 用途 |
|------|------|
| [goaihz.com](https://goaihz.com) | 报名、赛程、手册下载（最终准绳） |
| GOAI 四大赛道发布通稿（InfoQ 等） | 共同标准话术：可运行/可复现/可验证 |
| 赛道手册 PDF | 材料方向细则、评分、提交物 |
| [CASP](https://predictioncenter.org/) / AlphaFold 公开报道 | 盲测与独立评估纪律 |
| ScienceAgentBench（论文/仓库） | 任务级评测、专家校验、子任务可执行产出 |
| OpenAI MLE-bench | 多种子、自动 grading、真实工程任务评 Agent |
| DeepMind GNoME / AlphaFold 公开论文与博客 | 生成–验证飞轮；可量化突破 |
| Anthropic Claude Science 公开说明 | 协调 Agent + Reviewer + provenance |
| FutureHouse / Kosmos 公开材料 | 结构化世界模型、结论可引用 |
| Lila Sciences（AI Science Factory）公开介绍 | 假说–实验–学习闭环叙事 |
| Sciverse / MinerU 公开文档与教程 | AI-Ready 数据与可追溯检索 |

---


# 附录 A · 专业术语全表

## A.1 赛题与项目总览

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| GOAI | GOAI | 世界人工智能开源大赛；本项目属赛道三「前沿探索 AI for Research」。 |
| 算法赛题 | Algorithm track | 给定问题、数据与评测框架，提交可复现解法；与开放探索赛独立排名。 |
| 开放探索赛题 | Open exploration | 自定真实科学问题与 Agent 探索环境；本仓库当前未主做。 |
| 方向三 / 材料文献 Agent | Materials literature agent | 算法赛三方向之一：文献驱动、产出可证伪科学发现线索的智能体。 |
| 基本任务 | Basic task | 必做：文献调研 Agent（检索→抽取→Gap→结构化报告+证据链），方向内约 50% 权重。 |
| 进阶路线 A/B/C | Route A/B/C | 在基本任务之后三选一深入；本项目选 **路线 A 构效关系发现**。 |
| 初赛 / 复赛 / 决赛 | Preliminary / Semi / Final | 提交阶段：方案→可运行代码与结果→路演展示。 |
| 科学意义 | Scientific significance | 评审维度：结果对领域是否有真实意义，是否超出已有边界。 |
| 开源贡献 | Open-source contribution | 代码/管线可复用、文档与许可清晰、社区可接续。 |
| 依赖披露 | Dependency disclosure | 公开开源依赖、商业 API、闭源模型、数据授权与版本。 |
| 可运行 / 可复现 / 可验证 | Runnable / Reproducible / Verifiable | GOAI 公开共同标准三要素。 |

## A.2 Research Gap 与发现逻辑

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| Research Gap | Research Gap | 文献中未充分解决、矛盾或缺失连接的研究缺口；本项目核心产出单位。 |
| missing_link | missing_link | Gap 类型：材料/性能/机制之间缺少被证据支撑的关联。 |
| contradiction | contradiction | Gap 类型：主张互相冲突（篇内对立或双侧文献对立）。 |
| underexplored | underexplored | Gap 类型：方向被提及但探索不足、局限反复出现。 |
| method_gap | method_gap | Gap 类型：方法不平衡（如仅有 DFT/ML、缺实验/工艺闭环）。 |
| 可证伪性 | Falsifiability | 能事先说明「怎样的结果算否定该 Gap/假说」。 |
| suggested_next_step | Next step | 针对 Gap 的可执行下一步。 |
| falsification_test | Falsification test | 明确的否证条件或协议。 |
| novelty | Novelty | 新颖性分数；相对「已知」而言。 |
| actionability | Actionability | 可操作性：下一步能否真正开工。 |
| overlaps_known | overlaps_known | 是否与 Known 密集区重叠。 |
| Known / 已知密集区 | Known dense region | 语料内高频材料–性能共现（`known_pairs`）。 |
| candidate-new | Candidate-new | 相对本语料 Known 的候选新缺口/假说，仍待验证。 |
| Known 当新知 | Known-as-new | 把 Known 对说成重大首次发现。 |
| 负结果 | Negative result | 被清晰解释的失败、矛盾或不成立。 |
| 过宣称 | Overclaim | 把假说写成已证实发现。 |
| 幻觉 | Hallucination | 编造文献中不存在的材料、数值、DOI、结论。 |
| 人工金标准 | Human gold standard | 人按统一规则标好的冻结答案集，用于打分与校准。 |

## A.3 证据、抽取与审计

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| EvidenceSpan | Evidence span | 基础字段 `paper_id + claim + quote + confidence + location`；production 额外要求 provenance（URL、PDF hash、parser、chunk、offset）。 |
| 证据链 | Evidence chain | 多条 EvidenceSpan 支撑主张。 |
| 证据门控 | Evidence gate | 无依据则丢弃或降级。 |
| 知识抽取 | Information extraction | 抽出材料/性能/方法/合成/局限等字段。 |
| OA | Open Access | 开放获取全文。 |
| DOI | DOI | 文献永久标识符。 |
| audit | Audit trail | 步骤级工具调用日志。 |
| 一致性检查 | Consistency check | ID/引用自洽校验。 |
| 归一化 | Normalization | 异名统一（如 ZT / figure of merit）。 |
| Schema | Schema | 结构化输出约束与重试。 |

## A.4 检索与 Agent 组件

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| Agent | Agent | 规划、调工具、迭代产出的系统。 |
| Query 改写 | Query rewriting | 主题→多意图检索式。 |
| 多路召回 | Multi-query retrieval | 多查询合并去重。 |
| OpenAlex | OpenAlex | 默认开放文献 API。 |
| Sciverse | Sciverse | 科学智能数据库；语义检索与证据片段。 |
| MinerU | MinerU | PDF→结构化解析引擎。 |
| MCP | MCP | 工具/数据接入协议。 |
| RAG | RAG | 检索增强生成。 |
| temperature / seed | — | 解码随机性 / 复现种子。 |
| Ontology | Ontology | 领域词表与先验。 |
| Skill contract | Skill contract | 任务契约化拆分。 |

## A.5 路线 A 与数据库

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| 构效关系 | SPR | 结构/组成与性能的可解释关联。 |
| SEED/SCORE/PRUNE/MUTATE | — | LLM 在环角色。 |
| GA / MCTS / BO | — | 搜索外环算法族。 |
| Materials Project / OQMD / NOMAD | — | 材料开放数据库，用于交叉验证。 |
| 形成能 / 相稳定性 | Formation energy / Phase stability | 组成可行性常用指标。 |

## A.6 热电领域（demo）

| 术语 | 解释 |
|------|------|
| ZT | 热电优值。 |
| 热导 κ / 晶格热导 κ_L | 导热；常通过缺陷等抑制晶格部分。 |
| Seebeck / 功率因子 / 迁移率 | 电热输运相关量。 |
| 空位工程 / 共振掺杂 / 能带过滤 | 常见机制叙事。 |
| DFT / MD / SPS / XRD·SEM·TEM | 计算、动力学、烧结与表征。 |

## A.7 评测与质控

| 术语 | 解释 |
|------|------|
| 抽检 / 双人审 / 裁决 | 抽样质检；A/B 独立打分；保守合并。 |
| keep/revise/reject | 保留/修改/淘汰。 |
| 消融 / 固定题集 / 多种子稳定度 | 关模块对照；固定主题；换种子看一致性。 |
| PASS/PARTIAL/FAIL | 核验结论三态。 |
| 可检查性 / 可延续性 | 过程可复查；产物可被他人接续。 |

## A.8 产出文件

| 文件 | 含义 |
|------|------|
| `papers.json` / `extractions.json` / `gaps.json` | 文献 / 抽取 / Gap |
| `known_pairs.json` / `queries.json` / `consistency.json` / `audit.json` | Known / 查询 / 一致性 / 审计 |
| `report.md` / `route_a_spr_*` / `bundle.json` | 报告 / 路线 A / 整包 |

## A.9 世界级赛事与顶尖团队（对标用语）

| 术语 | 英文/代号 | 解释 |
|------|-----------|------|
| CASP | Critical Assessment of Structure Prediction | 蛋白结构预测社区盲测实验；预测时不见实验结构，由独立评估对照真值。启示：独立协议、信息隔离。 |
| AlphaFold | AlphaFold | DeepMind 蛋白结构预测系统；在 CASP 等场合以可量化指标证明突破。 |
| GNoME | Graph Networks for Materials Exploration | DeepMind 材料发现管线：候选生成→过滤→DFT/库验证→主动学习回灌。对标路线 A + MP/OQMD。 |
| AlphaEvolve / AI co-scientist | — | DeepMind 公开方向：LLM 引导进化/多 Agent 协作假说；需显式评价器。 |
| ScienceAgentBench | ScienceAgentBench | 从真实论文抽取科学 Agent 任务的评测集；强调子任务可执行与专家校验。 |
| MLE-bench | MLE-bench | OpenAI 等公开的 Kaggle 风格 Agent 基准；多种子、自动 grading。 |
| Claude Science | Claude for Science | Anthropic 公开科学 Agent 叙事：协调 Agent、独立 Reviewer、产出带 provenance。 |
| Kosmos | Kosmos（FutureHouse / Edison） | 文献与分析 Agent 共享结构化世界模型；结论须可引用文献或代码。 |
| AI Science Factory | Lila Sciences | 假说→实验→学习的工厂式闭环；实验提供可验证奖励信号。 |
| provenance | Provenance | 主张的来源可追溯性（文献片段、工具调用、代码/数据版本）。 |
| 主动学习飞轮 | Active learning loop | 预测/生成 → 验证 → 把结果回灌模型或规则，持续收紧搜索。 |
| 盲测 / 信息隔离 | Blind evaluation | 评测时不向系统泄露真值或测试标签，防止泄漏刷分。 |

---

**维护**：赛讯以官网为准；§三对标信息随公开论文/博客更新。改核心逻辑后请重跑 §九命令中的质量三件套。
