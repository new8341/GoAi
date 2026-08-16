# Gap 人工 / AI 抽检归档（科学意义 30%）

## 推荐：AI 可执行标准（默认）

正式门禁与阈值见：**[`科学抽检标准_AI可执行.md`](科学抽检标准_AI可执行.md)**

```bash
py -3 scripts/science_review_gate.py -c configs/production.yaml --run outputs/production
```

- **L0** 机械科学门禁（全量 Gap）  
- **L1** AI 双角色抽样（≥3，规则默认可跑）  
- **L2** 真人抽检（可选加分）

通过条件：`science_review_status=PASS`（写入 `outputs/<run>/science_review.json` + 本目录 `science-review-*.md`）。

### 最近一次六轮升级（Sciverse）

见：**[`expert-6rounds-20260811-production_sciverse.md`](expert-6rounds-20260811-production_sciverse.md)**  
终态：`production_sciverse` 上 verify ∩ science ∩ objective(must) = **PASS**。

### 架构与实现流程专家核验

见：**[`architecture-expert-audit-20260811.md`](architecture-expert-audit-20260811.md)**  
U1–U15 已落地（2026-08-11）。答辩索引：**[`defense_pack.md`](defense_pack.md)**。

---

## 可选：真人补强（L2）

完整专家核对标准与双端核对区见：**[`专家级真人核对标准.md`](专家级真人核对标准.md)**

- 用户端：打开运行 → **专家核对**
- 调试端：`/debug/?run=production` → **专家核对**
- API：`/api/runs/production/expert-review`

生产 `verify_production` 与 `science_review` 均 PASS 后，如需答辩「有人看过」：

1. 打开核对区或 `outputs/production/expert_review_pack.json`，按标准 ID（R/P/G/E/…）逐项判决。  
2. 重点核对 `quote_or_basis` 是否为对应全文子串（E2）与 Gap 类型名实相符（T*）。  
3. 导出本机判决 JSON，或复制下方模板为 `review-YYYYMMDD-<yourname>.md`。

> 工程提醒：黑盒任务产物路径为 `outputs/user_jobs/<job_id>/`；专家核对 API 使用完整相对 id（如 `user_jobs/<job_id>`），勿只取最后一段。维护脚本 `reground_production_gaps.py` 默认 dry-run，写盘需 `--write`。

```markdown
# Gap review YYYY-MM-DD

Reviewer:
Config: configs/production.yaml
production_verification: PASS / FAIL
science_review: PASS / FAIL

| gap_id | type | quote⊂source | notes |
|--------|------|--------------|-------|
|        |      | yes/no       |       |

Overall: accept / revise evidence filters
```
