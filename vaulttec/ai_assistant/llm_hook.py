"""LLM hook (Phase 2) — where a language model plugs in later.

Phase 2 keeps the assistant local and rule-based: no paid LLM API,
no API keys, nothing sent anywhere. This module defines the *shape*
a future LLM backend must fit, so swapping it in later means writing
one adapter, not rewriting the assistant.

Contract for any future LLM provider:
- ``complete(prompt, context) -> str`` — returns plain text only.
- It must never invent a price, a prediction, or a guarantee.
- It must say "I don't know" when the context has no data for the question.
- It must cite the evidence it used (indicator values, signal checks).
- It must never place, suggest, or approve a trade that bypasses the
  Risk Engine, and never promise profits.

``NoLLMProvider`` is the Phase 2 default: it raises a clear error so
no code can silently pretend an LLM answered.
"""
from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Interface a future LLM backend must implement."""

    def complete(self, prompt: str, context: dict | None = None) -> str:
        """Return a plain-text answer grounded in ``context``. Must not
        invent prices, predictions, or guarantees."""
        ...


class NoLLMProvider:
    """Phase 2 default — no LLM is connected. Any call fails loudly
    instead of faking an answer."""

    def complete(self, prompt: str, context: dict | None = None) -> str:
        raise RuntimeError(
            "No LLM provider is configured in Phase 2. VaultTec's assistant "
            "is rule-based and local for now — no paid API, no API keys. "
            "To add an LLM later, implement the LLMProvider protocol in "
            "ai_assistant/llm_hook.py and pass it to Assistant(llm=...)."
        )
