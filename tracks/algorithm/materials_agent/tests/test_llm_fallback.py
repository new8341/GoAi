"""OpenAI fallback when Cursor SDK primary fails."""

import sys
from types import SimpleNamespace

from materials_agent.config import LLMConfig
from materials_agent.llm import LLMClient


class _BoomCursor:
    @staticmethod
    def create(**_kwargs):
        raise OSError("WinError 10038")


class _FakeCompletion:
    def __init__(self, text: str):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


class _FakeOpenAI:
    def __init__(self, *_args, **_kwargs):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **_kw: _FakeCompletion('{"ok":true}')
            )
        )


def test_cursor_primary_falls_back_to_openai(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "cursor_sdk",
        SimpleNamespace(Agent=_BoomCursor, LocalAgentOptions=lambda **kw: kw),
    )
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=_FakeOpenAI))
    client = LLMClient(
        LLMConfig(
            provider="cursor_sdk",
            cursor_api_key="cursor_test",
            api_key="openai_test",
            model="gpt-4o-mini",
        )
    )
    assert client.enabled
    assert client.chat_text("sys", "user", step="extract") == '{"ok":true}'
    assert any(a["provider"] == "openai_fallback" for a in client.call_audit)
