# GOAI 初赛提交包 · 算法赛 · 方向三

> 队伍材料：材料科学文献驱动的科学发现智能体（Materials Agent）  
> 截止（规划）：**~2026-08-16**（以官网最终通知为准）  
> 官方手册（修订 MD）：仓库 `document/AI_for_research.md`（源 PDF：`AI_for_reserach.pdf`）  
> 报名/通知门户：**https://goaihz.com**

---

## 1. 本包包含什么（初赛必交 · 手册附录 B）

| 序号 | 文件 | 对应手册要求 |
|------|------|--------------|
| 01 | [`01_方案说明_材料文献Agent.md`](01_方案说明_材料文献Agent.md) | 方案说明文档 |
| 02 | [`02_技术路线概述.md`](02_技术路线概述.md) | 技术路线概述 |
| 03 | [`03_可行性与证据摘要.md`](03_可行性与证据摘要.md) | 可附初步实验/可行性 |
| 04 | [`04_开源计划与边界.md`](04_开源计划与边界.md) | 开源计划与边界 + 外部资源版本/访问 |
| — | [`官网表单填写指南.md`](官网表单填写指南.md) | 对照 goaihz「作品提交」页字段 |

**初赛须提交训练与推理源代码**（手册表一-2）：随机种子与关键参数在配置/代码中体现；外部资源注明来源与版本。不要求容器/完整文档；标准为代码完整、流程可复现。完整复现审核仍在复赛。

**基本任务报告格式（手册 A04）：** 须附 **PDF（编译产物）+ LaTeX 源码**（`report.tex`、`references.bib` 及编译所需文件）。生成：

```powershell
cd tracks\algorithm\materials_agent
python scripts\export_survey_latex.py outputs\production_sciverse
python scripts\dump_external_versions.py -c configs\production_sciverse.yaml
```

---

## 2. 推荐上传内容（给评委）

**对外唯一主包（命名规范，见 `document/xiuding.md`）：**

```text
submissions/packages/AI4R_ALG_MAT_和昆仑.zip
```

包内结构：`01_docs`（方案/路线）· `02_code`（脱敏源码）· `03_survey_report`（PDF+LaTeX）· `04_evidence`。

辅助中间包（不必上传）：`GOAI_T3_materials_*_时间戳.zip`。

合订入口：[`SUBMIT_合订入口.md`](SUBMIT_合订入口.md)。

---

## 3. 上传方法（官方口径）

1. 打开 **https://goaihz.com**，使用已报名账号登录。  
2. 进入赛道三 / 算法赛 · **方向三（材料文献 Agent）** 提交入口。  
3. 上传 **`AI4R_ALG_MAT_和昆仑.zip`**（表单若拆字段，按 `01_docs` / 源码 / 报告分别对应即可）。  
4. 提交后截图保存「已提交」页面与文件名、时间戳。

> 仓库内没有官方 zip 命名硬性规定；以官网为准。本包命名见 `../packages/README.md`。

---

## 4. 提交话术三分法（答辩/表单备注可用）

| 层 | 含义 | 路径 |
|----|------|------|
| Smoke | 离线可复现冒烟 | `configs/demo_local.yaml` |
| Production 证据链 | Sciverse OA 全文 + quote⊂source | `outputs/production_sciverse`（LLM off） |
| Route A | SPR 搜索 + Materials Project 外验；叙事按 **30/30/20/20** | `outputs/production_route_a` |

**禁止混说**：不要把 LLM-off 的 `production_sciverse` 写成「Sciverse + LLM 发现」。

---

## 5. 联系与版本

- 代码工作区：`tracks/algorithm/materials_agent/`  
- 答辩索引：`tracks/algorithm/materials_agent/experiments/reviews/defense_pack.md`  
- 本包生成/修订日期：2026-08-12  
