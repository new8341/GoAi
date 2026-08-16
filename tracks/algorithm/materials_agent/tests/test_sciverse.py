"""Unit tests for Sciverse client + retriever fallback."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from materials_agent.config import AppConfig, RetrievalConfig
from materials_agent.models import AuditEvent, Paper
from materials_agent.tools.retrievers import SciverseRetriever
from materials_agent.tools.fs_safe import safe_fs_name
from materials_agent.tools.sciverse_client import SciverseClient, _paper_from_meta


def test_safe_fs_name_strips_colon():
    assert ":" not in safe_fs_name("SV-paper:10.1002/aenm")
    assert safe_fs_name("SV-paper:10.1002/aenm").startswith("SV-paper")


def test_paper_from_meta_maps_fields():
    paper = _paper_from_meta(
        {
            "unique_id": "paper:10.1/abc",
            "title": "SnSe thermal conductivity",
            "doi": "10.1/abc",
            "abstract": "Vacancy engineering...",
            "publication_published_year": 2021,
            "publication_venue_name_unified": "Nature Energy",
            "author": [{"name": "A Author"}],
            "subjects": ["materials science"],
            "doc_id": "deadbeef",
            "is_content_accessible": True,
        }
    )
    assert paper is not None
    assert paper.title.startswith("SnSe")
    assert paper.year == 2021
    assert paper.doi == "10.1/abc"
    assert paper.source == "sciverse"
    assert ":" not in paper.id
    assert paper.raw["sciverse_doc_id"] == "deadbeef"


def test_meta_search_posts_bearer(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "results": [
                    {
                        "unique_id": "paper:1",
                        "title": "Demo SnSe paper",
                        "abstract": "kappa",
                        "publication_published_year": 2020,
                    }
                ],
                "total_count": 1,
                "page": 1,
                "page_size": 10,
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["headers"] = kwargs.get("headers")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, json=None):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    client = SciverseClient("tok-test", "https://api.sciverse.space")
    papers = client.meta_search("SnSe vacancy", year_from=2018, page_size=10)
    assert len(papers) == 1
    assert captured["url"].endswith("/meta-search")
    assert captured["headers"]["Authorization"] == "Bearer tok-test"
    assert captured["json"] == {
        "query": "SnSe vacancy",
        "page": 1,
        "page_size": 10,
    }
    assert "year_from" not in captured["json"]


def test_retriever_falls_back_without_token(monkeypatch):
    monkeypatch.delenv("SCIVERSE_API_TOKEN", raising=False)
    monkeypatch.delenv("SCIVERSE_API_KEY", raising=False)
    cfg = AppConfig(
        topic="SnSe",
        max_papers=2,
        retrieval=RetrievalConfig(backend="sciverse", sciverse_api_token=""),
    )
    audit: list[AuditEvent] = []
    fake_papers = [
        Paper(id="OA-1", title="OpenAlex hit", abstract="SnSe", source="openalex")
    ]
    with patch(
        "materials_agent.tools.retrievers.OpenAlexRetriever.search",
        return_value=fake_papers,
    ) as mocked:
        out = SciverseRetriever().search(["SnSe"], cfg, audit)
    assert out == fake_papers
    mocked.assert_called_once()
    assert audit[-1].tool == "sciverse"
    assert "fallback openalex" in (audit[-1].output_summary or "")


def test_retriever_uses_client_when_token_set():
    cfg = AppConfig(
        topic="SnSe lattice",
        max_papers=5,
        retrieval=RetrievalConfig(
            backend="sciverse",
            sciverse_api_token="tok",
            sciverse_mode="meta",
            min_relevance=0.0,
        ),
    )
    audit: list[AuditEvent] = []
    demo = [
        Paper(
            id="SV-1",
            title="SnSe lattice thermal conductivity",
            abstract="vacancy",
            source="sciverse",
        )
    ]
    fake_client = MagicMock()
    fake_client.meta_search.return_value = demo
    with patch(
        "materials_agent.tools.sciverse_client.SciverseClient",
        return_value=fake_client,
    ):
        with patch(
            "materials_agent.tools.sciverse_client.resolve_sciverse_token",
            return_value="tok",
        ):
            out = SciverseRetriever().search(["SnSe vacancy"], cfg, audit)
    assert len(out) >= 1
    assert audit[-1].tool == "sciverse"
    assert "fallback" not in (audit[-1].output_summary or "")
