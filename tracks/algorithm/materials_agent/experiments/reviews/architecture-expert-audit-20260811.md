# 专家架构与实现流程核验 · 问题清单与逐条升级

> 日期：2026-08-11  
> 范围：`tracks/algorithm/materials_agent` 整体架构 + 主调研流水线 + 门禁/UI/Sciverse 支线  
> 视角：可复现性、门禁诚实性、数据契约、科学可辩护性、维护成本（非单点 bug 清单）  
> 对照基线：`outputs/production_sciverse` 六轮终态 PASS；主叙事仍应以干净 `run_survey` 路径为准

---

## 0. 一句话结论

**主链路设计是对的**（调研 → 证据回源 → 正交门禁 → 双 UI），但 **Sciverse/验收支线把「复现」变成了「流水线 + 事后修补序列」**，再叠加 **门禁产物互踩、缓存失效不全、检索来源可静默漂移**，会在答辩与重跑时露出架构裂缝。下文按严重度列出问题，并给出可执行升级项。

---

## 1. 当前架构（应然 vs 实然）

### 1.1 应然主路径（健康）

```text
configs/*.yaml
  → run_survey / cli.survey
  → LiteratureSurveyAgent.run  (pipeline.py)
       rewrite → retrieve → fulltext/parse → archive?
       → chunk/index → extract → known → gaps+evidence
       → review → metrics → report → consistency → save
  → outputs/<run>/{gaps,papers,bundle,audit,...}.json
  → [正交门禁] verify_production | science_review_gate | objective_review
  → serve_viewer（黑盒 /debug 白盒）
```

这与 `README.md` §2 流程图一致，模块边界清楚：`agents/` 业务、`tools/` I/O、`scripts/` 门禁与运维。

### 1.2 实然旁路（风险集中区）

```text
build_sciverse_verify_bundle.py  ──注入缓存 PDF / 占位标题──┐
reground_production_gaps.py      ──改写 gaps 证据──────────┤
upgrade_sciverse_expert_rounds.py──消毒标题/Gap────────────┼→ 同一 outputs/production_sciverse
finish_sciverse_expert_rounds.py ──TEI 标题 / 恢复 temporal─┘
objective_review_run.py          ──覆盖 production_verification.json
serve_viewer.py                  ──user_result 缓存可能陈旧
```

**问题本质：** 金标跑次的真相源变成「脚本编年史」，而不是「配置 + 一次 pipeline」。

---

## 2. 架构上站得住的部分（不必推翻）

| 优点 | 说明 |
|------|------|
| Profile 隔离 | demo / production / sciverse / route_a 分轨，避免 smoke 冒充生产 |
| 证据优先 | 生产禁 abstract 冒充、禁 offline 材料库静默回退、quote⊂source |
| 审计留痕 | `audit.json` 记录降级（Sciverse→OpenAlex、Qdrant→file） |
| 门禁意图正交 | 工程 verify ≠ 科学 L0/L1 ≠ 专家标准包 |
| 双 UI 分工 | 黑盒对外行为、白盒对 provenance |
| 契约有中心 | `models.py` 的 Paper / ResearchGap / EvidenceSpan 是真 schema |

---

## 3. 问题清单（专家判定）

### A. 可复现性 / 真相源

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| A1 | **P0** | 金标目录依赖事后修补脚本，单次 `run_survey` 无法复现终态 | `upgrade_*` / `finish_*` / `reground_*` / `build_sciverse_verify_bundle.py` |
| A2 | **P0** | 注入路径用 PDF stem 当 title（`SV-paper …`），主题门禁与报告叙事被污染 | `build_sciverse_verify_bundle.py` 中 `title=stem` |
| A3 | P1 | 死目录 `src/` 与活包 `materials_agent/` 并存，新人易找错入口 | 仓库根 `src/**/.gitkeep` |
| A4 | P1 | `完成度与优化方向.md` 仍写 MinerU 主解析生产证据，与现行 GROBID-primary 配置漂移 | 文档 2026-08-02 vs `production*.yaml` |

### B. 门禁与验收契约

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| B1 | **P0** | `objective_review_run` **覆盖** `production_verification.json`（`profile: objective_review`），抹掉 `verify_production` 溯源 | 当前 sciverse 文件已是 `profile: objective_review` |
| B2 | P1 | 三门禁正交写在文档里，但脚本层耦合：objective 既判专家包又写工程验收文件 | `scripts/objective_review_run.py` |
| B3 | P1 | `optimization_metrics.json` 可被后写脚本裁成子集，丢失 boilerplate / provenance / pass_flags | 现文件仅 5 个字段；`topic_focus.compute_optimization_metrics` 输出更丰富 |
| B4 | P2 | `fulltext_source=grobid_fusion` 旧标签与现行 `grobid` 并存，契约语义模糊 | gaps / papers 历史字段 |

