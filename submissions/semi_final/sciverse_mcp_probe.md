# Sciverse 官方 MCP 接入证明

> Package: [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server)  
> Docs: [opendatalab/Sciverse-Agent-Tools MCP](https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/packages/mcp)

## 状态摘要

| 项 | 结果 |
|----|------|
| Cursor 源 | `AI_kaiyuan` → `.cursor/mcp.json` |
| 环境 | Local **Connected**（2026-08-16 本机确认） |
| `npx` resolve | **OK**（`scripts/probe_sciverse_mcp.py`） |
| REST 回退 | **OK**（批量 survey / `audit.json`） |
| Live MCP 调用 | **OK**（见下） |

## Cursor 配置

- 样例：仓库根 `mcp.json.example`（可提交）  
- 本机生效：`.cursor/mcp.json`（gitignore，含 Token，**勿提交**）

## 工具面（Connected 可见）

`search_papers` / `semantic_search` / `read_content` / `list_catalog` / `list_paper_relations` / `get_resource`

## Live 探针（Agent 经官方 MCP）

- 时间：2026-08-16  
- 工具：`semantic_search`  
- 查询：`SnSe lattice thermal conductivity vacancy scattering`  
- `mode=fast`，`top_k=3`，`biz_code=0` / `SUCCESS`  
- 命中示例（title · year · venue）：
  1. *Achieving high thermoelectric figure of merit in polycrystalline SnSe via introducing Sn vacancies* · 2017 · JACS  
  2. *Realization of high thermoelectric performance in polycrystalline tin selenide through Schottky vacancies…* · 2020 · Chem. Mater.  
  3. *Defect engineering boosted ultrahigh thermoelectric power conversion efficiency in polycrystalline SnSe* · 2021 · ACS AMI  

完整 JSON 备份：`tracks/algorithm/materials_agent/outputs/_mcp_probe/mcp_live_semantic.json`（本地 outputs，gitignore）。

## 双路径纪律

批量金标跑次仍用 REST `SciverseRetriever` 写可复现 `audit.json`；MCP 用于交互检索与手册鼓励项披露。
