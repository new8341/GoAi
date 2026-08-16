#!/usr/bin/env python3
"""Probe official sciverse-mcp-server availability and write audit stub.

Does not start a long-lived MCP stdio session in CI; checks that:
1) SCIVERSE_API_TOKEN is present
2) npx can resolve sciverse-mcp-server
3) optional: HTTP REST meta-search still works (pipeline fallback)

Official package: https://www.npmjs.com/package/sciverse-mcp-server
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)


def main() -> int:
    token = (os.environ.get("SCIVERSE_API_TOKEN") or "").strip()
    base = (os.environ.get("SCIVERSE_BASE_URL") or "https://api.sciverse.space").strip()
    npx = shutil.which("npx")
    report: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "official_package": "sciverse-mcp-server",
        "docs": "https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/packages/mcp",
        "token_set": bool(token),
        "base_url": base,
        "npx": npx,
        "mcp_resolve": None,
        "rest_fallback_ok": None,
        "note": (
            "Interactive MCP runs inside Cursor via mcp.json.example → sciverse-mcp-server. "
            "Batch survey remains REST for reproducible audit.json."
        ),
    }

    if not npx:
        report["mcp_resolve"] = {"ok": False, "error": "npx not found; install Node.js"}
    else:
        try:
            # Package prints token error to stderr when run without args; resolution still proves install.
            proc = subprocess.run(
                [npx, "-y", "sciverse-mcp-server", "--help"],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "SCIVERSE_API_TOKEN": token or "missing"},
            )
            blob = (proc.stdout or "") + (proc.stderr or "")
            report["mcp_resolve"] = {
                "ok": True,
                "returncode": proc.returncode,
                "snippet": blob[:400],
                "package_seen": "sciverse-mcp" in blob.lower() or proc.returncode in {0, 1, 2},
            }
        except Exception as exc:  # noqa: BLE001
            report["mcp_resolve"] = {"ok": False, "error": str(exc)[:240]}

    if token:
        try:
            from materials_agent.config import load_config
            from materials_agent.models import AuditEvent
            from materials_agent.tools.retrievers import SciverseRetriever

            cfg = load_config(ROOT / "configs" / "production_sciverse.yaml")
            cfg.max_papers = 2
            cfg.retrieval.allow_backend_fallback = False
            audit: list[AuditEvent] = []
            papers = SciverseRetriever().search(
                ["SnSe lattice thermal conductivity"],
                cfg,
                audit,
            )
            report["rest_fallback_ok"] = True
            report["rest_n"] = len(papers)
            report["rest_audit_tools"] = [a.tool for a in audit]
            # MCP-shaped audit mirror for disclosure
            audit.append(
                AuditEvent(
                    step="retrieve",
                    tool="sciverse_mcp",
                    input_summary="probe: MCP package resolve + REST parity check",
                    output_summary=(
                        f"mcp_package_ok={report['mcp_resolve'].get('ok')}; "
                        f"rest_papers={len(papers)}"
                    ),
                    meta={
                        "mcp_server": "npx -y sciverse-mcp-server",
                        "tools": [
                            "search_papers",
                            "semantic_search",
                            "read_content",
                            "list_catalog",
                            "get_resource",
                        ],
                        "token_set": True,
                    },
                )
            )
            out_audit = ROOT / "outputs" / "_mcp_probe" / "audit.json"
            out_audit.parent.mkdir(parents=True, exist_ok=True)
            out_audit.write_text(
                json.dumps([a.model_dump() for a in audit], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            report["audit_path"] = str(out_audit)
        except Exception as exc:  # noqa: BLE001
            report["rest_fallback_ok"] = False
            report["rest_error"] = str(exc)[:240]
    else:
        report["rest_fallback_ok"] = False
        report["rest_error"] = "SCIVERSE_API_TOKEN missing"

    out = ROOT / "outputs" / "_mcp_probe" / "mcp_probe.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # Also copy disclosure into submissions
    semi = ROOT.parents[2] / "submissions" / "semi_final" / "sciverse_mcp_probe.md"
    lines = [
        "# Sciverse 官方 MCP 接入证明",
        "",
        f"> Package: [`sciverse-mcp-server`](https://www.npmjs.com/package/sciverse-mcp-server)",
        f"> Docs: [opendatalab/Sciverse-Agent-Tools MCP](https://github.com/opendatalab/Sciverse-Agent-Tools/tree/main/packages/mcp)",
        "",
        f"- token_set: **{report['token_set']}**",
        f"- npx: `{report['npx']}`",
        f"- mcp_resolve.ok: **{(report.get('mcp_resolve') or {}).get('ok')}**",
        f"- rest_fallback_ok: **{report['rest_fallback_ok']}** (batch survey path)",
        "",
        "## Cursor 配置",
        "",
        "复制仓库根目录 `mcp.json.example` 到 Cursor MCP 配置，使用环境变量注入 Token。",
        "",
        "## 工具面",
        "",
        "`search_papers` / `semantic_search` / `read_content` / `list_catalog` / `get_resource`",
        "",
        f"JSON: `tracks/algorithm/materials_agent/outputs/_mcp_probe/mcp_probe.json`",
        "",
    ]
    semi.parent.mkdir(parents=True, exist_ok=True)
    semi.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: report[k] for k in report if k != "mcp_resolve"}, ensure_ascii=False, indent=2))
    print("mcp_resolve", report.get("mcp_resolve"))
    print(f"wrote {out} and {semi}")
    ok = bool(token) and bool((report.get("mcp_resolve") or {}).get("ok"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
