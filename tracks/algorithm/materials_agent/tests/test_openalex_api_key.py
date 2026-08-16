"""OpenAlex API key wiring."""

from __future__ import annotations

from materials_agent.config import AppConfig, RetrievalConfig
from materials_agent.tools.retrievers import OpenAlexRetriever, resolve_openalex_api_key


def test_resolve_openalex_api_key_prefers_config(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    cfg = AppConfig(topic="SnSe", retrieval=RetrievalConfig(openalex_api_key="cfg-key"))
    assert resolve_openalex_api_key(cfg) == "cfg-key"


def test_resolve_openalex_api_key_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("OPENALEX_API_KEY", "env-key")
    cfg = AppConfig(topic="SnSe", retrieval=RetrievalConfig(openalex_api_key=""))
    assert resolve_openalex_api_key(cfg) == "env-key"


def test_openalex_fetch_sends_api_key(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"results": []}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = dict(params or {})
            return FakeResponse()

    monkeypatch.setattr("materials_agent.tools.retrievers.httpx.Client", FakeClient)
    cfg = AppConfig(
        topic="SnSe",
        max_papers=5,
        retrieval=RetrievalConfig(
            mailto="team@example.com",
            openalex_api_key="test-oa-key",
            multi_query=False,
        ),
    )
    OpenAlexRetriever()._fetch_one("SnSe thermal", cfg, per_page=5)
    assert captured["params"]["api_key"] == "test-oa-key"
    assert captured["params"]["mailto"] == "team@example.com"
