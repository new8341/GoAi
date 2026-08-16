from materials_agent.config import IndexConfig
from materials_agent.models import DocumentChunk
from materials_agent.tools.index.qdrant_index import QdrantEvidenceIndex


def test_qdrant_filters_by_paper_id() -> None:
    index = QdrantEvidenceIndex(IndexConfig(qdrant_url=":memory:", collection="test_evidence"))
    index.upsert(
        [
            DocumentChunk(
                chunk_id="P1:0000",
                paper_id="P1",
                text="Vacancy engineering lowers thermal conductivity.",
                char_start=0,
                char_end=47,
            ),
            DocumentChunk(
                chunk_id="P2:0000",
                paper_id="P2",
                text="Catalysis is unrelated to thermoelectrics.",
                char_start=0,
                char_end=41,
            ),
        ]
    )

    hits = index.search("vacancy conductivity", paper_ids=["P1"])

    assert hits
    assert all(chunk.paper_id == "P1" for chunk, _ in hits)
