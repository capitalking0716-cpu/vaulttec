"""Ava's briefing — the note she reads before every answer.

``vaulttec/ava/briefing.md`` is a repo file (not ``data/``): it
travels with the code to Neko's PC, so Ava always knows the current
plan, the latest test verdicts, and what is still untested. It holds
status and strategy only — never secrets, API keys, account numbers,
or personal data.

``load_briefing`` returns ``""`` when the file is missing or
unreadable. It never raises and never logs anything sensitive.
"""
from __future__ import annotations

from pathlib import Path


def briefing_path() -> Path:
    return Path(__file__).resolve().parent / "briefing.md"


def load_briefing() -> str:
    """Tonight's briefing text, or "" when the file is missing or
    unreadable. Never raises, never logs anything."""
    try:
        path = briefing_path()
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""
