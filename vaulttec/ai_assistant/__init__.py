"""AI Assistant — Jarvis-style, rule-based in Phase 2, LLM-ready via llm_hook."""
from .assistant import Assistant
from .llm_hook import LLMProvider, NoLLMProvider

__all__ = ["Assistant", "LLMProvider", "NoLLMProvider"]
