# 初赛合订入口（可整份粘贴/导出 PDF）

请按顺序阅读或合并导出：

1. [方案说明](01_方案说明_材料文献Agent.md)  
2. [技术路线概述](02_技术路线概述.md)  
3. [可行性与证据摘要](03_可行性与证据摘要.md)（含三分法、规则 vs LLM / MP 外验、金标准口径）  
4. [开源计划与边界](04_开源计划与边界.md)  

## 官网实际上传（优先）

按 `document/xiuding.md` 命名规范，上传**唯一主包**：

```text
submissions/packages/AI4R_ALG_MAT_和昆仑.zip
```

内含：`01_docs` + `02_code` + `03_survey_report`（PDF+LaTeX）+ `04_evidence`。

若平台只允许**一个文档附件**另传合订，可合并上述 01–04，建议文件名：

`GOAI_赛道三_算法赛_方向三_材料文献Agent_初赛方案_20260812.md`（或导出 PDF）

重新打包：

```powershell
cd submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1
```
