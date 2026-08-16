# 科学抽检标准（AI 可执行 · 对齐科学意义 30%）

> 目标：把「科学意义」从不可操作的主观印象，落成 **AI/脚本可重复跑通、有明确 PASS/FAIL** 的门禁。  
> 适用：`verify_production` 已 PASS 的 `outputs/production`（或同结构运行目录）。  
> 执行：`py -3 scripts/science_review_gate.py -c configs/production.yaml`

---

## 0. 设计原则（为什么这样定）

| 原则 | 含义 |
|------|------|
| 可机器判定优先 | 每一项有输入文件、判定函数、阈值；不依赖「读起来像科学」 |
| 与赛题对齐 | 证据可回源、Gap 可行动/可证伪、不把常识当发现、贴题 |
| AI 能顺利完成 | **默认不强制真人**；L0+L1 规则双评即可出正式报告；LLM/真人可选加分 |
| 可达到 | 阈值按当前生产基线（贴题门禁后）标定，避免「永远 FAIL」或「永远虚高 PASS」 |

**分层：**

| 层级 | 谁执行 | 是否必须 | 产出 |
|------|--------|----------|------|
| **L0 机械科学门禁** | 纯脚本 | **必须** | 写入 `science_review.json` 的 `l0` 字段 |
| **L1 AI 双角色抽检** | 规则双评（默认） | **必须**（≥3 条） | 写入 `science_review.json` 的 `l1` 字段 |
| **L2 真人抽检** | 人 / 专家核对 UI | 可选加分 | `review-YYYYMMDD-*.md` 或专家判决导出 |

> 说明：门禁脚本一次写出 **`science_review.json`**（含 L0+L1），不再分别写 `science_review_l0.json` / `l1.json`。LLM 双评请用 `scripts/ai_human_review.py --use-llm`（可选）；`science_review_gate.py` 默认规则双评，无 `--use-llm`。

**总判定：**

```text
science_review_status = PASS
  当且仅当：L0.pass == true 且 L1.pass == true
```

`verify_production` 与 `science_review` **正交**：前者管工程证据链，后者管科学可辩护性。

---

## 1. L0 — 机械科学门禁（全量 Gap，必须 100% 过硬项）

对 `gaps.json` **全部**条目逐条检查；任一条硬项失败 → L0 FAIL。

### 1.1 硬项（任一失败即拒收该 Gap，并计 L0 失败）

| ID | 检查项 | 判定（AI 实现） | 阈值 |
|----|--------|-----------------|------|
| H1 | 证据非空 | `len(evidence_chain) ≥ 1` | ≥1 |
| H2 | 全文定位 | 每条 span：`location ∈ {fulltext, chunk}` | 100% |
| H3 | provenance 完整 | `pdf_hash` 与 `chunk_id` 均非空 | 100% |
| H4 | quote⊂chunk | `quote_or_basis` 为对应 `evidence_chunks` 文本子串（允许空白/换行折叠） | 每条 span 通过 |
| H5 | 非噪声 | `is_boilerplate_text(quote)=false` | 100% |
| H6 | 可行动+可证伪 | `suggested_next_step`≥20 字且 `falsification_test`≥20 字；且不含纯「need more research」 | 每条 Gap |
| H7 | 类型合法 | `gap_type ∈ {missing_link, contradiction, underexplored, method_gap}` | 每条 |
| H8 | contradiction 结构 | 若 type=contradiction：`supporting` 与 `contradicting` 均非空且集合不相交 | 每条 contradiction |

### 1.2 软项（计入分数，允许少量失败但有整体阈值）

| ID | 检查项 | 判定 | 达标线 |
|----|--------|------|--------|
| S1 | 主题材料对齐 | Gap 标题/描述/id 含 topic 材料，或 id∈{gap-limitations, gap-method-balance, gap-missing-link*} | **≥80%** Gap |
| S2 | 主题性质线索 | quote 或 title/description 命中 topic 性质词（vacancy/lattice/thermal/…）至少 1 个 | **≥60%** Gap |
| S3 | 主张–摘录重叠 | Gap title 实词（长度>3）与任一条 quote 的 token Jaccard ≥0.08，或 title 关键词命中 quote | **≥60%** Gap |
| S4 | 行动力下界 | `actionability ≥ 0.35` | **100%**（与 quality 配置对齐） |

### 1.3 L0 总判定

```text
L0.pass =
  (全部 Gap 的 H1–H8 通过)
  AND (S1 ≥ 0.80) AND (S2 ≥ 0.60) AND (S3 ≥ 0.60) AND (S4 == 1.0)
```

---

## 2. L1 — AI 双角色抽检（分层抽样 ≥3）

### 2.1 抽样

