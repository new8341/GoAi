"""MinerU adapters for local CLI and a compatible API endpoint."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path

import httpx

from materials_agent.config import ParserConfig
from materials_agent.tools.parsers.base import ParsedDocument


def _first_text_file(directory: Path) -> Path | None:
    choices = sorted(directory.rglob("*.md")) + sorted(directory.rglob("*.txt"))
    return next((p for p in choices if p.stat().st_size > 80), None)


def _mineru_command(cfg: ParserConfig) -> list[str]:
    """Split mineru_cmd so flags like `-b pipeline` are real argv tokens."""
    raw = (cfg.mineru_cmd or "mineru").strip()
    return shlex.split(raw, posix=False) or ["mineru"]


def parse_with_mineru(pdf_path: Path, output_dir: Path, cfg: ParserConfig) -> ParsedDocument:
    """Parse a PDF through MinerU and retain its generated artifacts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if cfg.mineru_mode == "api" and cfg.mineru_api_url:
        try:
            with pdf_path.open("rb") as handle, httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{cfg.mineru_api_url.rstrip('/')}/file_parse",
                    files={"files": (pdf_path.name, handle, "application/pdf")},
                    data={"return_md": "true"},
                )
                response.raise_for_status()
            payload = response.json()
            markdown = str(payload.get("markdown") or payload.get("md") or "")
            if len(markdown) >= 80:
                md_path = output_dir / "mineru.md"
                md_path.write_text(markdown, encoding="utf-8")
                return ParsedDocument(
                    text=markdown,
                    parser="mineru",
                    output_paths={"markdown": str(md_path)},
                )
            return ParsedDocument(parser="mineru", error="API response contains no markdown")
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return ParsedDocument(parser="mineru", error=f"MinerU API error: {exc}")

    command = _mineru_command(cfg)
    executable = command[0]
    if not shutil.which(executable):
        return ParsedDocument(parser="mineru", error=f"MinerU CLI not found: {executable}")
    try:
        # Pipeline cold-start + multi-page OCR often exceeds 3 minutes on CPU.
        completed = subprocess.run(
            [*command, "-p", str(pdf_path), "-o", str(output_dir)],
            check=False,
            capture_output=True,
            timeout=300,
            text=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ParsedDocument(parser="mineru", error=f"MinerU CLI error: {exc}")

    parsed = _first_text_file(output_dir)
    if not parsed:
        detail = (completed.stderr or completed.stdout or "").strip()[:400]
        suffix = f": {detail}" if detail else ""
        return ParsedDocument(parser="mineru", error=f"MinerU produced no usable Markdown/text{suffix}")
    text = parsed.read_text(encoding="utf-8", errors="ignore").strip()
    return ParsedDocument(
        text=text,
        parser="mineru",
        output_paths={"markdown": str(parsed)},
    )
