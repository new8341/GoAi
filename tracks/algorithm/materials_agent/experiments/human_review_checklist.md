# 人工 / AI 仿真抽检制度

> 目标：用**可复现的抽检节奏**替代「只看自动绿勾」。  
> AI 仿真双人审 = 两套对立角色独立打分 + 分歧裁决；真·人工可随时覆盖同一表格。

## 1. 制度设计（仿真实人工双人标）

| 角色 | 职责 | AI 如何仿真 |
|------|------|-------------|
| 抽样员 | 按 Gap 类型分层抽 10 条 | 固定 seed 分层抽样 |
| 评审 A「领域严谨派」 | 证据是否贴题、是否可证伪、类型是否正确 | 角色提示 / 规则量表偏严 |
| 评审 B「方法怀疑派」 | 是否把 Known 当新知、是否空泛、是否过宣称 | 对立角色提示 / 反膨胀规则 |
| 裁决员 | 对 A/B 分歧项给出最终 keep/revise/reject | 分歧表 + 保守合并（倾向降级） |
| 归档员 | 写清轮次、配置、结论、待改 bug | `experiments/reviews/round_*.md` |

**原则**：AI 抽检是「制度仿真与质量雷达」，不能宣称已替代领域专家终审；提交材料应写明 *AI dual-review + optional human override*。

## 2. 评分量表（0–2 分，双人共用）

| 维度 | 0 | 1 | 2 |
|------|---|---|---|
| evidence_fit | 无原文或与主张无关 | 有引用但弱相关 | paper_id+片段直接支撑主张 |
| falsifiability | 无可执行否证 | 有 next 但空泛 | next + falsification 可操作 |
| type_purity | 类型明显错 | 勉强可接受 | 类型与描述一致 |
| novelty_honesty | 把 Known 当重大新发现 | 新颖性略夸大 | Known/candidate 标注诚实 |
| non_overclaim | 宣称已发现/已证实 | 措辞偏满 | 明确是假说/缺口 |

**通过线（建议）**：五维总分 ≥ 6 且无任一维为 0 → `keep`；总分 4–5 或有一维为 0 → `revise`；总分 ≤ 3 → `reject`。

## 3. 节奏

| 节点 | 动作 |
|------|------|
| 每次改 Gap/抽取逻辑后 | 跑一轮 AI 双人抽检 |
| 每周固定 | 同一题集再跑 +（可选）人工抽 5 条覆盖 |
| 初赛/复赛提交前 | 归档 round 报告进 `submissions/` |

## 4. 命令

```bash
cd tracks/algorithm/materials_agent

# 无 LLM：纯规则仿真双人审（可复现）
python scripts/ai_human_review.py --gaps outputs/demo/gaps.json --known outputs/demo/known_pairs.json

# 有 LLM：双角色模型独立打分再裁决
python scripts/ai_human_review.py -c configs/default.yaml --gaps outputs/demo/gaps.json --use-llm
```

产出：`experiments/reviews/round_YYYYMMDD_HHMM/`（`scores.json` + `report.md`）。
