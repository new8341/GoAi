# 开源计划与边界（初赛可用）

## 计划开源范围

- **公开仓库 URL：** https://github.com/new8341/GoAi

## 目标许可证

- Apache-2.0（拟，需确认与上游依赖兼容）

## 复现入口（复赛起完善）

- 环境安装：`pip install -r tracks/algorithm/materials_agent/requirements.txt`
- 运行入口：`python scripts/run_survey.py survey -c configs/demo_local.yaml`
- 配置与随机种子：`configs/*.yaml` 中 `route_a.seed`
- 预期输出：`outputs/` 下 `report.md`、`gaps.json`、`audit.json`