- 样本量 `n = min(5, 全部 Gap 数)`，且 **n ≥ 3**（Gap 总数 <3 时抽全部，但报告标 `sample_warning`）。
- 分层：优先覆盖 `contradiction` / `underexplored` / `missing_link` / `method_gap`（round-robin）。
- 固定 `seed`（默认 42）保证可复现。

### 2.2 五维量表（每维 0/1/2）

与 `scripts/ai_human_review.py` 一致，便于复用：

| 维度 | 含义 | AI 可判定要点 |
|------|------|----------------|
| evidence_fit | 证据是否支撑主张 | quote 长度、provenance、非噪声（接 L0） |
| falsifiability | 能否证伪 | next_step + falsification 质量 |
| type_purity | 类型是否名实相符 | contradiction 必须双边论文 |
| novelty_honesty | 是否诚实对待 known | overlaps_known 时 novelty 不得虚高 |
| non_overclaim | 是否过宣称 | 禁 discover/首次证明/paradigm 等 |

### 2.3 角色与裁决

| 角色 | 默认实现 | 可选 |
|------|----------|------|
| Reviewer A（严谨） | 规则 `_rule_score_A` | 见 `ai_human_review.py --use-llm` |
| Reviewer B（怀疑） | 规则 `_rule_score_B` | 见 `ai_human_review.py --use-llm` |
| 裁决 | 逐维 `min(A,B)`（偏保守） | — |

单条决策：

| 条件 | 决策 |
|------|------|
| `evidence_fit` / `falsifiability` / `type_purity` 任维=0，或总分≤3 | `reject` |
| `novelty_honesty` / `non_overclaim` =0，或总分≤5 | `revise`（诚实性软失败，不直接否决） |
| 否则 | `keep` |

> 说明：corpus 内 `missing_link` 常 `overlaps_known`，怀疑派会压低 novelty_honesty；若因此一律 reject，门禁将不可达。软失败→`revise` 既保留压力又保证 AI 默认可 PASS。

### 2.4 L1 总判定（可达到、对齐需求）

```text
L1.pass =
  (抽样条数 ≥ 3 或 gaps_total < 3)
  AND (reject 条数 == 0)
  AND (keep 条数 ≥ ceil(2n/3))   # 等价 keep_rate ≥ 2/3；n=3 时 keep≥2
```

含义：允许 ≤1/3 为 `revise`（报告写改进点），**不允许 reject**；多数须 `keep`。

> 说明：规则双评在「证据链已 L0 通过」时通常可达；若 L1 FAIL，优先修 Gap 生成/证据选择，而不是先上真人。

---

## 3. L2 — 真人抽检（可选加分，非门禁）

仅当需要答辩「有人看过」时：

- 从 L1 样本中抽 **≥1** 条 `keep`，用原模板做 quote 肉眼确认。
- 不改变 `science_review_status`；写入 `review-*-human.md` 作为加分材料。

---

## 4. 与赛题「科学意义」的映射

| 评审关心点 | 本标准落点 |
|------------|------------|
| 缺口是否有文献依据 | H1–H5、L1 evidence_fit |
| 是否可行动/可检验 | H6、L1 falsifiability |
| 是否胡吹/把常识当新发现 | H8、S1、L1 novelty_honesty / non_overclaim |
| 是否贴题（SnSe 空位导热） | S1–S2 |
| 可复现抽检过程 | 固定 seed + JSON 报告入库 |

---

## 5. 命令与产物

```bash
cd tracks/algorithm/materials_agent
# 正式门禁（规则双评，无 --use-llm）
py -3 scripts/science_review_gate.py -c configs/production.yaml --run outputs/production

# 可选：额外 LLM 人工风格抽检（不替代 science_review_gate）
py -3 scripts/ai_human_review.py -c configs/production.yaml --gaps outputs/production/gaps.json --use-llm
```

| 产物 | 说明 |
|------|------|
| `outputs/<run>/science_review.json` | 总判定 + L0/L1 摘要 |
| `experiments/reviews/science-review-YYYYMMDD-<run>.md` | 可读归档（自动生成） |

**提交口径一句话：**

```text
science_review=PASS | L0 hard=all | S1–S4 ok | L1 keep≥2/3 reject=0 | seed=42
```

---

## 6. 明确不做的（避免 AI 无法稳定完成）

| 不做 | 原因 |
|------|------|
| 要求 AI「判断物理机制是否正确」到专家级 | 无稳定 ground truth，易幻觉 |
| 强制双人真人签字才算 PASS | 阻塞自动化；改为 L2 加分 |
| 金标准 accuracy 作为本门禁硬条件 | coverage 仍可另跑 `score_against_gold.py`，与本标准解耦 |

金标准 coverage 作为 **平行指标**（目标建议 ≥0.5 后再报），不阻塞 `science_review_status`。
