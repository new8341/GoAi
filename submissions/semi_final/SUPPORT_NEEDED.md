# 需要你支持的事项

> Docker / hybrid 金标、公开仓库、L2 签字、coverage≥0.5、官方 MCP、**许可证 Apache-2.0** 均已确认完成。人工卡点清空。

---

## 1. Docker / hybrid 金标 — 已完成

- GROBID + Qdrant：green  
- `production_sciverse_scibase`：`verify_production` **PASS**（含 scibase）  

---

## 2. L2 真人签字 — 已完成

- 正式归档：`tracks/algorithm/materials_agent/experiments/reviews/l2-signed-20260816-production_sciverse_scibase.md`  
- 签字人：Lee · 日期：2026-08-16 · **4/4 同意**（≥3 要求）  
- 草案保留：`l2-draft-20260816-production_sciverse_scibase.md`  

---

## 3. 公开仓库 URL — 已完成

- https://github.com/new8341/GoAi  

---

## 4. Sciverse 官方 MCP — 已完成

- 包：`npx -y sciverse-mcp-server`（OpenDataLab 官方）
- 配置样例：仓库根 `mcp.json.example`
- Skill：`tracks/algorithm/materials_agent/skills/sciverse-mcp/SKILL.md`
- 探针：`submissions/semi_final/sciverse_mcp_probe.md`（npx resolve OK + REST 回退 OK）
- 说明：`tracks/algorithm/materials_agent/docs/SCIVERSE_MCP.md`
- **本机 Cursor**：Settings → MCP → `sciverse` = Local **Connected**（2026-08-16）；Live `semantic_search` 已跑通（见 `sciverse_mcp_probe.md`）

## 5. coverage 扩标 — 已完成

- `gold_set_v2_hybrid.json` vs hybrid gaps → **coverage 0.667** / type_accuracy **1.0**
- 见 `gold_coverage.md`、`gold_score_hybrid.md`

## 6. 许可证 — 已确认

**保持 Apache-2.0**（2026-08-16 队内确认）。根目录 `LICENSE` 无需改动。
