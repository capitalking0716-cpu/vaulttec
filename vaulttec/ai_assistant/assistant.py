"""VaultTec AI Assistant — Phase 2 expanded rule-based assistant.

Speaks like a professional financial intelligence analyst, not a
gambling tipster. It only answers from data it actually has, explains
its reasoning, and says "I don't know" when data is missing.
It never invents a price, a prediction, or a guarantee.

Phase 2 additions (all still local / rule-based — no paid LLM, no keys):
- market explanations (trend, RSI, MACD, Bollinger, volume, ATR),
- portfolio questions (value, holdings, exposure, P&L),
- trade analysis (a specific signal, its evidence, what could go wrong),
- strategy explanations (SMA crossover, MACD crossover, stop-loss,
  position sizing, diversification, risk/reward),
- daily market briefings (watchlist summary, top opportunities, risks).

An LLM can plug in later through ``llm_hook.LLMProvider`` — pass
``Assistant(llm=provider)`` and the assistant will ask the provider
for free-form answers, then still run the same honesty checks on the
result. With no provider (the default), every answer is rule-based.
"""
from __future__ import annotations

from .llm_hook import LLMProvider, NoLLMProvider

STRATEGIES = {
    "sma crossover": (
        "The SMA crossover strategy: buy when a short moving average (e.g. 10 days) "
        "crosses above a long one (e.g. 30 days), sell when it crosses back below. "
        "The idea is to ride a trend once it has started. The weakness: in a flat, "
        "choppy market it crosses back and forth and loses a little each time. "
        "It is a trend-following idea, not a guarantee — backtest it before trusting it."),
    "macd crossover": (
        "The MACD crossover strategy: buy when the MACD line crosses above its signal "
        "line, sell on the reverse cross. MACD measures momentum — how fast prices "
        "are moving — so this strategy follows momentum. The weakness: momentum can "
        "turn suddenly on news, and MACD lags the price because it is built from "
        "averages. One clue among several, never a signal on its own."),
    "stop-loss": (
        "A stop-loss is a price you set in advance: if the trade falls to it, the "
        "trade closes automatically. It is the single most important rule in VaultTec "
        "— no trade is allowed without one. It limits how much one bad trade can cost, "
        "so one mistake cannot wipe out the portfolio."),
    "position sizing": (
        "Position sizing is deciding how much of your money goes into one trade. "
        "VaultTec caps it by your risk profile — 5% per trade if you are conservative, "
        "10% balanced, 15% growth. Small positions mean a bad trade hurts a little; "
        "big positions mean a bad trade hurts a lot. Risk first, reward second."),
    "diversification": (
        "Diversification means not putting everything in one stock or one market. "
        "If one holding falls, the others can cushion it. VaultTec watches concentration "
        "— no single holding above your profile's limit — for exactly this reason."),
    "risk/reward": (
        "Risk/reward asks: if this trade can lose $10, how much can it make? VaultTec "
        "requires at least 1.5:1 — risk $10 to make $15. A trade that risks more than "
        "it can make needs to be right most of the time just to break even, and "
        "nobody is right most of the time."),
    "bollinger": (
        "Bollinger Bands wrap a price in two bands, two standard deviations above and "
        "below its 20-day average. Price near the top band has risen a lot recently; "
        "near the bottom, fallen a lot. Bands are not walls — price can walk along them "
        "or break through. They show how stretched a move is, nothing more."),
    "rsi": (
        "RSI (0–100) measures how strong recent gains were versus recent losses. "
        "Above 70 is called overbought, below 30 oversold. It is a warning light, not "
        "a trade signal: a stock can stay overbought for weeks in a strong trend, and "
        "oversold stocks can keep falling."),
}

DISCLOSURE_LINE = "Remember: this is paper trading. No signal here is a guarantee."


