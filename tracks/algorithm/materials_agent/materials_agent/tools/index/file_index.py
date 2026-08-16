"""Portable lexical evidence index used by demos and Qdrant fallback."""

from __future__ import annotations

import json
import re
from pathlib import Path

from materials_agent.models import DocumentChunk


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


class FileEvidenceIndex:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.chunks: list[DocumentChunk] = []
        if self.path.is_file():
            rows = json.loads(self.path.read_text(encoding="utf-8"))
            self.chunks = [DocumentChunk.model_validate(row) for row in rows]

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        by_id.update({chunk.chunk_id: chunk for chunk in chunks})
        self.chunks = list(by_id.values())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([chunk.model_dump() for chunk in self.chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def search(
        self, query: str, paper_ids: list[str] | None = None, limit: int = 5
    ) -> list[tuple[DocumentChunk, float]]:
        query_tokens = _tokens(query)
        candidates = (
            [chunk for chunk in self.chunks if chunk.paper_id in set(paper_ids)]
            if paper_ids
            else self.chunks
        )
        scored = []
        for chunk in candidates:
            doc_tokens = _tokens(chunk.text)
            score = len(query_tokens & doc_tokens) / max(1, len(query_tokens))
            scored.append((chunk, score))
        return sorted(scored, key=lambda row: row[1], reverse=True)[:limit]
