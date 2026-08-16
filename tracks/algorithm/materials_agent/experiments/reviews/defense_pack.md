# 答辩包索引（文献金标 ∩ Route A）

> 更新日期：2026-08-11  
> 目的：同一 SnSe 主题下，把文献证据链与构效搜索外验挂到同一入口（U12）

## 权威视图

| 角色 | URL / 路径 | 用途 |
|------|------------|------|
| **提交叙事（黑盒）** | http://127.0.0.1:8765/?run=production_sciverse | 用户可见结论与证据摘录 |
| 工程师白盒 | http://127.0.0.1:8765/debug/?run=production_sciverse | audit / provenance / 门禁 |
| Route A 白盒 | http://127.0.0.1:8765/debug/?run=production_route_a | SPR 候选与 MP 外验 |

黑盒是对外讲述权威视图；白盒只用于排障，二者不得互相冒充。

## 文献金标（LLM off，证据链）

| 项 | 路径 |
|----|------|
| Profile | `configs/production_sciverse.yaml` |
| 复现剧本 | `scripts/reproduce_production_sciverse.ps1` |
| 产物 | `outputs/production_sciverse/` |
| 工程验收 | `outputs/production_sciverse/production_verification.json` |
| 科学门禁 | `outputs/production_sciverse/science_review.json` |
| 客观专家包 | `outputs/production_sciverse/objective_review.json` |

叙事：**不要**把该跑次说成「Sciverse + LLM 发现」。LLM 版配置是 `configs/production_sciverse_llm.yaml`（独立目录 `outputs/production_sciverse_llm`）。2026-08-11 已跑通三门禁 PASS，但 `llm_rewrite` 为 `RateLimitError`，查询仍走启发式——**不可当作 LLM 发现材料**。

## Route A（同一主题，MP 外验）

| 项 | 路径 |
|----|------|
| Profile | `configs/production_route_a.yaml` |
| 产物 | `outputs/production_route_a/` |
| 摘要 | `outputs/production_route_a/route_a_run_summary.json` |
| 外验 | `outputs/production_route_a/route_a_external_validation.json` |
| 报告 | `outputs/production_route_a/route_a_spr_report.md` |

2026-08-12：Minimax（国内 `api.minimaxi.com`）已打通。`production_sciverse_llm` 三门禁 PASS，audit 含 `llm_rewrite/extract/gap/review/report=finished`。Route A 见 `outputs/production_route_a_minimax`（LLM 角色齐全；本轮 MP 外验返回 error，需核 MP Key/网络）。

建议答辩命令（文献已存在时只挂 Route A）：

```bash
py scripts/run_route_a.py -c configs/production_route_a.yaml --bundle-dir outputs/production_sciverse
```

（将 SPR 候选写入 sciverse 跑次目录，便于黑盒同一 `run=` 展示。默认仍保留独立 `outputs/production_route_a/`。）

## 三分法纪律

1. `production_verification.json` **只**由 `verify_production.py` 写入。  
2. `objective_review_run.py` 只写 `objective_review.json` + `objective_verify_shadow.json`。  
3. 对外同时引用：工程 verify ∩ science ∩（可选）objective must，外加 Route A 外验摘要。
