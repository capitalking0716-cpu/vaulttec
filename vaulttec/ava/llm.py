"""Ava's connection to a real thinking model (optional).

Ava is her own AI. To actually *think* she needs
a model API key: ``AVA_API_KEY`` (or ``OPENAI_API_KEY``) in Streamlit
Secrets or ``.env``, with an optional ``AVA_MODEL`` (default
``gpt-4o-mini``) and ``AVA_BASE_URL`` for any OpenAI-compatible
endpoint. The key is read from the environment only — it is never
written to a file, never shown in the UI, and never pushed to GitHub.

Without a key, ``chat()`` returns ``None`` and Ava answers in offline
mode from the app's own data and her lessons, clearly labelled as such.
She never pretends to be thinking when she is not.
"""
from __future__ import annotations

import json
import os
import urllib.request


def llm_configured() -> bool:
    """True when an API key is available for Ava to think with."""
    return bool(os.environ.get("AVA_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def chat(system_prompt: str, user_message: str, timeout: int = 30) -> str | None:
    """One chat-completions call. Returns the reply text, or None on any
    failure (no key, no network, bad key, bad response). Callers fall
    back to offline mode — they never crash and never invent a reply.
    """
    key = os.environ.get("AVA_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    base = os.environ.get("AVA_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("AVA_MODEL", "gpt-4o-mini")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 600,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 — any LLM failure means offline mode
        return None
    try:
        return payload["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        return None
