# AI 仿真人工抽检报告 · round_20260729_1250

- seed: `42` · sampled: **5** · mode: `rules`
- keep/revise/reject: **5** / **0** / **0**

> 本报告为 AI/规则双人审仿真，不替代领域专家终审。

| Gap | Type | A合计 | B合计 | Final | Decision | 分歧 |
|-----|------|-------|-------|-------|----------|------|
| `gap-method-balance` | method_gap | 10 | 10 | 10 | **keep** | — |
| `gap-conflict-LOCAL-004` | contradiction | 10 | 9 | 9 | **keep** | evidence_fit: A=2 B=1 -> 1 |
| `gap-missing-link-topic` | missing_link | 10 | 10 | 10 | **keep** | — |
| `gap-limitations` | underexplored | 10 | 10 | 10 | **keep** | — |
| `gap-debate-LOCAL-001` | underexplored | 10 | 10 | 10 | **keep** | — |

## 制度说明

- 评审 A：证据与可证伪优先（严谨派）
- 评审 B：新颖性膨胀与过宣称敏感（怀疑派）
- 裁决：逐维取 min(A,B)（保守），再按总分映射 keep/revise/reject

协议详见 `experiments/human_review_checklist.md`。
