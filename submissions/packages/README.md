# 提交打包目录 · packages/

> 生成脚本：`../scripts/build_submission_packages.ps1`  
> 命名依据：`document/xiuding.md`「提交物命名规范」

## 对外主包（必传）

| 包 | 说明 |
|----|------|
| **`AI4R_ALG_MAT_和昆仑.zip`** | 赛道_类型_方向_队伍名；含 docs + 源码 + 调研 PDF/LaTeX + 证据 |

## 辅助中间包（不必上传官网）

| 包 | 用途 |
|----|------|
| `GOAI_T3_materials_preliminary_docs_*.zip` | 仅文档 |
| `GOAI_T3_materials_code_*.zip` | 仅脱敏代码 |
| `GOAI_T3_materials_evidence_*.zip` | 仅证据快照 |

## 重新打包

```powershell
cd submissions\scripts
powershell -ExecutionPolicy Bypass -File .\build_submission_packages.ps1
```

## 门户

- 官网：https://goaihz.com  
- 手册：`document/AI_for_research.md` / `document/xiuding.md`
