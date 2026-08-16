"""Probe Minimax OpenAI-compatible auth without printing secrets."""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=True)

key = (os.environ.get("OPENAI_API_KEY") or "").strip().strip("'\"")
model = (os.environ.get("OPENAI_MODEL") or "MiniMax-M3").strip().strip("'\"")
configured = (os.environ.get("OPENAI_BASE_URL") or "").strip().rstrip("/")

hosts = []
for h in (configured, "https://api.minimaxi.com/v1", "https://api.minimax.io/v1"):
    if h and h not in hosts:
        hosts.append(h)

print(f"key_present={bool(key)} prefix={(key[:6] + '...') if len(key) >= 6 else ''} len={len(key)}")
print(f"model={model}")
print(f"configured_base={configured}")

payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Reply with exactly PONG"}],
    "max_tokens": 16,
}
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

ok_host = None
for base in hosts:
    try:
        r = httpx.post(f"{base}/chat/completions", headers=headers, json=payload, timeout=45.0)
        snip = r.text[:220].replace(key[:10], "***") if key else r.text[:220]
        print(f"TRY {base} -> HTTP {r.status_code} | {snip}")
        if r.status_code < 400:
            ok_host = base
            break
    except httpx.HTTPError as exc:
        print(f"TRY {base} -> ERROR {type(exc).__name__}: {str(exc)[:160]}")

print(f"RESULT ok_host={ok_host or 'NONE'}")
raise SystemExit(0 if ok_host else 1)
