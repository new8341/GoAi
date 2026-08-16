"""Tests for literature archive naming and layout."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from materials_agent.config import AppConfig, FulltextConfig, RetrievalConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.tools.literature_archive import (
    archive_retrieved_literature,
    make_run_dir,
    slugify_topic,
)


def test_slugify_topic_keeps_ascii_and_chinese() -> None:
    assert "SnSe" in slugify_topic("SnSe lattice thermal conductivity")
    assert slugify_topic("热电/空位工程!!") 


def test_make_run_dir_uses_topic_and_time(tmp_path: Path) -> None:
    when = datetime(2026, 8, 2, 23, 5, 9)
    path = make_run_dir("SnSe vacancy", tmp_path, when=when)
    assert path.name.startswith("SnSe_vacancy_20260802_230509")
    assert (path / "pdfs").is_dir()
    assert (path / "abstracts").is_dir()


def test_archive_writes_metadata_and_abstract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "materials_agent.tools.literature_archive._project_root",
        lambda: tmp_path,
    )
    cfg = AppConfig(
        topic="SnSe test topic",
        retrieval=RetrievalConfig(
            archive_literature=True,
            archive_root=str(tmp_path / "data"),
            fetch_fulltext=False,
        ),
        fulltext=FulltextConfig(download_oa=False, pdf_cache_dir=str(tmp_path / "pdfs")),
    )
    papers = [
        Paper(
            id="P1",
            title="Example paper",
            year=2020,
            doi="10.1/x",
            abstract="Abstract text " * 20,
        )
    ]
    audit: list[AuditEvent] = []
    out = archive_retrieved_literature(
        papers, cfg, audit, queries=["SnSe test topic"], run_dir=make_run_dir(cfg.topic, tmp_path / "data")
    )
    assert out is not None
    assert (out / "papers.json").is_file()
    assert (out / "manifest.json").is_file()
    assert (out / "README.md").is_file()
    assert (out / "abstracts" / "P1.txt").is_file()
    assert any(a.step == "archive_literature" for a in audit)
