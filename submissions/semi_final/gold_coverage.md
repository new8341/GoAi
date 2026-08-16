# 金标准 coverage 口径（复赛）

## 现行主集（hybrid · 可宣传）

| 集 | 跑次 | coverage | type_accuracy | 说明 |
|----|------|----------|---------------|------|
| **`gold_set_v2_hybrid.json`** | `production_sciverse_scibase` | **0.667** | **1.0** | L2 签字 Gap + 关键词别名；负例无泄漏 |
| `gold_set_v1.json` | demo / 历史 | ≈0.30 | — | 离线 demo 起步集；**不再作主宣传** |

命令：

```powershell
cd tracks\algorithm\materials_agent
py -3 scripts/score_against_gold.py `
  --gaps outputs/production_sciverse_scibase/gaps.json `
  --gold experiments/gold_gaps/gold_set_v2_hybrid.json `
  --out outputs/production_sciverse_scibase/gold_score.json
```

产物副本：`submissions/semi_final/gold_score_hybrid.md`（打包时一并带上）。

## 门禁关系

正式工程门禁仍以：

`verify_production` ∩ `science_review` ∩ `objective(must)` = PASS

为准。coverage≥0.5 后可**并列**汇报 type_accuracy（本跑次 type_accuracy=1.0）。

## 标注来源

v2 正例对齐 `l2-signed-20260816-production_sciverse_scibase.md`（Lee · 2026-08-16 · 4/4 同意）。
