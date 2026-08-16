# 人工金标准协议（Gold Gap Set）

> 目的：用**冻结的人工标签**校准自动 Gap，而不是只看自动 novelty。

## 标注字段

| 字段 | 取值 | 含义 |
|------|------|------|
| `match_key` | gap id 或标题关键词 | 与自动产出对齐 |
| `is_true_gap` | true/false | 是否真是 Research Gap |
| `correct_type` | missing_link / contradiction / underexplored / method_gap | 正确类型 |
| `evidence_ok` | true/false | 证据链是否撑得住 |
| `novelty_tier` | low / mid / high | 相对 Known 表的新颖性 |
| `actionability_ok` | true/false | next step 是否可开工 |
| `annotator` | A/B/consensus | 标注来源 |
| `notes` | 自由文本 | 争议说明 |

## 流程

1. 从 `outputs/demo/gaps.json` 或抽检轮次抽样  
2. 双人独立标注 → 分歧裁决写入 `annotator=consensus`  
3. 冻结为 `gold_set_v1.json`（≥20 条）  
4. 跑 `python scripts/score_against_gold.py` 得到准确率 / 类型一致率 / 新颖性校准误差  

## 本仓库起步集

`gold_set_v1.json` 含 20 条：以 demo 离线语料可复现 Gap 为主，并补充负例（非 Gap / 类型错）用于校准。