### C. 检索诚实性与质量门

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| C1 | **P0** | `backend: sciverse` 无 token / 空结果时静默 OpenAlex，profile 名仍叫 sciverse | `SciverseRetriever` fallback |
| C2 | P1 | `production_sciverse` 关 LLM + 关 rewrite/multi_query，科学发现叙事偏「规则抽取演示」 | `production_sciverse.yaml` |
| C3 | P1 | oversample×3 再裁切有全文论文：正确，但 audit 未强制写入「最终来源占比」到用户可见 metrics | `pipeline.py` fulltext_select |
| C4 | P2 | 主题材料正则硬编码热电名单，换 ontology 泛化弱 | `topic_focus.py` |

### D. 证据与科学可辩护性

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| D1 | P1 | 噪声证据曾靠事后 reground；管道内过滤虽已加强，**注入/旧缓存**仍可绕过 | 六轮报告 R1–R2 |
| D2 | P1 | Gap 类型与标题/主张对齐依赖启发式；LLM off 时易出「语料局限袋」式 limitations | `gap_finder` + 关 LLM |
| D3 | P2 | Route A 未挂在 sciverse 金标上，方法创新分与文献金标脱节 | `route_a.enabled: false` |

### E. UI / 缓存 / 交付面

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| E1 | **P0** | `user_result.json` 仅在 **gaps 条数**变化时失效；标题/证据原文改写可继续返回陈旧黑盒视图 | `serve_viewer._public_from_run` |
| E2 | P1 | 黑盒/白盒两套静态根，文档链接与判决标准已补，但「何者是提交叙事权威视图」未写死 | `user/` vs `viewer/` |
| E3 | P2 | 用户 job 路径须用 `user_jobs/<id>` 全相对路径，易踩「只取最后一段」 | reviews README 已提醒 |

### F. 工程卫生与竞赛 ROI

| ID | 严重度 | 问题 | 证据落点 |
|----|--------|------|----------|
| F1 | P1 | 修补脚本与生产入口混在 `scripts/`，无 `scripts/maintenance/` 或「勿用于答辩复现」标记 | 目录结构 |
| F2 | P1 | Windows MinerU 挂死 → 永久降级 GROBID；缺「平台矩阵」与健康检查入口 | 配置注释 |
| F3 | P2 | CI 未强制三门禁；本地 PASS 不等于 PR 可复现 | 无统一 gate workflow（或未绑金标） |

---

## 4. 逐条升级清单（按执行顺序）

> 约定：每条含 **动作 / 落点 / 完成判据**。优先把能力收进 `pipeline` 与正式门禁，再淘汰一次性修补。

### U1 · 门禁文件解耦（对应 B1/B2）— P0

- **动作：** `objective_review_run` 只写 `objective_review.json`（及可选 `expert_review_pack.json`），**禁止**覆盖 `production_verification.json`。若需「类 verify」摘要，写入 `objective_verify_shadow.json`。
- **落点：** `scripts/objective_review_run.py`；更新 README「对外只引用 verify + science」纪律。
- **完成判据：** 连续跑 `verify_production` → `objective_review_run` 后，`production_verification.profile` 仍为生产验收脚本名；客观报告仍 PASS。

### U2 · Sciverse 标题与元数据在管道内完成（对应 A2）— P0

- **动作：** 注入或检索落盘时：优先 API meta title → GROBID TEI title → 才允许临时 stem；禁止把 `SV-paper_*` 当作最终 `Paper.title` 进入 gap/report。
- **落点：** `sciverse_client.py` / `build_sciverse_verify_bundle.py` / `fulltext` 解析后回填 title；单测覆盖「stem 不得进 gaps」。
- **完成判据：** 全新 sciverse 跑次 `papers.json` 无 `title.startswith("SV-paper")`；无需 `finish_sciverse_*` 修标题。

### U3 · 检索来源诚实门禁（对应 C1）— P0

- **动作：** 配置增加 `retrieval.allow_backend_fallback: false`（生产默认 false）。静默 OpenAlex 时：**硬失败**或强制 `run_name`/`audit.meta.effective_backend` 与对外 label 一致，并由 `verify_production` 检查 `effective_backend == configured_backend`（除非显式允许）。
- **落点：** `retrievers.py`、`verify_production.py`、`production_sciverse.yaml`。
- **完成判据：** 无 token 时 production_sciverse **FAIL 并写明原因**；有 token 时空结果不得假装「Sciverse 成功」。

