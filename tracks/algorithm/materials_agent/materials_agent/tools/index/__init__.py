"""Evidence index backends."""

from __future__ import annotations

from pathlib import Path

from materials_agent.config import AppConfig
from materials_agent.tools.index.base import EvidenceIndex
from materials_agent.tools.index.file_index import FileEvidenceIndex


def get_evidence_index(cfg: AppConfig) -> EvidenceIndex:
    """Return configured Qdrant index, degrading explicitly to file storage."""
    chunk_dir = Path(cfg.fulltext.chunk_cache_dir)
    if not chunk_dir.is_absolute():
        chunk_dir = Path(__file__).resolve().parents[3] / chunk_dir
    if cfg.fulltext.index.backend == "qdrant":
        try:
            from materials_agent.tools.index.qdrant_index import QdrantEvidenceIndex

            return QdrantEvidenceIndex(cfg.fulltext.index)
        except RuntimeError:
            pass
        except Exception as exc:
            # qdrant-client wraps transport failures in its own exception type.
            if not exc.__class__.__module__.startswith("qdrant_client"):
                raise
            pass
    return FileEvidenceIndex(chunk_dir / "evidence_chunks.json")


__all__ = ["EvidenceIndex", "FileEvidenceIndex", "get_evidence_index"]
