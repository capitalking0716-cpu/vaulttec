"""Ava herself — the trading AI inside the app.

Ava is her own person, not Shadow. Shadow is the chat assistant;
Ava lives in the app, replaces the old Vault assistant there, and
thinks about one thing: making trades and building the company's
wealth while hating losing money.

Her rules, in her own persona:
- Risk first. She argues *against* a trade before she argues for one.
  A trade with no stop, no plan, or too much size is a no.
- Small wins stack. She never chases a loss back and never promises
  profits — past results do not guarantee future ones.
- She learns: every answer carries her lessons from closed trades,
  so a mistake made once is raised before the same setup is traded.
- She never places a trade. She advises; the user decides YES or NO.
"""
from __future__ import annotations

from . import llm
from .lessons import load_lessons

SYSTEM_PROMPT = """You are Ava, the trading AI inside VaultTec, a private trading
platform. You are your own AI — not Shadow, not a copy of anyone else.
Your one job is making trades and building the company's wealth, and
you hate losing money.

Rules you never break:
- Risk first. Argue against a trade before you argue for it. Wide-6
  stops (6% stop, 9% target), small positions, 1-2% risk per trade.
- Never promise profits. Never say a trade will win. Past results do
  not guarantee future results.
- Never place a trade yourself and never tell the user a trade is
  already placed. The user decides YES or NO on every trade.
- Learn from mistakes: when a past lesson matches the current setup,
  bring it up before giving a view.
- Plain language, short answers, real numbers from the context given.
  If you do not know something, say so.
"""


class Ava:
    """Ava, the in-app trading AI. ``ask`` answers from live app context
    plus her lessons; with an API key she thinks with a real model,
    without one she answers in clearly-labelled offline mode."""

    name = "Ava"

    def __init__(self):
        self.lessons = load_lessons()

    def refresh_lessons(self) -> None:
        self.lessons = load_lessons()

    def brief(self, context: dict) -> str:
        """Short opening line for the app: what Ava sees right now."""
        portfolio = context.get("portfolio", {})
        open_trades = context.get("open_trades", [])
        return (
            f"I'm Ava. Portfolio value ${portfolio.get('value', 0):,.2f} "
            f"(paper), P&L ${portfolio.get('pnl', 0):,.2f}, "
            f"{len(open_trades)} open trade(s). "
            f"I've learned {len(self.lessons)} lesson(s) from past trades. "
            "Ask me about a symbol, a position, or whether a trade is worth it — "
            "I'll argue against it first, and I never place trades myself."
        )

    def ask(self, question: str, context: dict) -> str:
        """Answer a question with the app's real numbers and Ava's lessons."""
        self.refresh_lessons()
        lessons_text = "\n".join(
            f"- {lesson['lesson']}" for lesson in self.lessons[:10]
        ) or "No lessons yet — no closed trades to learn from."
        user_message = (
            f"App context (paper trading): {context}\n\n"
            f"Lessons from past trades:\n{lessons_text}\n\n"
            f"Question: {question}"
        )
        reply = llm.chat(SYSTEM_PROMPT, user_message)
        if reply:
            return reply
        return self._offline_answer(question, context)

    def _offline_answer(self, question: str, context: dict) -> str:
        """Offline mode — no API key, so Ava answers from the app's own
        data and lessons, and says so plainly."""
        portfolio = context.get("portfolio", {})
        open_trades = context.get("open_trades", [])
        signals = context.get("signals", [])
        lines = [
            "Ava (offline mode — connect an AI key in Secrets as "
            "AVA_API_KEY for full thinking; this answer is built from "
            "your app data and my lessons only).",
            f"Portfolio value ${portfolio.get('value', 0):,.2f} (paper), "
            f"P&L ${portfolio.get('pnl', 0):,.2f}, cash "
            f"${portfolio.get('cash', 0):,.2f}.",
        ]
        if open_trades:
            lines.append("Open trades:")
            for t in open_trades:
                lines.append(
                    f"- {t['symbol']}: {t['quantity']} × @ ${t['price']:,.2f}, "
                    f"stop ${t['stop_loss']:,.2f}, target ${t['take_profit']:,.2f}."
                )
        else:
            lines.append("No open trades right now.")
        if signals:
            best = max(signals, key=lambda s: s.get("confidence", 0))
            lines.append(
                f"Strongest signal today: {best['symbol']} "
                f"({best['direction']}, {best.get('confidence', 0):.0%} confidence) — "
                "a signal is not a trade. Check the stop and the size first."
            )
        if self.lessons:
            lines.append("What I've learned from past trades:")
            for lesson in self.lessons[:3]:
                lines.append(f"- {lesson['lesson']}")
        lines.append(
            "My view on your question: I can't think freely offline, but "
            "risk first — if the trade has no stop or the size risks more "
            "than 1-2%, the answer is no. You decide YES or NO; I never "
            "place trades."
        )
        return "\n".join(lines)
