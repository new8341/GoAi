import sys
from types import SimpleNamespace

from materials_agent.config import LLMConfig
from materials_agent.llm import LLMClient


class _FakeRun:
    def wait(self):
        return SimpleNamespace(status="finished", result='{"queries":["SnSe"]}', id="run-1")


class _FakeAgent:
    agent_id = "agent-1"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def send(self, prompt):
        assert "Do not edit files" in prompt
        return _FakeRun()


class _FakeCursorAgent:
    @staticmethod
    def create(**kwargs):
        assert kwargs["api_key"] == "cursor_test"
        assert kwargs["model"] == "composer-2.5"
        return _FakeAgent()


class _FakeLocalAgentOptions:
    def __init__(self, *, cwd):
        self.cwd = cwd


def test_cursor_sdk_backend_returns_text_and_audits_run(monkeypatch, tmp_path):
    monkeypatch.setitem(
        sys.modules,
        "cursor_sdk",
        SimpleNamespace(
            Agent=_FakeCursorAgent,
            LocalAgentOptions=_FakeLocalAgentOptions,
        ),
    )
    client = LLMClient(
        LLMConfig(
            provider="cursor_sdk",
            cursor_api_key="cursor_test",
            cursor_workspace=str(tmp_path),
        )
    )

    assert client.enabled
    assert client.chat_text("System", "User", step="extract") == '{"queries":["SnSe"]}'
    assert client.call_audit == [
        {
            "step": "extract",
            "provider": "cursor_sdk",
            "model": "composer-2.5",
            "agent_id": "agent-1",
            "run_id": "run-1",
            "status": "finished",
        }
    ]


def test_cursor_sdk_provider_uses_cursor_model_and_key():
    cfg = LLMConfig(
        provider="cursor_sdk",
        cursor_api_key="cursor_test",
        cursor_model="composer-2.5",
    )

    assert cfg.available
    assert cfg.resolve("gap")[0] == "composer-2.5"
