from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from materials_agent.config import LLMConfig


class LLMClient:
    """LLM adapter for OpenAI-compatible APIs or the Cursor SDK."""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self._client = None
        self._cursor_agent = None
        self.call_audit: list[dict[str, str]] = []
        self._cursor_disabled = False
        self._openai_disabled = False
        if cfg.available:
            self._initialize_provider()

    def _initialize_provider(self) -> None:
        try:
            if self.cfg.provider == "cursor_sdk" or self.cfg.cursor_api_key.strip():
                from cursor_sdk import Agent

                self._cursor_agent = Agent
            if self.cfg.provider == "openai" or self.cfg.api_key.strip():
                from openai import OpenAI

                if self.cfg.api_key.strip():
                    self._client = OpenAI(
                        api_key=self.cfg.api_key,
                        base_url=self.cfg.base_url or "https://api.openai.com/v1",
                        timeout=45.0,
                    )
        except Exception:
            # Keep whichever backend initialized successfully.
            pass

    @property
    def enabled(self) -> bool:
        if self.cfg.provider == "cursor_sdk":
            return self._cursor_agent is not None or self._client is not None
        return self._client is not None or self._cursor_agent is not None

    def chat_text(
        self,
        system: str,
        user: str,
        *,
        step: str = "extract",
    ) -> str | None:
        if not self.enabled:
            return None
        model, temperature = self.cfg.resolve(step)
        primary = self.cfg.provider
        if primary == "cursor_sdk" and self._cursor_agent is not None and not self._cursor_disabled:
            text = self._cursor_chat_text(system, user, model, step)
            if text:
                return text
            # Windows bridge failures (e.g. WinError 10038) should not be retried every call.
            if any(
                a.get("step") == step and str(a.get("status", "")).startswith("error:OSError")
                for a in self.call_audit[-2:]
            ):
                self._cursor_disabled = True
            if self._client is not None:
                return self._openai_chat_text(
                    system, user, self.cfg.model or model, temperature, step, fallback=True
                )
            return None
        if primary == "cursor_sdk" and self._cursor_disabled and self._client is not None:
            return self._openai_chat_text(
                system, user, self.cfg.model or model, temperature, step, fallback=True
            )
        if self._client is not None and not self._openai_disabled:
            text = self._openai_chat_text(system, user, model, temperature, step)
            if text:
                return text
            if self._cursor_agent is not None and not self._cursor_disabled:
                return self._cursor_chat_text(
                    system, user, self.cfg.cursor_model or model, step, fallback=True
                )
            return None
        if self._cursor_agent is not None and not self._cursor_disabled:
            return self._cursor_chat_text(system, user, model, step)
        return None

    def _openai_chat_text(
        self,
        system: str,
        user: str,
        model: str,
        temperature: float,
        step: str,
        *,
        fallback: bool = False,
    ) -> str | None:
        if self._openai_disabled or self._client is None:
            return None
        try:
            resp = self._client.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=self.cfg.max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = resp.choices[0].message.content
            self.call_audit.append(
                {
                    "step": step,
                    "provider": "openai" + ("_fallback" if fallback else ""),
                    "model": model,
                    "agent_id": "",
                    "run_id": "",
                    "status": "finished" if text else "empty",
                }
            )
            return text
        except Exception as exc:
            name = type(exc).__name__
            self.call_audit.append(
                {
                    "step": step,
                    "provider": "openai" + ("_fallback" if fallback else ""),
                    "model": model,
                    "agent_id": "",
                    "run_id": "",
                    "status": f"error:{name}",
                }
            )
            # Quota / auth failures are sticky for this process.
            if name in {"RateLimitError", "AuthenticationError", "PermissionDeniedError"}:
                self._openai_disabled = True
            return None

    def _cursor_chat_text(
        self,
        system: str,
        user: str,
        model: str,
        step: str,
        *,
        fallback: bool = False,
    ) -> str | None:
        """Run a bounded one-shot SDK agent and retain only non-secret audit metadata."""
        if self._cursor_agent is None:
            return None

        prompt = (
            f"{system}\n\n{user}\n\n"
            "Return only the requested answer. Do not edit files, run commands, "
            "or call external tools."
        )
        try:
            from cursor_sdk import LocalAgentOptions

            workspace = str(Path(self.cfg.cursor_workspace).resolve())
            with self._cursor_agent.create(
                model=model,
                api_key=self.cfg.cursor_api_key,
                local=LocalAgentOptions(cwd=workspace),
            ) as agent:
                run = agent.send(prompt)
                result = run.wait()
                self.call_audit.append(
                    {
                        "step": step,
                        "provider": "cursor_sdk" + ("_fallback" if fallback else ""),
                        "model": model,
                        "agent_id": str(getattr(agent, "agent_id", "")),
                        "run_id": str(getattr(result, "id", "")),
                        "status": str(getattr(result, "status", "unknown")),
                    }
                )
                if getattr(result, "status", "") != "finished":
                    return None
                text = getattr(result, "result", None)
                return text if isinstance(text, str) else None
        except Exception as exc:
            self.call_audit.append(
                {
                    "step": step,
                    "provider": "cursor_sdk" + ("_fallback" if fallback else ""),
                    "model": model,
                    "agent_id": "",
                    "run_id": "",
                    "status": f"error:{type(exc).__name__}:{exc}",
                }
            )
            return None

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        step: str = "extract",
        validator: Callable[[dict[str, Any]], bool] | None = None,
    ) -> dict[str, Any] | None:
        retries = max(1, self.cfg.max_retries + 1)
        last_err = ""
        for attempt in range(retries):
            hint = ""
            if attempt and last_err:
                hint = f"\nPrevious output failed validation: {last_err}\nFix and return valid JSON only."
            text = self.chat_text(
                system,
                user + "\n\nRespond with valid JSON only." + hint,
                step=step,
            )
            if not text:
                return None
            data = self._parse_json(text)
            if data is None:
                last_err = "JSON parse error"
                continue
            if validator and not validator(data):
                last_err = "schema/validator rejected payload"
                continue
            return data
        return None

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any] | None:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start >= 0 and end > start:
                try:
                    data = json.loads(text[start : end + 1])
                    return data if isinstance(data, dict) else None
                except json.JSONDecodeError:
                    return None
            return None
