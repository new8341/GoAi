"""Tool adapters for retrieval, full-text provenance, and evidence indexing."""

from materials_agent.tools.retrievers import get_retriever
from materials_agent.tools.index import get_evidence_index

__all__ = ["get_evidence_index", "get_retriever"]
