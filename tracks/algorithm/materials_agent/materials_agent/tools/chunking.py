"""Deterministic chunking with stable offsets for evidence provenance."""

from __future__ import annotations

import hashlib
import re

from materials_agent.config import ChunkingConfig
from materials_agent.models import DocumentChunk, Paper


def _section_ranges(text: str) -> list[tuple[str, int, int]]:
    """Detect Markdown-like headings; fallback to one Body section."""
    matches = list(re.finditer(r"(?m)^#{1,6}\s+(.+?)\s*$", text))
    if not matches:
        return [("Body", 0, len(text))]
    ranges: list[tuple[str, int, int]] = []
    if matches[0].start() > 0:
        ranges.append(("Preamble", 0, matches[0].start()))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        ranges.append((match.group(1).strip()[:200], match.start(), end))
    return ranges


def _split_range(
    text: str, start: int, end: int, max_chars: int, overlap_chars: int
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    cursor = start
    while cursor < end:
        limit = min(end, cursor + max_chars)
        if limit < end:
            boundary = max(text.rfind("\n\n", cursor, limit), text.rfind(". ", cursor, limit))
            if boundary > cursor + max_chars // 3:
                limit = boundary + (2 if text.startswith(". ", boundary) else 0)
        if limit <= cursor:
            limit = min(end, cursor + max_chars)
        ranges.append((cursor, limit))
        if limit >= end:
            break
        cursor = max(cursor + 1, limit - overlap_chars)
    return ranges


def chunk_paper(paper: Paper, cfg: ChunkingConfig) -> list[DocumentChunk]:
    """Split canonical full text into source-addressable chunks."""
    text = (paper.full_text or "").strip()
    if len(text) < 1:
        return []
    chunks: list[DocumentChunk] = []
    sections = _section_ranges(text) if cfg.respect_sections else [("Body", 0, len(text))]
    for section, section_start, section_end in sections:
        for start, end in _split_range(
            text, section_start, section_end, cfg.max_chars, cfg.overlap_chars
        ):
            snippet = text[start:end].strip()
            if len(snippet) < 20:
                continue
            actual_start = text.find(snippet, start, end)
            actual_end = actual_start + len(snippet)
            digest = hashlib.sha256(snippet.encode("utf-8")).hexdigest()
            chunks.append(
                DocumentChunk(
                    chunk_id=f"{paper.id}:{len(chunks):04d}",
                    paper_id=paper.id,
                    text=snippet,
                    char_start=actual_start,
                    char_end=actual_end,
                    section=section,
                    parser=paper.fulltext_source or "local_cache",
                    source_url=paper.fulltext_url or paper.oa_url,
                    pdf_hash=paper.pdf_hash,
                    chunk_hash=digest,
                )
            )
    return chunks
