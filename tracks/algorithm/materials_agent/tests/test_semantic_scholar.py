"""Semantic Scholar retriever + client unit tests."""

from __future__ import annotations

import httpx

from materials_agent.config import AppConfig, RetrievalConfig
from materials_agent.models import Paper
from materials_agent.tools.retrievers import SemanticScholarRetriever
from materials_agent.tools.semantic_scholar_client import (
    SemanticScholarClient,
    _paper_from_hit,
    resolve_semantic_scholar_api_key,
)


def test_resolve_s2_key_prefers_config(monkeypatch):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    cfg = AppConfig(
        topic="SnSe",
        retrieval=RetrievalConfig(semantic_scholar_api_key="cfg-s2"),
    )
    assert resolve_semantic_scholar_api_key(cfg) == "cfg-s2"


def test_resolve_s2_key_env_alias(monkeypatch):
    monkeypatch.setenv("S2_API_KEY", "env-s2")
    cfg = AppConfig(topic="SnSe", retrieval=RetrievalConfig(semantic_scholar_api_key=""))
    assert resolve_semantic_scholar_api_key(cfg) == "env-s2"


def test_paper_from_hit_maps_fields():
    paper = _paper_from_hit(
        {
            "paperId": "abc123",
            "title": "SnSe thermal conductivity",
            "year": 2020,
            "abstract": "A study.",
            "authors": [{"name": "A Author"}],
            "citationCount": 12,
            "venue": "Nature",
            "externalIds": {"DOI": "10.1000/test"},
            "openAccessPdf": {"url": "https://example.com/a.pdf"},
            "fieldsOfStudy": ["Materials Science"],
        },
        query="SnSe",
    )
    assert paper is not None
    assert paper.id == "S2-abc123"
    assert paper.source == "semantic_scholar"
    assert paper.doi == "10.1000/test"
    assert paper.oa_url.endswith(".pdf")
    assert paper.cited_by == 12


def test_client_sends_api_key_header(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "paperId": "p1",
                        "title": "T",
                        "year": 2021,
                        "authors": [],
                        "citationCount": 1,
                        "externalIds": {},
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            captured["headers"] = kwargs.get("headers") or {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = dict(params or {})
            return FakeResponse()

    monkeypatch.setattr(
        "materials_agent.tools.semantic_scholar_client.httpx.Client", FakeClient
    )
    out = SemanticScholarClient("secret-key").search("SnSe", limit=5, year_from=2018)
    assert captured["headers"]["x-api-key"] == "secret-key"
    assert captured["params"]["year"] == "2018-"
    assert len(out) == 1
    assert out[0].id == "S2-p1"


def test_retriever_falls_back_to_openalex(monkeypatch):
    calls: list[str] = []

    def boom(*args, **kwargs):
        raise httpx.HTTPError("429")

    def fake_oa(self, queries, cfg, audit, ontology=None):
        calls.append("openalex")
        return [
            Paper(id="W1", title="OA hit", source="openalex", abstract="SnSe"),
        ]

    monkeypatch.setattr(SemanticScholarClient, "search", boom)
    monkeypatch.setattr(
        "materials_agent.tools.retrievers.OpenAlexRetriever.search", fake_oa
    )
    cfg = AppConfig(
        topic="SnSe",
        max_papers=5,
        retrieval=RetrievalConfig(
            backend="semantic_scholar",
            semantic_scholar_api_key="k",
            multi_query=False,
        ),
    )
    audit: list = []
    out = SemanticScholarRetriever().search(["SnSe"], cfg, audit)
    assert calls == ["openalex"]
    assert out[0].source == "openalex"
    assert any(a.tool == "semantic_scholar" for a in audit)


def test_retriever_falls_back_on_tenacity_retry_error(monkeypatch):
    """Regression: exhausted @retry used to raise RetryError and skip OpenAlex fallback."""
    from tenacity import RetryError
    from unittest.mock import MagicMock

    calls: list[str] = []

    def boom(*args, **kwargs):
        req = httpx.Request("GET", "https://api.semanticscholar.org/graph/v1/paper/search")
        resp = httpx.Response(429, request=req)
        inner = httpx.HTTPStatusError("429", request=req, response=resp)
        fut = MagicMock()
        fut.exception = MagicMock(return_value=inner)
        raise RetryError(fut)

    def fake_oa(self, queries, cfg, audit, ontology=None):
        calls.append("openalex")
        return [Paper(id="W1", title="OA hit", source="openalex", abstract="SnSe")]

    monkeypatch.setattr(SemanticScholarClient, "search", boom)
    monkeypatch.setattr(
        "materials_agent.tools.retrievers.OpenAlexRetriever.search", fake_oa
    )
    cfg = AppConfig(
        topic="SnSe",
        max_papers=5,
        retrieval=RetrievalConfig(
            backend="semantic_scholar",
            semantic_scholar_api_key="",
            multi_query=False,
        ),
    )
    out = SemanticScholarRetriever().search(["SnSe"], cfg, [])
    assert calls == ["openalex"]
    assert out[0].id == "W1"
