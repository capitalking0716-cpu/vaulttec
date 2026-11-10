"""Shadow bridge — the link between the VaultTec app and Shadow (Muse).

Shadow does not run inside Streamlit: the app is a local program on
the user's PC, and Shadow is the chat assistant. This bridge is the
honest version of "merge with the app":

- The app builds a context snapshot (positions, P&L, today's signals,
  risk limits, profile) and shows it in the Shadow tab, so a question
  asked there carries the user's real numbers, not generic text.
- A question typed in the app is saved to ``data/shadow-questions.jsonl``
  on this PC (local only, never pushed to GitHub). When the user talks
  to Shadow in chat, Shadow reads that file and answers with the app's
  actual state in front of it.
- Answers Shadow gives in chat can be saved back by the user into
  ``data/shadow-notes.md``; the app shows those notes in the Shadow tab.

No network calls, no keys, no credentials in this module. Nothing here
trades, and nothing here sends anything anywhere on its own.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def bridge_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def questions_path() -> Path:
    return bridge_dir() / "shadow-questions.jsonl"


def notes_path() -> Path:
    return bridge_dir() / "shadow-notes.md"


def build_context_snapshot(profile, portfolio, engine, signals, prices,
                           cash: float, value: float, pnl: float) -> dict:
    """Plain-language snapshot of the app's current state, for Shadow."""
    holdings = [
        {"symbol": s, "quantity": h.quantity, "avg_cost": h.avg_cost,
         "current_price": prices.get(s, h.avg_cost),
         "value": h.quantity * prices.get(s, h.avg_cost)}
        for s, h in portfolio.holdings.items()
    ]
    open_trades = [
        {"symbol": t.symbol, "side": t.side, "quantity": t.quantity,
         "price": t.price, "stop_loss": t.stop_loss,
         "take_profit": t.take_profit, "status": t.status}
        for t in engine.trades if t.status == "open"
    ]
    return {
        "when": datetime.utcnow().isoformat(),
        "user": {"name": profile.name, "goal": profile.goal,
                 "risk_tolerance": profile.risk_tolerance,
                 "max_position_pct": profile.max_position_pct,
                 "daily_loss_limit_pct": profile.daily_loss_limit_pct,
                 "allowed_markets": list(profile.allowed_markets)},
        "portfolio": {"cash": round(cash, 2), "value": round(value, 2),
                      "pnl": round(pnl, 2)},
        "holdings": holdings,
        "open_trades": open_trades,
        "closed_trades": sum(1 for t in engine.trades if t.status == "closed"),
        "signals": [
            {"symbol": s.symbol, "direction": s.direction,
             "confidence": round(s.confidence, 2)} for s in signals
        ],
    }


def save_question(question: str, context: dict) -> Path:
    """Save one question + its context snapshot. Returns the file."""
    path = questions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"asked_at": datetime.utcnow().isoformat(),
              "question": question.strip(), "context": context}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    return path


def load_questions(limit: int = 10) -> list[dict]:
    """Most recent saved questions, newest first. Empty list when none."""
    path = questions_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]


def load_notes() -> str:
    """Shadow's notes the user saved back into the app (may be empty)."""
    path = notes_path()
    return path.read_text(encoding="utf-8") if path.exists() else ""
