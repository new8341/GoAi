# 复赛实验结果汇总 · 和昆仑

## 1. 基本任务（production_sciverse，LLM-off）

| 指标 | 值 |
|------|-----|
| verify / science / objective(must) | PASS |
| papers / parsed fulltext | 5 / 3（见 `oa_parse_audit.md`） |
| gaps（全文证据） | 3；Database 标注 6/6 spans |
| 报告 | `report.pdf` + `.tex` + `.bib` |

## 2. Route A 消融（seed=42，同一 bundle）

见 [`ablation_route_a.md`](ablation_route_a.md)。

| | Rule-only | LLM-on |
|--|-----------|--------|
| candidates | 12 | 12 |
| llm_score_unavailable | false | **false** |
| MP Top-K | pass×4 + error×1 | **pass×5** |

## 3. 稳定度（demo_local，seeds 41/42/43）

来源：`outputs/stability_demo/stability_summary.json`

| 指标 | mean ± std |
|------|------------|
| n_gaps | 3.0 ± 0.0 |
| gap_fulltext_ratio | 1.0 ± 0.0 |
| quote_in_source_ratio | **1.0 ± 0.0** |
| route_a_top_score | 0.557 ± 0.013 |

## 4. 科学意义

见 [`science_significance.md`](science_significance.md)；L2 正式归档：`experiments/reviews/l2-signed-20260816-production_sciverse_scibase.md`（Lee · 2026-08-16 · 4/4 同意）。

## 5. 金标准口径

见 [`gold_coverage.md`](gold_coverage.md)（coverage≈0.30 时不主推 type_accuracy）。