class Assistant:
    def __init__(self, name: str = "Vault", llm: LLMProvider | None = None):
        self.name = name
        # Default: no LLM. Pass an LLMProvider to enable free-form answers.
        self.llm = llm if llm is not None else NoLLMProvider()

    # -- Phase 1 methods (signatures unchanged) -------------------------
    def briefing(self, portfolio_value: float, daily_pnl: float, signals: list) -> str:
        lines = [
            f"Good day. This is {self.name}, your VaultTec assistant.",
            f"Portfolio value (paper): ${portfolio_value:,.2f}. Daily P&L: ${daily_pnl:,.2f}.",
        ]
        if signals:
            lines.append(f"{len(signals)} active signal(s) on your watchlist:")
            for s in signals:
                lines.append(f"  - {s.symbol}: {s.direction} ({s.confidence:.0%} confidence). {s.evidence}")
        else:
            lines.append("No active signals right now.")
        lines.append(DISCLOSURE_LINE)
        return "\n".join(lines)

    def explain_signal(self, signal) -> str:
        return (
            f"{signal.symbol} is showing a {signal.direction} signal at "
            f"{signal.confidence:.0%} confidence. Why: {signal.evidence} "
            f"What could go wrong: the trend can reverse, and past patterns "
            f"do not guarantee future results. Check your stop-loss before any trade."
        )

    # -- Phase 2: daily market briefing ----------------------------------
    def daily_briefing(self, scan_results: list, portfolio_value: float,
                       daily_pnl: float, accuracy: dict | None = None) -> str:
        """Morning briefing: what the watchlist is doing, the strongest
        opportunities, what to watch — and what VaultTec does not know."""
        lines = [
            f"Good morning. {self.name} here with your daily briefing.",
            f"Portfolio (paper): ${portfolio_value:,.2f}, daily P&L ${daily_pnl:,.2f}.",
        ]
        ranked = [r for r in scan_results if r["direction"] != "neutral"]
        if ranked:
            lines.append(f"Strongest opportunities on the watchlist ({len(ranked)}):")
            for r in ranked[:3]:
                lines.append(f"  - {r['symbol']}: {r['direction']} ({r['confidence']:.0%} confidence, "
                             f"{r['checks_agreeing']} check(s) agreed). {r['evidence']}")
        else:
            lines.append("No symbol on the watchlist cleared the bar for a signal today — "
                         "that is normal, and it is better than forcing a trade.")
        neutrals = [r["symbol"] for r in scan_results if r["direction"] == "neutral"]
        if neutrals:
            lines.append(f"No clear signal on: {', '.join(neutrals)}.")
        if accuracy and accuracy.get("accuracy_pct") is not None:
            lines.append(f"Signal accuracy so far: {accuracy['accuracy_pct']:.1f}% over "
                         f"{accuracy['total']} resolved signals. Past performance does not "
                         "guarantee future results.")
        elif accuracy:
            lines.append(accuracy.get("note", "Not enough resolved signals to judge accuracy yet."))
        lines.append("Watch your stop-losses and your daily loss limit today. " + DISCLOSURE_LINE)
        return "\n".join(lines)

    # -- Phase 2: market / trade / strategy explanations -----------------
    def explain_market(self, symbol: str, analysis: dict) -> str:
        """Plain-language market explanation for one symbol, from the
        indicator analysis (see market/indicators.analyse_indicators)."""
        lines = [
            f"Here is what I see on {symbol} at ${analysis['price']:,.2f}.",
            f"Trend: {analysis['trend']}. {analysis['ema_text']}",
            analysis["rsi_text"],
            analysis["macd_text"],
            analysis["bollinger_text"],
            f"Volume: {analysis['volume']['label']}.",
        ]
        if analysis.get("atr") == analysis.get("atr"):  # not NaN
            lines.append(f"It usually moves about ${analysis['atr']:.2f} a day — "
                         "a stop-loss tighter than that can be hit by ordinary noise.")
        lines.append("That is what the past prices show. It is not a forecast, "
                     "and it is not a recommendation to buy or sell.")
        return " ".join(lines)

    def explain_trade(self, signal, analysis: dict | None = None) -> str:
        """Trade analysis: the signal, its evidence, the risks, and the
        checks to run before any trade. Never says 'take this trade'."""
        text = self.explain_signal(signal)
        if analysis is not None:
            text += f" Market context: {analysis['rsi_text']} {analysis['macd_text']}"
        return (text + " Before any trade, check: is the stop-loss set, is the position "
                       "size inside your profile limit, and is the risk/reward at least "
                       "1.5:1? If any answer is no, VaultTec blocks the trade.")

    def explain_strategy(self, name: str) -> str:
        key = name.lower().strip()
        for known, text in STRATEGIES.items():
            if known in key or key in known:
                return text
        return ("I can explain these strategies: SMA crossover, MACD crossover, "
                "stop-loss, position sizing, diversification, risk/reward, "
                "Bollinger Bands, and RSI. Which one would you like?")

    def explain_portfolio(self, portfolio_value: float, cash: float, holdings: list,
                          exposure: float) -> str:
        lines = [f"Your portfolio (paper) is worth ${portfolio_value:,.2f}, "
                 f"with ${cash:,.2f} in cash and ${exposure:,.2f} invested."]
        if holdings:
            lines.append("Holdings:")
            for h in holdings:
                lines.append(f"  - {h.get('symbol')}: {h.get('quantity')} shares.")
        else:
            lines.append("You hold nothing yet — your first coached paper trade will start the journal.")
        lines.append("If one holding is much bigger than the others, that is concentration "
                     "risk: one bad day in that stock hurts the whole portfolio.")
        return " ".join(lines)

    # -- Phase 2: question routing ---------------------------------------
    def answer(self, question: str, context: dict | None = None) -> str:
        q = question.lower()
        context = context or {}
        if "risk" in q or "stop" in q:
            return ("Risk first: every trade needs a stop-loss, a position size "
                    "inside your profile limit, and a risk/reward of at least 1.5:1. "
                    "If a trade fails any of those checks, VaultTec blocks it.")
        if "profit" in q or "guarantee" in q or "make money" in q:
            return ("I can't promise profits — nobody can, and any system that does "
                    "is not being honest with you. What I can do is show you the "
                    "evidence, the risk, and the plan, and track whether the "
                    "approach works over 30–50 paper trades.")
        if "automat" in q:
            return ("Automation starts only after you graduate from coaching, "
                    "only inside your profile settings, and only on paper in "
                    "Phase 1. You can stop it instantly with the kill-switch.")
        if "portfolio" in q or "holding" in q or "how much" in q:
            if "portfolio_value" in context:
                return self.explain_portfolio(
                    context["portfolio_value"], context.get("cash", 0.0),
                    context.get("holdings", []), context.get("exposure", 0.0))
            return "Tell me your portfolio value and holdings and I will break them down for you."
        if any(k in q for k in ("strategy", "sma", "macd", "bollinger", "rsi",
                                "diversif", "position sizing", "risk/reward")):
            return self.explain_strategy(q)
        if "brief" in q or "morning" in q or "today" in q:
            if "scan_results" in context:
                return self.daily_briefing(
                    context["scan_results"], context.get("portfolio_value", 0.0),
                    context.get("daily_pnl", 0.0), context.get("accuracy"))
            return ("Ask for a briefing after the scanner has run — I need the "
                    "watchlist results to brief you honestly.")
        if "coach" in q or "graduat" in q or "learn" in q:
            return ("Coaching walks you through your first 5 paper trades, step by "
                    "step, until you can explain the 'why' yourself. Graduation is "
                    "your choice, never automatic — and only after graduation can "
                    "supervised automation (paper only) be switched on.")
        if "signal" in q or "opportunit" in q:
            if "signals" in context and context["signals"]:
                return "\n".join(self.explain_signal(s) for s in context["signals"])
            return "No signals in the current context. Run the market scanner and I will explain what it found."
        # Free-form fallback: only if an LLM provider was explicitly given.
        if not isinstance(self.llm, NoLLMProvider):
            try:
                return self.llm.complete(question, context)
            except Exception as exc:  # never fail the whole app on an LLM error
                return f"I could not get an answer from the language model ({exc}). Here is what I know for certain: " + DISCLOSURE_LINE
        return ("I can help with your portfolio, signals, risk, strategies, and "
                "coaching progress. Ask me about a symbol, your risk limits, a "
                "strategy like 'SMA crossover', or say 'daily briefing' for the "
                "morning summary.")
