# 初赛提交清单

## 已选定：算法赛 · 方向三（材料文献 Agent）· 队伍「和昆仑」

### 材料齐备

- [x] 方案说明 → `01_方案说明_材料文献Agent.md`
- [x] 技术路线 → `02_技术路线概述.md`
- [x] 可行性摘要 → `03_可行性与证据摘要.md`（三分法 + 规则/LLM/MP + 金标准口径）
- [x] 开源边界 → `04_开源计划与边界.md`
- [x] 合订入口 → `SUBMIT_合订入口.md`
- [x] 上传说明 → `README_提交说明.md`
- [x] 调研报告 PDF + LaTeX + bib + `external_versions.json`
- [x] 脱敏源代码（种子/参数在 YAML）
- [x] **官方主包** → `../packages/AI4R_ALG_MAT_和昆仑.zip`

### 上传前人工确认

- [x] 打开 https://goaihz.com ，赛道三 · 算法赛 · 材料方向
- [x] 上传文件名为 **`AI4R_ALG_MAT_和昆仑.zip`**（勿改名）
- [x] 确认包内无 `.env` / Token / 付费墙 PDF
- [x] 提交成功页截图存档 → `archives/GOAI_初赛提交截图_20260812_105128_评审版本_AI4R_ALG_MAT_和昆仑.png`（评审版本 · 3/3）

详情见 [`archives/GOAI_初赛提交留档_20260812.md`](archives/GOAI_初赛提交留档_20260812.md)。

### 重新生成主包

```powershell
cd submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1
```
