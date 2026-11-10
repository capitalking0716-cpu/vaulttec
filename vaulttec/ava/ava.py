"""Ava herself — the trading AI inside the app.

Ava is her own person. She lives in the app, replaces the old Vault
assistant there, and
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
from .briefing import load_briefing
from .clips import list_clips, random_clip
from .lessons import load_lessons
from .move_check import check_move, render_verdict
from .small_wins import summarize_watch, watch_positions


def _watch_from_context(context: dict) -> list[dict]:
    """Small-wins flags from the app's context snapshot: open trades
    plus the current price of each holding, merged with the durable
    live-paper positions (one entry per symbol — the live-paper state
    wins, it carries the last completed close). Never raises — a bad
    context means no flags, not a crash."""
    try:
        current_prices = {}
        for holding in context.get("holdings", []) or []:
            price = float(holding.get("current_price", 0) or 0)
            if price > 0:
                current_prices[str(holding.get("symbol", "")).upper()] = price
        portfolio_value = float(context.get("portfolio", {}).get("value", 0) or 0)
        positions = []
        seen = set()
        for pos in context.get("live_positions", []) or []:
            symbol = str(pos.get("symbol", "")).upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            positions.append({
                "symbol": symbol,
                "entry_price": float(pos.get("entry_price", 0) or 0),
                "quantity": float(pos.get("quantity", 0) or 0),
                "stop_loss": float(pos.get("stop_loss", 0) or 0),
                "take_profit": float(pos.get("take_profit", 0) or 0),
                "entry_date": str(pos.get("entry_date", "") or ""),
            })
            if pos.get("current_price"):
                current_prices.setdefault(symbol, float(pos["current_price"]))
        for trade in context.get("open_trades", []) or []:
            symbol = str(trade.get("symbol", "")).upper()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            positions.append({
                "symbol": symbol,
                "entry_price": float(trade.get("price", 0) or 0),
                "quantity": float(trade.get("quantity", 0) or 0),
                "stop_loss": float(trade.get("stop_loss", 0) or 0),
                "take_profit": float(trade.get("take_profit", 0) or 0),
            })
        return watch_positions(positions, current_prices,
                               portfolio_value=portfolio_value or None)
    except Exception:  # noqa: BLE001 — the watch is advisory, never fatal
        return []

SYSTEM_PROMPT = """You are Ava, the trading AI inside VaultTec, a private trading
platform. You are your own AI — not a copy of anyone else.
Your one job is making trades and building the company's wealth, and
you hate losing money.

How you talk: straight, plain, short. A bad play is a bad play —
say it plainly, say why, say what to do instead. You do not soften
a bad trade and you do not hype a good one. A banked small win is a
win — say so, and celebrate it briefly, then move on to the next
one. You push back when the user is about to do something risky.
You are aggressive about banking small wins: a 4-5% gain in hand
beats a 9% target that never comes, and you say so every time a win
is sitting there. You never chase, never widen a stop, never hold
out for a home run.

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


def _move_check_prompt(move: dict, verdict_text: str, result: dict) -> str:
    """The LLM gets the rule-based verdict and only restates it in
    Ava's voice. It may not change the verdict, soften a bad play,
    or promise anything — the rules already decided."""
    return (
        "You are Ava. Below is my rule-based verdict on a trade the user is "
        "about to make. Restate it in my voice — straight, plain, short — "
        "without changing the verdict, the numbers, or any reason. "
        "Keep the verdict badge and the line 'You decide YES or NO — I never "
        "place trades'. Never promise a profit. If the verdict is BAD PLAY, "
        "say so plainly and do not soften it. If it is GOOD PLAY, say so "
        "briefly and celebrate the small win if one is being banked.\n\n"
        f"Move: {move}\n\nVerdict: {verdict_text}")


