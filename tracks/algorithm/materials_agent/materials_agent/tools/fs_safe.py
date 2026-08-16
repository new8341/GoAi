"""Filesystem-safe name helpers (esp. Windows-invalid characters)."""

from __future__ import annotations

import re


_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def safe_fs_name(value: str, *, max_len: int = 120) -> str:
    """Sanitize a string for use as a file or directory name."""
    text = _INVALID.sub("_", (value or "").strip())
    text = re.sub(r"_+", "_", text).strip(" ._")
    if not text:
        text = "item"
    return text[:max_len].rstrip(" ._")