### U4 · `user_result` 内容哈希失效（对应 E1）— P0

- **动作：** 缓存键 = `hash(gaps.json + papers.json mtimes/content + metrics)`，或任何核心字段变更即重建；去掉「仅比 gaps 条数」。
- **落点：** `scripts/serve_viewer.py` `_public_from_run`。
- **完成判据：** 只改一篇 paper title 后刷新用户端，标题立即更新。

### U5 · 金标复现剧本化（对应 A1）— P0

- **动作：** 新增 `scripts/reproduce_production_sciverse.sh|ps1`（或 `make reproduce-sciverse`）：仅调用正式入口（survey + 三门禁），**不**调用 upgrade/finish。一次性修补脚本移至 `scripts/maintenance/` 并在文件头标注 deprecated。
- **落点：** 新脚本 + 目录搬迁 + `experiments/reviews/` 指向新剧本。
- **完成判据：** 干净目录按剧本可得到 verify∩science∩objective(must) PASS（允许依赖本地 GROBID/缓存 PDF，但步骤可列清单）。

### U6 · metrics 契约锁死（对应 B3）— P1

- **动作：** `save()` 始终写完整 `compute_optimization_metrics`；禁止手工裁剪。UI/门禁读取缺字段视为 FAIL 或 degraded。
- **落点：** `pipeline.py` save、`topic_focus.py`、后写脚本删除手写 metrics。
- **完成判据：** `optimization_metrics.json` 含 `evidence_boilerplate_rate`、`provenance_coverage`、`pass_flags`（若设计有）。

### U7 · 证据噪声进 L0 硬门（对应 D1）— P1

- **动作：** `science_review_gate` / `verify_production` 对 boilerplate span **直接失败**（不仅 L1 降分）；pipeline 的 `ground_gap_evidence` 已过滤的，验收再扫一遍防回归。
- **落点：** `evidence_selector.is_boilerplate_text`、两门禁脚本、已有 `test_gap_evidence.py`。
- **完成判据：** 人为插入 Creative Commons quote → verify 或 science **必 FAIL**。

### U8 · 解析标签归一（对应 B4）— P1

- **动作：** 新解析只写 `grobid` | `mineru`；读路径把 `grobid_fusion` 映射为 `grobid` 并在 audit 记 legacy。
- **落点：** `fulltext.py`、`verify_production.py`。
- **完成判据：** 新跑次 papers 无 `grobid_fusion`；旧跑次仍能 verify。

### U9 · 文档与配置对齐（对应 A4）— P1

- **动作：** 更新 `完成度与优化方向.md` / README 硬证据快照：GROBID primary、Sciverse 六轮终态、三门禁文件名纪律。
- **落点：** 上述 md；本文件交叉链接。
- **完成判据：** 文档中的 parser / 路径与当前 yaml 一致。

### U10 · 删除或隔离死树（对应 A3/F1）— P1

- **动作：** 删除空 `src/` 或改 README「忽略」；`scripts/maintenance/` 收纳 reground/upgrade/finish/build_bundle。
- **完成判据：** 新贡献者 5 分钟能指出唯一包根与唯一复现入口。

### U11 · Sciverse profile 科学叙事补强（对应 C2/D2）— P1

- **动作：** 二选一写清：(a) sciverse 金标 = 证据链工程演示（LLM off 诚实）；(b) 另建 `production_sciverse_llm.yaml` 开 rewrite + LLM gap，用于方法分。
- **完成判据：** 提交材料中不会出现「Sciverse + LLM 发现」却指向 LLM-off 跑次。

### U12 · Route A 与文献金标挂钩（对应 D3）— P1

- **动作：** 在同一 SnSe 主题上跑一次 `production_route_a`（或 sciverse+route_a），MP 外验写入同一答辩包索引。
- **完成判据：** 答辩包同时链到 literature PASS 与 Route A 外验 PASS。

### U13 · 平台健康检查（对应 F2）— P2

- **动作：** `scripts/healthcheck.py`：GROBID ping、Qdrant ping、Sciverse token、MinerU 是否建议禁用（Windows）。
- **完成判据：** 调研前一条命令给出绿/黄/红。

### U14 · CI 最小门禁（对应 F3）— P2

