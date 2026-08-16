# 金标准 coverage 口径（复赛）

## 平行指标（非 production 门禁）

| 集 | 结果 | 说明 |
|----|------|------|
| `experiments/gold_gaps/gold_set_v1.json` × demo 跑次 | coverage≈**0.30**（6/20） | 见历史 `outputs/demo/gold_score.json` |
| matched 子集 type_accuracy | 可高 | **coverage&lt;0.5 时不作为主成绩宣传** |

正式门禁仍以：

`verify_production` ∩ `science_review` ∩ `objective(must)` = PASS

为准（`production_sciverse` 已满足）。

## 复赛动作

1. 扩标 gold_set（对齐 SnSe κ_L vacancy 主题）或缩小声称范围到「已匹配子集」。  
2. 仅当 coverage≥0.5 后再并列汇报 type_accuracy。  
3. 扩标完成前，对外材料统一引用本节口径，避免虚高。

命令：

```powershell
py -3 scripts/score_against_gold.py --gaps outputs/production_sciverse/gaps.json --gold experiments/gold_gaps/gold_set_v1.json
```
