# Sciverse MCP / Skill（手册鼓励项）

> 0816：鼓励 Sciverse API 的 MCP/Skill 接入，调用记录构成可审计证据链。  
> 本队现状：生产路径为 **REST Bearer**（`SciverseRetriever`）+ `audit.json`；MCP 为可选增强。

## 当前可审计证据链（已落地）

| 环节 | 落点 |
|------|------|
| 检索调用 | `outputs/*/audit.json`（tool=`sciverse` / `sciverse_scibase` / `scibase`） |
| 数据库标签 | Gap/主张 `retrieval_database` |
| 外部版本 | `external_versions.json` |

## MCP 接入步骤（需人工：平台开通 + Cursor 配置）

1. 在 [sciverse.space](https://sciverse.space) / OpenDataLab 控制台确认是否提供 **官方 MCP server** 或 Skill 包（以官网赛道页为准）。  
2. 若提供 SSE/stdio MCP：在 Cursor `mcp.json` 增加服务器条目，注入与 `.env` 相同的 `SCIVERSE_API_TOKEN`（勿提交密钥）。  
3. 将 MCP 工具名映射到本仓库审计：每次 MCP 调用后写一条 `AuditEvent(step=retrieve, tool=sciverse_mcp, ...)`。  
4. 复赛披露：在 `compliance/API_AND_CLOSED_MODELS.md` 增加 MCP 权限范围与可替代性（REST 回退）。

## 未接 MCP 时的合规表述

> 本系统使用 Sciverse HTTP Agent Tools（meta/semantic search）形成可审计调用链；MCP/Skill 为手册鼓励项，待官方 MCP 端点可用后按上表接入，REST 路径保持为可复现主路径。

## Skill 占位

仓库可另增 `.cursor/skills/sciverse-retrieve/SKILL.md`（需你确认官方 Skill 规范后启用）。当前以 REST 为准，避免虚构 MCP 端点。
