"""Ava's memory — how she learns from mistakes.

Every closed paper trade gets one lesson, written to
``data/ava-lessons.jsonl`` on this PC only (local, never pushed to
GitHub, never shared). A lesson records the symbol, whether the trade
won or lost, what the setup was, and the takeaway in plain language:

- A loss that hit its stop is NOT a failure of the stop — the stop did
  its job and kept the loss small. The lesson is about the setup.
- A win is a lesson about what to repeat.
- A trade closed early, or a setup that kept losing, is a lesson about
  patience and selection, not about chasing the money back.

``review_closed_trades`` finds closed trades with no lesson yet and
writes one each, so Ava's memory grows as the journal grows. Lessons
are read back into every answer, so a mistake made once gets brought
up before the same setup is traded again.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def lessons_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "ava-lessons.jsonl"


def _lesson_for(trade) -> dict:
    won = (trade.pnl or 0) > 0
    if trade.status != "closed":
        return {}
    if won:
        takeaway = (
            f"{trade.symbol} won ${trade.pnl:,.2f}. The setup worked — "
            "repeat the conditions that made it, do not enlarge it "
            "just because it won once."
        )
    else:
        takeaway = (
            f"{trade.symbol} lost ${abs(trade.pnl):,.2f}. The stop did "
            "its job and kept the loss planned and small — do not chase "
            "it back. Re-check the setup before trading this pattern again."
        )
    return {
        "when": datetime.utcnow().isoformat(),
        "symbol": trade.symbol,
        "side": trade.side,
        "entry": trade.price,
        "pnl": round(trade.pnl or 0, 2),
        "won": won,
        "source": trade.source,
        "lesson": takeaway,
    }


def learn_from_trade(trade) -> dict | None:
    """Write one lesson for a closed trade. Returns the lesson, or None
    when the trade is still open (nothing to learn yet)."""
    lesson = _lesson_for(trade)
    if not lesson:
        return None
    path = lessons_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(lesson) + "\n")
    return lesson


def review_closed_trades(engine) -> list[dict]:
    """Learn from every closed trade that has no lesson yet. Returns the
    new lessons (empty when the journal is already fully reviewed)."""
    existing = {(r.get("symbol"), r.get("pnl")) for r in load_lessons(limit=1000)}
    new = []
    for trade in engine.trades:
        if trade.status != "closed":
            continue
        if (trade.symbol, round(trade.pnl or 0, 2)) in existing:
            continue
        lesson = learn_from_trade(trade)
        if lesson:
            new.append(lesson)
            existing.add((trade.symbol, round(trade.pnl or 0, 2)))
    return new


def load_lessons(limit: int = 20) -> list[dict]:
    """Most recent lessons, newest first. Empty list when none exist."""
    path = lessons_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]