- **动作：** CI 跑单测 + `demo_local` checklist；可选 nightly 对缓存跑 science L0。
- **完成判据：** PR 红灯能挡住证据回退类回归。

### U15 · 主题门禁配置化（对应 C4）— P2

- **动作：** 材料/性质 token 以 ontology 为主，硬编码表仅兜底。
- **完成判据：** 换 ontology 文件即可换主题，无需改 `topic_focus.py` 正则大表。

---

## 4.1 落地状态（2026-08-11）

| ID | 状态 | 说明 |
|----|------|------|
| U1 | **已做** | `objective_review_run` 只写 `objective_verify_shadow.json` |
| U2 | **已做** | `paper_titles` + `attach_fulltext` TEI 回填；注入不再用 stem 当最终标题 |
| U3 | **已做** | `allow_backend_fallback`；生产 sciverse/s2 默认 false；verify 查诚实性 |
| U4 | **已做** | `user_result` 用 gaps/papers/metrics 内容哈希失效 |
| U5 | **已做** | `reproduce_production_sciverse.ps1/.sh`；修补脚本迁 `scripts/maintenance/` |
| U6 | **已做** | `save()` 重算完整 metrics；`refresh_run_metrics.py`；verify 查契约键 |
| U7 | **已做** | `verify_production` 增加 `no_boilerplate_evidence`（science H5 仍为硬门） |
| U8 | **已做** | 新写入 canonical `grobid`/`mineru`；读路径映射 `grobid_fusion` |
| U9 | **已做** | README / 完成度文档与 GROBID-primary、门禁纪律对齐 |
| U10 | **已做** | 无独立 `src/` 死树；维护脚本隔离 + README 标明包根 |
| U11 | **已做** | sciverse 金标注释 LLM off；新增 `production_sciverse_llm.yaml` |
| U12 | **已做（索引）** | `defense_pack.md` 挂接已有 Route A；**未重跑** MP/LLM |
| U13 | **已做** | `scripts/healthcheck.py` |
| U14 | **已做** | `.github/workflows/materials-agent.yml`（pytest + demo checklist） |
| U15 | **已做** | ontology `property_focus` 优先，硬编码表仅兜底 |

完整重跑 survey / 点亮 LLM Route A 需要外部服务，见用户回复中的申请项。

---

## 5. 建议执行波次

| 波次 | 升级项 | 目标 |
|------|--------|------|
| **Wave 0（本周）** | U1 U2 U3 U4 | 堵住答辩时最丢人的「文件被覆盖 / 假标题 / 假 Sciverse / 假 UI」 |
| **Wave 1** | U5 U6 U7 U8 U9 U10 | 复现剧本化 + 契约锁死 + 文档一致 |
| **Wave 2** | U11 U12 U13 U14 U15 | 方法叙事、Route A、CI、泛化 |

---

## 6. 流程健康度评分（专家主观）

| 维度 | 分（/5） | 评语 |
|------|----------|------|
| 主调研流水线清晰度 | 4.5 | `pipeline.py` 顺序正确，证据强制回源 |
| 金标可复现性 | 2.5 | 依赖修补编年史 |
| 门禁诚实性 | 3.0 | 意图好，objective 覆盖 verify 是硬伤 |
| 检索来源诚实 | 2.5 | 静默 fallback 与 profile 名冲突 |
| 科学可辩护性 | 3.5 | 六轮后 PASS，但仍偏工程修补胜利 |
| UI 交付一致性 | 3.0 | 功能全，缓存失效不全 |
| 文档与现实一致性 | 3.0 | README 新、完成度文档偏旧 |
| **综合** | **3.2** | **可提交，但 Wave 0 不做会埋雷** |

---

## 7. 明确「不是问题」的项（避免误改）

- 双 UI 本身不是问题，是验收设计。
- OpenAlex 作为无 Token 时的**显式**降级可以保留，关键是不能冒充 Sciverse 成功。
- GROBID 代替 MinerU（Windows）是务实工程选择，应文档化而非强行 MinerU。
- LLM off 的 sciverse 跑次可以作为「证据链金标」，只要叙事不夸大发现能力。

---

## 8. 相关产物

- 六轮升级终态：[`expert-6rounds-20260811-production_sciverse.md`](expert-6rounds-20260811-production_sciverse.md)
- 工程地图：[`../../README.md`](../../README.md)
- 赛题完成度（待 U9 对齐）：[`../../完成度与优化方向.md`](../../完成度与优化方向.md)
- 人工核验指南：[`../../docs/人工核验_production_sciverse.md`](../../docs/人工核验_production_sciverse.md)
