"""Retrieval-backend honesty helpers for audit + verify."""

from __future__ import annotations

from typing import Any


STRICT_BACKENDS = {"sciverse", "semantic_scholar", "s2"}


class BackendFallbackError(RuntimeError):
    """Configured backend failed and silent OpenAlex fallback is forbidden."""


def retrieve_meta(
    *,
    configured: str,
    effective: str,
    fallback_reason: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = {
        "configured_backend": configured,
        "effective_backend": effective,
        "fallback": bool(fallback_reason) and effective != configured,
        "fallback_reason": fallback_reason,
    }
    if extra:
        meta.update(extra)
    return meta


def audit_effective_backend(audit: list[Any]) -> str | None:
    for event in reversed(audit):
        meta = getattr(event, "meta", None)
        if meta is None and isinstance(event, dict):
            if event.get("step") != "retrieve":
                continue
            meta = event.get("meta") or {}
        elif getattr(event, "step", None) != "retrieve":
            continue
        if isinstance(meta, dict) and meta.get("effective_backend"):
            return str(meta["effective_backend"])
    return None
