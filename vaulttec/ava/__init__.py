"""Ava — the trading AI inside Neko's private VaultTec.

Ava is a trading-focused AI assistant who lives in the private app
and thinks about one thing — making trades and building the company's wealth, while hating
losing money. That means risk first: she argues *against* a trade
before she argues for one, she never promises profits, and she never
places a trade herself. The user decides YES or NO on every trade.

How Ava thinks:
- With an AI key set (``AVA_API_KEY`` / ``OPENAI_API_KEY`` in Secrets
  or ``.env``), she calls an OpenAI-compatible chat model with her
  persona, the live app context and her lessons, and answers in her
  own voice.
- Without a key she runs in offline mode: honest, rule-based answers
  built from the same context and lessons, clearly labelled offline.
  She never pretends to be thinking when she is not.

How Ava learns:
- After a paper trade closes, ``learn_from_trade`` writes a lesson to
  ``data/ava-lessons.jsonl`` (local only, never pushed). A loss that
  hit its stop is a lesson about the setup, not a failure of the
  stop — the stop did its job. A win is a lesson about what to repeat.
- Lessons are read back into every answer, so a mistake made once is
  brought up before the same setup is traded again.
"""
from __future__ import annotations

from .ava import Ava
from .briefing import load_briefing
from .clips import list_clips, random_clip
from .lessons import learn_from_trade, load_lessons, review_closed_trades
from .move_check import (check_move, load_live_paper_positions,
                         load_private_proposals, render_verdict)
from .paper_trading import load_evidence
from .small_wins import summarize_watch, watch_positions

__all__ = ["Ava", "learn_from_trade", "load_lessons", "review_closed_trades",
           "list_clips", "random_clip", "load_briefing", "load_evidence",
           "check_move", "render_verdict", "load_live_paper_positions",
           "load_private_proposals", "watch_positions", "summarize_watch"]
