"""Common parser result types for full-text evidence extraction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedDocument:
    text: str = ""
    parser: str = ""
    parser_version: str = ""
    sections: list[tuple[str, int, int]] = field(default_factory=list)
    output_paths: dict[str, str] = field(default_factory=dict)
    error: str = ""
