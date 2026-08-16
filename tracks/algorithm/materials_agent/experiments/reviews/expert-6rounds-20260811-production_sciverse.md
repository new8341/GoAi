# 专家级自动核验 · 6 轮升级报告（production_sciverse）

> 日期：2026-08-11  
> 运行目录：`outputs/production_sciverse`  
> 主题：SnSe lattice thermal conductivity vacancy engineering  
> 标准：[`专家级真人核对标准.md`](专家级真人核对标准.md) + [`科学抽检标准_AI可执行.md`](科学抽检标准_AI可执行.md)  
> 执行方式：自动专家级（L0/L1 科学门禁 + objective 专家包判决），按轮次缺陷升级产物与代码

---

## 总览

| 轮次 | 动作 | verify | science | objective must | 关键升级 |
|------|------|--------|---------|----------------|----------|
| R1 | 基线核验 | PASS | **FAIL**（H5 噪声×2 Gap） | **FAIL**（E4/P1/G2/N1…） | 建立缺陷清单 |
| R2 | 证据重接地 `reground` | PASS | （待复测） | （待复测） | 噪声证据 4→0 |
| R3–4 | 标题修复 + Gap 消毒 | PASS | **PASS** | FAIL（假标题/偏题文） | 主题对齐 limitations；弱化 overclaim |
| R5 | 恢复 temporal + TEI 标题 + 代码升级 | PASS | **PASS** | FAIL（GeTe 偏题文 P1） | L1 噪声计分；temporal 措辞；缓存一致性 |
| R6 | 剔除偏题文 + metrics + 终检 | **PASS** | **PASS** | **PASS** | `optimization_metrics`；报告同步 |

**终态（R6）：**

```text
verify_production = PASS
science_review    = PASS | L0_hard_fail=0 | L1 keep=2/2
objective must    = PASS | must_fail=[]
papers=4 · gaps=2 · fulltext=3/4 · topic_hit_rate=1.0 · gap_material_alignment=1.0
```

产物：

- `outputs/production_sciverse/science_review.json`
- `outputs/production_sciverse/objective_review.json`
- `outputs/production_sciverse/expert_review_pack.json`（objective 运行时写出）
- `experiments/reviews/science-review-2026-08-10-production_sciverse.md`
- `experiments/reviews/review-20260810-objective-production_sciverse.md`

---

## Round 1 · 基线专家核验（发现问题）

### 1.1 科学门禁 L0

| Gap | hard_ok | 问题 |
|-----|---------|------|
| `gap-limitations` | FAIL | H5：3 条 Creative Commons / Correspondence 噪声 |
| `gap-temporal-SnSe` | FAIL | H5：1 条 Data availability 噪声 |

`science_review=FAIL | L0_hard_fail=2`

### 1.2 Objective / 专家包 must 失败（摘录）

| 标准 | 对象 | 失败信号 |
|------|------|----------|
| E4 | limitations 证据 ×3 | boilerplate=True（许可协议/通讯） |
| E4 | temporal 证据 ×1 | Data availability |
| P1 | 3 篇注入文献 | 标题为 `SV-paper 10.…`，无法判定 SnSe 贴题 |
| G2 | gap-limitations | 标题未点名 SnSe |
| N1 | gap-temporal-SnSe | overclaim 词表（discovery/paradigm 类） |

### 1.3 意义

工程 verify 已 PASS，但**科学可辩护性未过**：证据链含出版商页脚噪声，Gap 主张与摘录语义脱节。

---

## Round 2 · 升级：证据重接地

```bash
py scripts/reground_production_gaps.py --run-dir outputs/production_sciverse --write
```

| Gap | before | after |
|-----|--------|-------|
| limitations | evid=4 noise=3 | evid=4 noise=**0**（替换为 ZT/crystal-growth 等正文 limitation） |
| temporal | evid=4 noise=1 | evid=4 noise=**0** |

备份：`gaps.json.20260810T232541Z.bak`

**升级点：** 复用 `ground_gap_evidence` + `is_boilerplate_text`，避免许可协议冒充科学证据。

---

## Round 3–4 · 升级：标题与 Gap 叙事消毒

脚本：`scripts/upgrade_sciverse_expert_rounds.py`

| 动作 | 结果 |
|------|------|
| 过滤剩余 boilerplate span | limitations 保留；temporal 一度被误丢（见 R5 恢复） |
| limitations 标题/描述对齐 SnSe | `Open SnSe limitations…` |
| temporal 降 novelty、弱化 discovery 措辞 | 降低 N1 风险 |
| 复测 science | **PASS**（L0_hard_fail=0） |
| 复测 objective | 仍 FAIL：注入论文标题未修好 + GeTe 偏题 |