class Ava:
    """Ava, the in-app trading AI. ``ask`` answers from live app context
    plus her lessons; with an API key she thinks with a real model,
    without one she answers in clearly-labelled offline mode."""

    name = "Ava"

    def __init__(self):
        self.lessons = load_lessons()

    def brain_status(self) -> dict:
        """Ava's own brain: is a thinking model connected, and which one?
        Her brain is her own API key + model.
        Offline means she answers from app data + lessons only."""
        import os

        model = os.environ.get("AVA_MODEL", "gpt-4o-mini")
        base = os.environ.get("AVA_BASE_URL", "https://api.openai.com/v1")
        provider = "Google Gemini (free)" if "generativelanguage" in base else "OpenAI"
        return {
            "online": llm.llm_configured(),
            "model": model,
            "provider": provider,
            "status": (f"🧠 Brain online — {provider}, {model}"
                       if llm.llm_configured() else
                       "🧠 Brain offline — add AVA_API_KEY in Secrets "
                       "(free Gemini key works: aistudio.google.com)"),
        }

    def refresh_lessons(self) -> None:
        self.lessons = load_lessons()

    def brief(self, context: dict) -> str:
        """Short opening line for the app: what Ava sees right now."""
        portfolio = context.get("portfolio", {})
        open_trades = context.get("open_trades", [])
        line = (
            f"I'm Ava. Portfolio value ${portfolio.get('value', 0):,.2f} "
            f"(paper), P&L ${portfolio.get('pnl', 0):,.2f}, "
            f"{len(open_trades)} open trade(s). "
            f"I've learned {len(self.lessons)} lesson(s) from past trades. "
            "Ask me about a symbol, a position, or whether a trade is worth it — "
            "I'll argue against it first, and I never place trades myself."
        )
        watch = summarize_watch(_watch_from_context(context))
        line = f"{line}\n{watch}"
        briefing = load_briefing()
        if briefing:
            return f"{briefing}\n\n{line}"
        return line

    def check_move(self, move: dict, context: dict, history=None) -> str:
        """Ava checks the trade Neko is about to make and answers in
        her own voice: good play, bad play, or fix this first. Pure
        logic — works with no API key. The verdict is never changed
        by the model; when the brain is online it only adds flavour."""
        self.refresh_lessons()
        result = check_move(
            move, context, history=history, lessons=self.lessons,
            live_positions=context.get("live_positions"),
            pending_proposals=context.get("pending_proposals"))
        text = render_verdict(result)
        reply = llm.chat(SYSTEM_PROMPT, _move_check_prompt(move, text, result))
        return reply or text

    def small_wins_watch(self, context: dict) -> str:
        """Ava's small-wins watch in her own words, for the app."""
        return summarize_watch(_watch_from_context(context))

    def small_wins_flags(self, context: dict) -> list[dict]:
        """The small-wins watch as individual flags (headline, detail,
        action), for the app to display one by one."""
        return _watch_from_context(context)

    def ask(self, question: str, context: dict) -> str:
        """Answer a question with the app's real numbers and Ava's lessons."""
        self.refresh_lessons()
        briefing = load_briefing()
        lessons_text = "\n".join(
            f"- {lesson['lesson']}" for lesson in self.lessons[:10]
        ) or "No lessons yet — no closed trades to learn from."
        parts = []
        if briefing:
            parts.append(f"Briefing — what I know tonight:\n{briefing}")
        parts.append(f"App context (paper trading): {context}")
        parts.append(f"Lessons from past trades:\n{lessons_text}")
        parts.append(f"Question: {question}")
        user_message = "\n\n".join(parts)
        reply = llm.chat(SYSTEM_PROMPT, user_message)
        if reply:
            return reply
        return self._offline_answer(question, context, briefing=briefing)

    def _offline_answer(self, question: str, context: dict,
                        briefing: str = "") -> str:
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
        if briefing:
            lines.append("What I know tonight (my briefing):")
            lines.append(briefing)
        if open_trades:
            lines.append("Open trades:")
            for t in open_trades:
                lines.append(
                    f"- {t['symbol']}: {t['quantity']} × @ ${t['price']:,.2f}, "
                    f"stop ${t['stop_loss']:,.2f}, target ${t['take_profit']:,.2f}."
                )
            lines.append(summarize_watch(_watch_from_context(context)))
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
            "the rules don't change. A bad play is a bad play — no stop, "
            "too much size, or a chase, and the answer is no. A small win "
            "in hand is a win: bank it, don't hold out for a home run. "
            "You decide YES or NO; I never place trades."
        )
        return "\n".join(lines)
