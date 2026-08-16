"""Tests for MinerU CLI command assembly."""

from __future__ import annotations

from materials_agent.config import ParserConfig
from materials_agent.tools.parsers.mineru_parser import _mineru_command


def test_mineru_command_splits_backend_flags() -> None:
    cfg = ParserConfig(mineru_cmd="mineru -b pipeline")
    assert _mineru_command(cfg) == ["mineru", "-b", "pipeline"]


def test_mineru_command_default() -> None:
    assert _mineru_command(ParserConfig()) == ["mineru"]
