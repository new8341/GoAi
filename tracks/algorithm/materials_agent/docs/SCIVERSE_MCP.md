# Sciverse MCP / Skill（手册鼓励项 · 已接官方包）

> 0816：鼓励 Sciverse API 的 MCP/Skill 接入，调用记录构成可审计证据链。

## 官方来源

| 项 | 链接 |
|----|------|
| npm | https://www.npmjs.com/package/sciverse-mcp-server |
| GitHub | https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/packages/mcp |
| Token | https://sciverse.space |

暴露工具：`search_papers` / `semantic_search` / `read_content` / `list_catalog` / `get_resource`

## 本仓库落点

| 产物 | 路径 |
|------|------|
| Cursor MCP 样例 | 仓库根 `mcp.json.example` |
| Agent Skill | `tracks/algorithm/materials_agent/skills/sciverse-mcp/SKILL.md` |
| 探针脚本 | `scripts/probe_sciverse_mcp.py` |
| 探针报告 | `submissions/semi_final/sciverse_mcp_probe.md` |

```powershell
cd tracks\algorithm\materials_agent
py -3 scripts/probe_sciverse_mcp.py
```

## 双路径纪律

| 路径 | 用途 |
|------|------|
| **MCP**（`npx -y sciverse-mcp-server`） | Cursor/交互式 Agent 检索；手册鼓励的 MCP 接入 |
| **REST**（`SciverseRetriever`） | 复赛可复现批量 survey + `audit.json` 主证据链 |

MCP 与 REST 共用同一 Bearer Token；MCP 不可用时 REST 为等价可验证回退（须在合规中披露）。

## Cursor 启用步骤

1. 将 `mcp.json.example` 合并进 Cursor MCP 配置（用户级或项目级）。  
2. 环境已有 `SCIVERSE_API_TOKEN`（与 `.env` 一致，**勿提交**）。  
3. 重启 MCP；确认工具列表出现上述 5 个工具。  

## 合规表述（可直接贴提交物）

> 本队已接入 OpenDataLab 官方 [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server)（见 `mcp.json.example`）。批量金标跑次仍用 REST Agent Tools 写入可审计 `audit.json`；MCP 用于交互式检索与手册鼓励项披露，二者共享 Sciverse Token 与证据溯源口径。
