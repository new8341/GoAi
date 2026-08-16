"""Qdrant evidence index with deterministic hash embeddings and payload filters."""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from materials_agent.config import IndexConfig
from materials_agent.models import DocumentChunk


def _vector(text: str, size: int) -> list[float]:
    """Dependency-free baseline embedding; replaceable by a domain encoder later."""
    vector = [0.0] * size
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % size
        vector[index] += 1.0
    norm = sum(value * value for value in vector) ** 0.5
    return [value / norm for value in vector] if norm else vector


class QdrantEvidenceIndex:
    def __init__(self, cfg: IndexConfig):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, PointStruct, VectorParams
        except ImportError as exc:
            raise RuntimeError("Install qdrant-client to use index.backend=qdrant") from exc
        self._models = (Distance, PointStruct, VectorParams)
        self.client = (
            QdrantClient(path=":memory:")
            if cfg.qdrant_url == ":memory:"
            else QdrantClient(url=cfg.qdrant_url, api_key=cfg.qdrant_api_key or None)
        )
        self.collection = cfg.collection
        self.size = cfg.vector_size
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.size, distance=Distance.COSINE),
            )

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        _, PointStruct, _ = self._models
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"materials-agent:{chunk.chunk_id}")),
                vector=_vector(chunk.text, self.size),
                payload=chunk.model_dump(),
            )
            for chunk in chunks
        ]
        if points:
            self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(
        self, query: str, paper_ids: list[str] | None = None, limit: int = 5
    ) -> list[tuple[DocumentChunk, float]]:
        query_filter: Any = None
        if paper_ids:
            from qdrant_client.models import FieldCondition, Filter, MatchAny

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="paper_id",
                        match=MatchAny(any=paper_ids),
                    )
                ]
            )
        hits = self.client.query_points(
            collection_name=self.collection,
            query=_vector(query, self.size),
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        ).points
        return [
            (DocumentChunk.model_validate(hit.payload), float(hit.score))
            for hit in hits
            if hit.payload
        ]
