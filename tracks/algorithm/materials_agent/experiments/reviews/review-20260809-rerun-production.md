# Gap / 生产轮人工核验报告 2026-08-09（重跑后）

Reviewer: Auto（用户端 + 调试端）  
Config: `configs/production.yaml`  
Run: `outputs/production`  
UI: http://127.0.0.1:8765/ → 打开已有运行 **production ★**  
Debug: http://127.0.0.1:8765/debug/?run=production  

`production_verification`: **PASS**

---

## 0. 本轮做了什么

1. 修复 LLM 把 `confidence/novelty/actionability` 写成 `high/low` 导致的崩溃（`parse_confidence`）。
2. 完整重跑 `production.yaml`（OpenAlex + LLM，约 27 分钟）成功落盘。
3. 首次 verify 因 `gap-limitations` 缺 provenance **FAIL**；加固证据选择器后离线重接地 `gaps.json`，verify → **PASS**。
4. 对照 `docs/人工核验_production_sciverse.md` 口径（黑盒+白盒）做人工抽检。

---

## 1. 用户端（黑盒）核验

| 检查 | 结果 | 判定 |
|------|------|------|
| 文献数 ≥5 | 10 | 通过 |
| Gap ≥1 | 6 | 通过 |
| 含全文 | 7/10 | 通过 |
| 一致性 UI 摘要 | `consistency_ok=true`（摘要字段） | 见 §2 |
| 报告/面板可打开 | `/api/runs/production/public` 200 | 通过 |
| verify 星标 | `verify_status=PASS` | 通过 |

### 1.1 文献贴题性（人工）

主题是 **SnSe lattice thermal conductivity vacancy engineering**，本轮 Top 文献却大量是：

- Bi₂Te₃ 综述（W3108444599）
- SnS（W2996304641 / W2914712880）
- GeTe 缺陷结构（W4306179630 / W2783223402）
- 通用 TE 策略 / XTe monolayers

**结论：检索相关性偏题** —— 自动门禁不检查“是否真是 SnSe 空位 κ_L”，科学叙事偏弱。

### 1.2 Gap 抽检（≥3）

| gap_id | type | quote⊂chunk | boilerplate | 主张是否贴题 | 判定 |
|--------|------|-------------|-------------|--------------|------|
| gap-limitations | underexplored | yes（4/4） | 0 | 弱：证据多落在 Bi₂Te₃/通用 TE，非 SnSe 局限簇 | **revise** |
| gap-temporal-SnSe | contradiction | yes | 0 | 弱：支撑片段含 GeTe 文；未形成可核对的 SnSe 跨年冲突表 | **revise** |
| gap-conflict-W3108444599 | underexplored | yes | 0 | 弱：冲突锚定在 Bi₂Te₃ 文，偏离赛题主材料 | **revise** |
| gap-missing-link-topic | missing_link | yes | 0 | 中：点名 SnSe–Seebeck 覆盖缺口，但证据片段泛化 | **conditional** |
| gap-temporal-PbTe / GeTe | contradiction | yes | 0 | 偏离主 topic 材料 | **reject for submission narrative** |

**证据过滤改进有效**：本轮未见 Creative Commons / Peer review 噪声（相对上一轮 sciverse）。

---

## 2. 调试端（白盒）核验

| 检查 | 结果 | 判定 |
|------|------|------|
| `production_verification.json` | PASS：papers=10，parsed=7/10，fulltext spans=24，verifiable ok | 通过 |
| Audit `retrieve/openalex` | `10 papers after rank/filter (raw=180)` | 通过（非 Sciverse） |
| Audit `evidence_retrieve`（原跑） | `fulltext=6 rejected=4` | 说明门禁在工作 |
| `fulltext_source` | parser-derived（非 local_cache） | 通过 |
| Gap provenance | 重接地后 6×4 均有 `pdf_hash`+`chunk_id` | 通过（机械） |
| `consistency.json` | 重跑前曾报 `gap_evidence_missing_provenance`；与 verify 不同步风险 | 需保持与 gaps 同步刷新 |

Debug URL 建议人工再点开：Gaps / Papers / Audit 三页对照。

---

## 3. 是否符合要求（总评）

| 维度 | 结论 |
|------|------|
| 工程可复现 / 自动生产门禁 | **符合**（PASS） |
| 证据可回源（quote∈全文 + provenance） | **符合**（机械） |
| 噪声过滤（license/参考文献） | **明显改善** |
| 科学意义 / 贴题 / 可行动 Gap（竞赛抽检口径） | **仍不符合冲分终稿** |
| 文献库叙事 | 本轮是 **OpenAlex production**，不是 Sciverse ★ 轮 |

**一句话**：可以展示「管线跑通 + verify PASS + 证据可追溯」；不宜声称「已完成高质量 SnSe 空位导热空白发现」。

```text
run=production | backend=openalex | verify=PASS |
gaps_reviewed=3+ | quote_ok=mechanical PASS | claim_align=weak |
topic_drift=Bi2Te3/SnS/GeTe heavy | notes=rerun+reground after parse_confidence+evidence filter
```

---

## 4. 建议下一步

1. 收紧检索：提高 SnSe / vacancy / κ_L 权重，降权 Bi₂Te₃/GeTe 综述噪声。  
2. 对 `gap-temporal-*` 非主题材料默认不进入提交叙事。  
3. `gap-limitations` 强制 quote 与 limitation 抽取句对齐（已部分实现，需在偏题语料上再验）。  
4. 若要 Sciverse 叙事：在 Token 可用时另跑 `production_sciverse`（`max_papers` 已调到 5）并单独核验。  
5. 正式人工档：本文件即可作为 `experiments/reviews/` 抽检留档。
