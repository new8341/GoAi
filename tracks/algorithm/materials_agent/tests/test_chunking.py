from materials_agent.config import ChunkingConfig
from materials_agent.models import Paper
from materials_agent.tools.chunking import chunk_paper


def test_chunks_have_stable_offsets_and_hashes() -> None:
    text = "# Results\n" + ("Vacancy engineering suppresses thermal conductivity. " * 80)
    paper = Paper(id="P1", title="Demo", full_text=text, fulltext_source="mineru")
    chunks = chunk_paper(paper, ChunkingConfig(max_chars=180, overlap_chars=20))

    assert len(chunks) > 1
    assert all(chunk.text == text[chunk.char_start : chunk.char_end] for chunk in chunks)
    assert all(chunk.chunk_hash for chunk in chunks)
    assert all(chunk.section == "Results" for chunk in chunks)
