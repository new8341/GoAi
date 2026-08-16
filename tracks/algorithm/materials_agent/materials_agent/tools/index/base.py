"""Evidence-index abstraction shared by file and Qdrant backends."""

from __future__ import annotations

from typing import Protocol

from materials_agent.models import DocumentChunk


class EvidenceIndex(Protocol):
    def upsert(self, chunks: list[DocumentChunk]) -> None: ...

    def search(
        self, query: str, paper_ids: list[str] | None = None, limit: int = 5
    ) -> list[tuple[DocumentChunk, float]]: ...
