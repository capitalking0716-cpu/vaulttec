"""Dashboard — available trades only.

The Dashboard tab shows ONE thing: today's available trades. Everything
else that used to live there (metric cards, charts, assets, tools)
moved to the tab it belongs in (Results / Trade) — this module is the
pure logic for the trades list, so it is testable without Streamlit.

An "available trade" is a wide-6 mean-reversion setup from the existing
signal pipeline — nothing invented:

- the signal direction is "long" (VaultTec does not short),
- the wide-6 entry trigger fired — a bullish RSI check (RSI <= 30) or
  a bullish Bollinger check (price at the lower band),
- confidence clears the scanner floor (0.55, the same floor
  ``top_opportunities`` uses).

Wide-6 numbers: 6% stop, 9% target, 1.5:1 risk/reward. Sizing comes
from the same RiskEngine the Trade tab uses — 10% of the pot per trade.
The dollars at risk are what the stop costs on a full-size position.
Paper trading only; a trade shown here is a signal, not an order.
Neko decides YES or NO on every trade.
"""
from __future__ import annotations

STOP_PCT = 0.06
TARGET_PCT = 0.09
RISK_REWARD = 1.5
MIN_CONFIDENCE = 0.55
MEAN_REVERSION_CHECKS = ("rsi", "bollinger")


def passes_wide6(signal, checks: list[dict]) -> bool:
    """True when a signal is an available wide-6 trade.

    ``signal`` is a ``Signal`` (direction + confidence); ``checks`` is
    the list ``signal_checks`` returned for that symbol. A trade is
    available only when the signal is a long, the mean-reversion
    trigger fired, and confidence clears the scanner floor.
    """
    if signal.direction != "long":
        return False
    if signal.confidence < MIN_CONFIDENCE:
        return False
    return any(
        c.get("name") in MEAN_REVERSION_CHECKS and c.get("side") == "bullish"
        for c in checks
    )


def build_available_trades(signals, checks_by_symbol, quotes,
                           portfolio_value, risk_engine,
                           held_symbols=()) -> list[dict]:
    """Build the Dashboard's available-trade cards.

    ``signals`` are the watchlist signals from ``generate_signal``;
    ``checks_by_symbol`` maps each symbol to its ``signal_checks`` list;
    ``quotes`` maps each symbol to its current ``Quote``; ``held_symbols``
    are symbols already in open paper positions (they are not available
    to open again). Returns one dict per available trade, strongest
    confidence first. A symbol with no usable price, or one that cannot
    be sized, is skipped — never invented.
    """
    held = set(held_symbols or ())
    trades: list[dict] = []
    for sig in signals:
        if sig.symbol in held:
            continue
        checks = checks_by_symbol.get(sig.symbol, [])
        if not passes_wide6(sig, checks):
            continue
        quote = quotes.get(sig.symbol)
        if quote is None or quote.price is None or quote.price <= 0:
            continue
        entry = quote.price
        stop = round(entry * (1 - STOP_PCT), 2)
        target = round(entry * (1 + TARGET_PCT), 2)
        max_shares = risk_engine.position_size(portfolio_value, entry)
        if max_shares <= 0:
            continue
        if max_shares >= 1:
            shares: float = float(int(max_shares))
            shares_label = f"{int(max_shares):,}"
        else:
            shares = round(max_shares, 4)
            shares_label = f"{shares:.4f}"
        risk_usd = round((entry - stop) * shares, 2)
        reward_usd = round((target - entry) * shares, 2)
        setup = "; ".join(
            c["evidence"]
            for c in checks
            if c.get("name") in MEAN_REVERSION_CHECKS and c.get("side") == "bullish"
        ) or sig.evidence
        trades.append({
            "symbol": sig.symbol,
            "direction": "BUY",
            "confidence": sig.confidence,
            "setup": setup,
            "entry": entry,
            "stop_loss": stop,
            "take_profit": target,
            "risk_reward": f"{RISK_REWARD}:1",
            "shares": shares,
            "shares_label": shares_label,
            "risk_usd": risk_usd,
            "reward_usd": reward_usd,
        })
    trades.sort(key=lambda t: t["confidence"], reverse=True)
    return trades
