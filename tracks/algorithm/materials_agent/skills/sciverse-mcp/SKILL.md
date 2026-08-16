# Sciverse official MCP (handbook鼓励项)

Use when the user needs academic literature retrieval via **official** OpenDataLab Sciverse MCP tools (`search_papers`, `semantic_search`, `read_content`, `list_catalog`, `get_resource`), or when wiring Cursor/Claude Code to Sciverse for GOAI materials Agent evidence chains.

## Official sources

- MCP package: https://www.npmjs.com/package/sciverse-mcp-server  
- Repo: https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/packages/mcp  
- Token: https://sciverse.space  

## Project setup (Cursor)

1. Copy repo-root `mcp.json.example` → Cursor MCP config (user or project `.cursor/mcp.json`).  
2. Ensure `SCIVERSE_API_TOKEN` is set in the environment (same as `tracks/algorithm/materials_agent/.env`; **never commit the token**).  
3. Restart Cursor MCP / Agent so tools appear.  
4. Prefer calling MCP tools for interactive retrieval; production batch survey still uses REST `SciverseRetriever` for reproducible `audit.json`.

## Audit discipline

When MCP is used in a session that feeds the competition pipeline, record:

- tool name (`search_papers` / `semantic_search` / …)  
- query summary  
- top doc ids / DOIs  

into the run `audit.json` as `tool=sciverse_mcp` (see `scripts/probe_sciverse_mcp.py` and `docs/SCIVERSE_MCP.md`).

## Fallback

If MCP/node is unavailable, use REST:

```powershell
py -3 scripts/run_survey.py survey -c configs/production_sciverse_scibase.yaml
```