**教训：** 仅消毒 Gap 不够；语料层 P1（贴题标题）必须修。

---

## Round 5 · 升级：TEI 标题、恢复 temporal、代码硬化

脚本：`scripts/finish_sciverse_expert_rounds.py` + 代码改动。

### 5.1 产物修复

| 项 | 结果 |
|----|------|
| 从 GROBID TEI 抽标题 | 3 篇 `SV-paper…` → 真实题名（含 SnSe / lattice κ） |
| 恢复 temporal Gap | evid=3（去掉 Data availability） |
| 重写 `report.md` | 与 gaps.json 标题一致（修 X2） |
| 刷新 `user_result.json` | 删除陈旧缓存后重建 |

### 5.2 代码升级（防复发）

| 文件 | 升级 |
|------|------|
| `scripts/ai_human_review.py` | L1 `evidence_fit`：存在 boilerplate → 降为 0/1，避免「H5 FAIL 仍 keep」 |
| `materials_agent/agents/gap_finder.py` | temporal 文案去掉 `paradigm shift` / discovery 口吻，改为 corpus-scoped candidate |
| `scripts/serve_viewer.py` | `_public_from_run`：`user_result` 与 `gaps.json` 条数不一致时强制重建 |

### 5.3 复测

- science：**PASS**（keep=2/2）
- objective：仍余 **P1** 于 GeTe 文（标题已是 GeTe，非 SnSe）— 属正确拒收

---

## Round 6 · 升级：语料净化 + 贴题 metrics + 终检

| 动作 | 结果 |
|------|------|
| 删除未支撑 Gap 的偏题 GeTe 文献 | papers 5→**4** |
| 写入 `optimization_metrics.json` | topic_hit_rate=**1.0**，gap_material_alignment=**1.0** |
| `verify_production` | **PASS**（parsed=3/4，fulltext spans=7） |
| `science_review_gate` | **PASS** |
| `objective_review_run` | **PASS**（must_fail=[]） |

### 6.1 终态 Gap（可答辩摘要）

1. **Open SnSe limitations…**（underexplored）  
   - 证据：室温 ZT 仍偏低、晶体生长约束等正文 limitation（非许可协议）  
   - 可行动 / 可证伪字段保留  

2. **Candidate temporal tension for SnSe…（corpus-scoped）**（contradiction）  
   - 证据：非 boilerplate 的跨年语料片段  
   - 措辞限定 screened corpus，避免过宣称  

### 6.2 残余非 must 项

- objective `fail_samples` 中可能仍有 R4 软提示或 D* `unsure`（领域主观项，无自动 ground truth）  
- 全文率 3/4：Zenodo 条目无解析全文，可接受于阈值 0.5 以上  
- 建议后续：Sciverse 注入论文时**默认从 TEI/元数据写 title**，避免再出现 `SV-paper` 占位标题  

---

## 升级清单（代码 / 脚本 / 产物）

### 新增脚本

- `scripts/upgrade_sciverse_expert_rounds.py` — R3–4 消毒  
- `scripts/finish_sciverse_expert_rounds.py` — R5 恢复与 TEI 标题  

### 修改代码

- `scripts/ai_human_review.py` — boilerplate 影响 evidence_fit  
- `materials_agent/agents/gap_finder.py` — temporal 候选措辞  
- `scripts/serve_viewer.py` — user_result 缓存失效条件  

### 维护流程（可复现）

```bash
cd tracks/algorithm/materials_agent
py scripts/reground_production_gaps.py --run-dir outputs/production_sciverse --write
py scripts/finish_sciverse_expert_rounds.py
py scripts/verify_production.py -c configs/production_sciverse.yaml
py scripts/science_review_gate.py -c configs/production_sciverse.yaml --run outputs/production_sciverse
py scripts/objective_review_run.py --run outputs/production_sciverse
```

---

## 结论

六轮自动专家核验把 `production_sciverse` 从「工程 PASS / 科学 FAIL」推进到：

**verify ∩ science ∩ objective(must) = PASS**

核心收益：

1. 噪声证据被重接地与门禁双重堵住  
2. 假标题 / 偏题语料被清出答辩面  
3. Gap 叙事与主题、过宣称风险对齐  
4. L1 规则与 UI 缓存不再掩盖 H5 类硬伤  

真人 L2 仍可选：在用户端/调试端「专家核对」页对 D1–D3 做领域 sanity 签名即可加分。
