"""Text-cache policy for production vs demo fulltext attachment."""

from __future__ import annotations

from pathlib import Path

from materials_agent.config import AppConfig, FulltextConfig, RetrievalConfig
from materials_agent.models import Paper
from materials_agent.tools.fulltext import attach_fulltext


def test_allow_text_cache_false_forces_pdf_parse(tmp_path: Path, monkeypatch) -> None:
    cache = tmp_path / "cache"
    pdfs = tmp_path / "pdfs"
    cache.mkdir()
    pdfs.mkdir()
    paper_id = "WTEST1"
    (cache / f"{paper_id}.txt").write_text("cached fulltext " * 20, encoding="utf-8")
    pdf = pdfs / f"{paper_id}.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    cfg = AppConfig(
        topic="test",
        retrieval=RetrievalConfig(fetch_fulltext=True, fulltext_cache_dir=str(cache)),
        fulltext=FulltextConfig(
            download_oa=False,
            allow_text_cache=False,
            pdf_cache_dir=str(pdfs),
            parse_cache_dir=str(tmp_path / "parsed"),
        ),
    )
    monkeypatch.setattr(
        "materials_agent.tools.fulltext._parse_pdf",
        lambda paper, pdf_path, cfg, audit: ("parsed from pdf " * 10, "mineru", {}, []),
    )
    papers = [Paper(id=paper_id, title="t", year=2020)]
    out = attach_fulltext(papers, cfg, audit=[])
    assert out[0].fulltext_source == "mineru"
    assert "parsed from pdf" in (out[0].full_text or "")


def test_grobid_source_label_not_fusion(tmp_path: Path, monkeypatch) -> None:
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    paper_id = "WGROBID1"
    pdf = pdfs / f"{paper_id}.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    cfg = AppConfig(
        topic="test",
        retrieval=RetrievalConfig(fetch_fulltext=True, fulltext_cache_dir=str(tmp_path / "cache")),
        fulltext=FulltextConfig(
            download_oa=False,
            allow_text_cache=False,
            pdf_cache_dir=str(pdfs),
            parse_cache_dir=str(tmp_path / "parsed"),
        ),
    )
    monkeypatch.setattr(
        "materials_agent.tools.fulltext._parse_pdf",
        lambda paper, pdf_path, cfg, audit: ("grobid body " * 20, "grobid", {}, []),
    )
    out = attach_fulltext([Paper(id=paper_id, title="t", year=2020)], cfg, audit=[])
    assert out[0].fulltext_source == "grobid"

def test_allow_text_cache_true_reuses_txt(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    paper_id = "WTEST2"
    (cache / f"{paper_id}.txt").write_text("cached fulltext " * 20, encoding="utf-8")
    cfg = AppConfig(
        topic="test",
        retrieval=RetrievalConfig(fetch_fulltext=True, fulltext_cache_dir=str(cache)),
        fulltext=FulltextConfig(download_oa=False, allow_text_cache=True),
    )
    papers = [Paper(id=paper_id, title="t", year=2020)]
    out = attach_fulltext(papers, cfg, audit=[])
    assert out[0].fulltext_source == "local_cache"
