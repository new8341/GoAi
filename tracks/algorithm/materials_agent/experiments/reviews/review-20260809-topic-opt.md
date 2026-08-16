# 专项优化重跑报告 2026-08-09

Reviewer: Auto  
Config: `configs/production.yaml`（贴题门禁 + GROBID 优先）  
Run: `outputs/production`  
用户端: http://127.0.0.1:8765/ → **production**  
调试端: http://127.0.0.1:8765/debug/?run=production  

`production_verification`: **PASS** · Consistency: **PASS**

---

## 1. 本轮专项优化（相对上一轮偏题）

| 问题 | 改动 |
|------|------|
| Bi₂Te₃/GeTe 冲榜 | `score_relevance` 主题材料门禁：未点名 topic 材料大幅降权；够多 hit 时只保留 hit |
| `gap-temporal-PbTe/GeTe` | 仅对 topic 材料生成 temporal；reviewer 拒收 off-topic contradiction/conflict |
| 缺优化反馈 | 新增 `optimization_metrics` + `optimization_metrics.json`，双端展示 |
| MinerU Windows 挂死 | `production.yaml` primary → **grobid** |

监控点目标：贴题≥70%、Gap对齐≥80%、噪声≤5%、溯源≥95%。

---

## 2. 监控点结果（本轮）

| 监控点 | 本轮 | 目标 | 判定 |
|--------|------|------|------|
| topic_hit_rate | **100%** (10/10) | ≥70% | PASS |
| property_hit_rate | **100%** | — | 参考 |
| gap_material_alignment | **100%** (3/3) | ≥80% | PASS |
| evidence_boilerplate_rate | **0%** | ≤5% | PASS |
| provenance_coverage | **100%** (12/12) | ≥95% | PASS |
| extraction_topic_rate | 90% | — | 参考 |

对比上一轮（人工核验）：贴题弱、含 PbTe/GeTe temporal、Bi₂Te₃ conflict → **本轮四项监控全绿**。

---

## 3. 双端状态

### 用户端 `/`
- 摘要：10 文献 / 3 Gap / 8 全文 / 一致性通过
- 新增监控条：贴题 / Gap对齐 / 噪声 / 溯源（均达标）
- Gaps：仅 `missing-link`、`limitations`、`temporal-SnSe`（无 PbTe/GeTe）

### 调试端 `/debug/?run=production`
- verify **PASS**（parsed 8/10）
- 总览「优化监控点」四项 pass
- retrieve audit：`topic_hit_rate=1.0`，top_scores 带 `topic_hit`
- 文献标题主体为 **SnSe** 多晶 / vacancy / 导热（仍可能有 1 篇 SnS 对比文，摘要里可点名 SnSe）

---

## 4. 终端跑程笔记（运维）

1. 首次重跑卡在 MinerU `fast_api` → 已杀进程并改 GROBID。  
2. 必须 `PYTHONPATH=.../materials_agent`，避免 site-packages 旧包遮挡。  
3. 全文 10/10 后 LLM 阶段可静默 15–30 分钟，属正常。

---

## 5. 总评与下一方向

| 维度 | 结论 |
|------|------|
| 自动门禁 + 监控点 | **符合** |
| 贴题检索 / Gap 收敛 | **明显达标（相对上轮）** |
| 科学主张细粒度（limitation quote 是否最优） | 仍可继续抽检，但已不是偏题级问题 |

**建议下一监控/优化方向（若继续冲分）：**
1. 标题硬过滤：拒绝 `SnS`/`Bi2Te3` 主标题（即使摘要提到 SnSe）。  
2. `gap-limitations` 强制 quote 与 SnSe limitation 句对齐率监控。  
3. 检索阶段打印 `rejected_offtopic_count` 到 audit，便于调 `min_relevance`。

```text
run=production | verify=PASS | topic_hit=1.0 | gap_align=1.0 |
boilerplate=0.0 | provenance=1.0 | gaps=3 (SnSe-only temporal) | parser=grobid
```
