"""Signal history + accuracy tracking (Phase 2).

Every generated signal is recorded with its direction, confidence,
and evidence. Later, once enough days have passed, the outcome is
checked against what the price actually did — that is how VaultTec
learns whether its signals are worth anything, instead of claiming
accuracy it has never measured.

Outcome rule (simple, honest, and stated on the record): for a
``long`` signal, the outcome is a win if the close ``days_ahead``
later is higher than the close on the signal day; for ``short``,
if it is lower. Neutral signals have no outcome — they made no call.
Accuracy is only reported once at least 10 outcomes exist; before
that the tracker says "not enough data yet" instead of inventing a
percentage.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..db.database import get_connection
from ..db.models import Signal

MIN_OUTCOMES_FOR_ACCURACY = 10

SCHEMA_EXTRA = """
CREATE TABLE IF NOT EXISTS signal_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, direction TEXT, confidence REAL, evidence TEXT,
    price_at_signal REAL, outcome TEXT, outcome_price REAL,
    created_at TEXT
);
"""


def init_signal_history(db_path: str | Path) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_EXTRA)
        conn.commit()


def record_signal(db_path: str | Path, signal: Signal, price_at_signal: float) -> int:
    """Record a signal. Returns the row id. Outcome is NULL until resolved."""
    init_signal_history(db_path)
    with get_connection(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO signal_history (symbol, direction, confidence, evidence, "
            "price_at_signal, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (signal.symbol, signal.direction, signal.confidence, signal.evidence,
             price_at_signal, signal.created_at))
        conn.commit()
        return cur.lastrowid


def get_signal_history(db_path: str | Path, limit: int = 50) -> list[dict]:
    """Most recent signals, newest first."""
    init_signal_history(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM signal_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def resolve_outcomes(db_path: str | Path, price_lookup) -> int:
    """Resolve unresolved signals using ``price_lookup(symbol, date)``,
    which returns the close price on/after a date (or None). A signal
    is resolved when a price at least 5 days after the signal day is
    available. Returns the number of signals resolved.
    """
    from datetime import timedelta

    init_signal_history(db_path)
    resolved = 0
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM signal_history WHERE outcome IS NULL").fetchall()
        for row in rows:
            if row["direction"] == "neutral":
                conn.execute("UPDATE signal_history SET outcome = 'no_call' WHERE id = ?",
                             (row["id"],))
                resolved += 1
                continue
            signal_date = datetime.fromisoformat(row["created_at"])
            later = price_lookup(row["symbol"], signal_date + timedelta(days=5))
            if later is None:
                continue
            entry = row["price_at_signal"]
            if row["direction"] == "long":
                outcome = "win" if later > entry else "loss"
            else:
                outcome = "win" if later < entry else "loss"
            conn.execute("UPDATE signal_history SET outcome = ?, outcome_price = ? WHERE id = ?",
                         (outcome, later, row["id"]))
            resolved += 1
        conn.commit()
    return resolved


def accuracy_summary(db_path: str | Path) -> dict:
    """Accuracy so far — or an honest 'not enough data yet'.

    Returns {"total", "wins", "losses", "accuracy_pct" | None, "note"}.
    """
    init_signal_history(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT outcome, COUNT(*) AS n FROM signal_history "
            "WHERE outcome IN ('win', 'loss') GROUP BY outcome").fetchall()
    counts = {r["outcome"]: r["n"] for r in rows}
    wins, losses = counts.get("win", 0), counts.get("loss", 0)
    total = wins + losses
    if total < MIN_OUTCOMES_FOR_ACCURACY:
        return {"total": total, "wins": wins, "losses": losses, "accuracy_pct": None,
                "note": f"Not enough data yet — only {total} resolved signal(s) so far. "
                        f"Accuracy needs at least {MIN_OUTCOMES_FOR_ACCURACY} before it means anything."}
    return {"total": total, "wins": wins, "losses": losses,
            "accuracy_pct": round(wins / total * 100, 1),
            "note": "Historical signal accuracy. Past performance does not guarantee future results."}
