"""Canonical fulltext_source labels (new writes never emit grobid_fusion)."""

from __future__ import annotations

PARSER_CANONICAL = {"mineru", "grobid"}
PARSER_READ_ALIASES = {"grobid_fusion": "grobid"}


def canonical_fulltext_source(source: str | None) -> str:
    raw = (source or "").strip()
    return PARSER_READ_ALIASES.get(raw, raw)


def is_parser_derived_source(source: str | None) -> bool:
    return canonical_fulltext_source(source) in PARSER_CANONICAL
