# 复赛最短复现（评委 / 组委会核验）

工作目录：`tracks/algorithm/materials_agent`

## 0. Profile 三分法（禁止混说）

| Profile / 目录 | 含义 |
|----------------|------|
| `configs/demo_local.yaml` | 离线 smoke，无密钥 |
| `outputs/production_sciverse` | **LLM-off** 文献证据链金标 |
| `outputs/production_route_a`（或 `*_minimax`） | Route A + MP；可含 LLM 角色 |

## 1. 依赖与服务

```powershell
pip install -r requirements.txt
copy .env.example .env   # 填入 SCIVERSE / OPENALEX / UNPAYWALL / MP / OPENAI*
docker compose up -d grobid qdrant
# 镜像已钉：grobid/grobid:0.8.0 ，qdrant/qdrant:v1.13.2
```

## 2. 金标证据链（LLM off）

```powershell
powershell -File scripts/reproduce_production_sciverse.ps1
# 或：
py -3 scripts/verify_production.py -c configs/production_sciverse.yaml
py -3 scripts/science_review_gate.py -c configs/production_sciverse.yaml
py -3 scripts/export_survey_latex.py outputs/production_sciverse
py -3 scripts/dump_external_versions.py -c configs/production_sciverse.yaml
```

期望：`production_verification.json` status=PASS；`report.pdf`+`.tex`+`.bib` 存在。

## 3. Route A（同 seed=42）

```powershell
# 规则-only 消融
py -3 scripts/ablate_route_a.py --bundle-dir outputs/production_sciverse --seed 42

# 或单独 LLM-on（需可用的 OPENAI_*）
py -3 scripts/run_route_a.py -c configs/production_route_a.yaml --bundle-dir outputs/production_sciverse --out outputs/production_route_a
```

期望：`route_a_run_summary.json` 含 `external_providers`；消融报告见 `submissions/semi_final/ablation_route_a.md`。

## 4. 黑盒验收 UI

```powershell
py -3 scripts/serve_viewer.py
# http://127.0.0.1:8765/?run=production_sciverse
```

## 5. 稳定度（可选工程分）

```powershell
py -3 scripts/run_stability.py -c configs/demo_local.yaml --seeds 41,42,43
```
