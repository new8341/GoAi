# 复赛提交清单 · 算法赛 · 方向三 · 队伍「和昆仑」

> 依据：`document/AI_for_reserach0816.md`；截止 ~2026-09-03（以官网为准）  
> 命名：`AI4R_ALG_MAT_和昆仑.zip`  
> 卡点文档：[`SUPPORT_NEEDED.md`](SUPPORT_NEEDED.md)（三项主卡点已完成）

## 手册必交

- [x] 可运行代码仓库 + `REPRODUCE.md`
- [x] 实验结果 + 科学意义 + 依赖披露
- [x] 基本任务 PDF+LaTeX + 系统说明
- [x] Sci-Base 接入（`production_sciverse_scibase` verify PASS）
- [x] 路线 A 解释文档 + 构效/外验产物
- [x] 引用自查 `citation_audit.md`
- [x] 技术报告草稿 + 一页纸预稿 + LICENSE(Apache-2.0)
- [x] Dockerfile + MCP 说明文档
- [x] **完整 hybrid 金标重跑**
- [x] **L2 真人签字 ≥3** → `l2-signed-20260816-production_sciverse_scibase.md`（4/4 同意）
- [x] **公开仓库 URL** → https://github.com/new8341/GoAi

## 冲分

- [x] GA 叙事 + LLM 消融
- [x] MP + OQMD 双库外验
- [x] MinerU/GROBID 披露口径
- [x] L2 真人抽检归档
- [ ] coverage≥0.5（可选扩标；当前≈0.30 不作主宣传）
- [ ] Sciverse 官方 MCP（可选；REST 已合规）

## 重新打包

```powershell
cd submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1 -SemiFinal
```
