"""Ava's small-wins watch — she watches Neko's open positions and
flags the three things that matter most to her:

1. BANK IT — a small win is in hand (at least halfway to the 9%
   target, or the target is hit). A banked win beats a target that
   never comes. Small wins stack — Neko's own line is that he does
   not mind small wins until there is enough to do bigger trades.
2. SLIPPING — a win that was bigger and is fading (peak gain has
   given back more than 40%). Bank it before it is gone.
3. CUT IT — a position is past its stop, or drifting toward it.
   The stop does its job only if it is obeyed.
4. TOO MUCH IN ONE NAME — over-concentration in a single symbol.

Everything is computed from real state (open positions + last
completed closes, plus optional recent history for the slipping
check). A flag is only raised from numbers that exist — no current
price, no price-based flag. Nothing here promises a profit, and
nothing here trades. Ava advises; Neko decides YES or NO.
"""
from __future__ import annotations

import pandas as pd

# A gain at least halfway to the 9% target is a small win worth
# banking instead of holding out for the full target.
BANK_IT_PCT = 0.045

# A win that has given back more than this share of its peak gain
# is slipping away.
SLIP_BACK_FRACTION = 0.40

# A loss this deep is drifting toward the 6% stop — flag it before
# it gets there.
DRIFT_PCT = -0.03


def _position_value(position: dict, current_price: float) -> float:
    return float(position.get("quantity", 0) or 0) * current_price


def watch_positions(positions: list[dict], current_prices: dict[str, float],
                    history_by_symbol: dict[str, pd.DataFrame] | None = None,
                    portfolio_value: float | None = None,
                    max_concentration_pct: float = 0.25) -> list[dict]:
    """Scan open positions and return flags, worst first: cut it,
    bank it, slipping, drifting, concentrated.

    ``positions``: each with symbol, entry_price, quantity,
    stop_loss, take_profit (and optionally bars_held, strategy).
    ``current_prices``: symbol -> last completed close. A position
    with no current price gets no price-based flag.
    ``history_by_symbol``: symbol -> daily bars (with a "date" and
    "close" column) for the slipping check; optional.
    """
    flags: list[dict] = []
    history_by_symbol = history_by_symbol or {}
    for position in positions or []:
        symbol = str(position.get("symbol", "")).upper()
        entry = float(position.get("entry_price", 0) or 0)
        quantity = float(position.get("quantity", 0) or 0)
        stop = float(position.get("stop_loss", 0) or 0)
        target = float(position.get("take_profit", 0) or 0)
        if entry <= 0 or quantity <= 0:
            continue
        current = float(current_prices.get(symbol, 0) or 0)
        if current <= 0:
            continue  # no current price: no price-based flag, never invented
        gain_pct = (current - entry) / entry
        gain_usd = (current - entry) * quantity
        if stop and current <= stop:
            flags.append({
                "symbol": symbol, "kind": "cut_it", "priority": 1,
                "headline": f"Cut {symbol} now — you're past your stop.",
                "detail": (f"{symbol} is at ${current:,.2f}, below your stop of "
                           f"${stop:,.2f}. You're down ${abs(gain_usd):,.2f}. The stop "
                           "already said so — waiting only makes the loss bigger."),
                "action": f"Sell {symbol} now.",
            })
            continue
        if target and current >= target:
            flags.append({
                "symbol": symbol, "kind": "bank_it", "priority": 2,
                "headline": f"Target hit on {symbol} — bank it now.",
                "detail": (f"{symbol} is at ${current:,.2f}, at your target of "
                           f"${target:,.2f}. You're up ${gain_usd:,.2f} ({gain_pct:+.1%}). "
                           "That's the win. Take it."),
                "action": f"Sell {symbol} and bank the ${gain_usd:,.2f}.",
            })
            continue
        history = history_by_symbol.get(symbol)
        slipped = _slipping(position, current, history)
        if slipped is not None:
            peak_gain_usd, peak_gain_pct = slipped
            flags.append({
                "symbol": symbol, "kind": "slipping", "priority": 3,
                "headline": f"{symbol} is slipping away — bank the small win.",
                "detail": (f"{symbol} was up ${peak_gain_usd:,.2f} ({peak_gain_pct:+.1%}) "
                           f"and is now up ${gain_usd:,.2f} ({gain_pct:+.1%}). It gave back "
                           "more than 40% of the win. Bank what's left instead of watching "
                           "it disappear."),
                "action": f"Sell {symbol} and bank the ${gain_usd:,.2f}.",
            })
            continue
        if gain_pct >= BANK_IT_PCT:
            flags.append({
                "symbol": symbol, "kind": "bank_it", "priority": 2,
                "headline": f"Bank the small win on {symbol}.",
                "detail": (f"You're up ${gain_usd:,.2f} ({gain_pct:+.1%}) on {symbol} — "
                           "more than halfway to the 9% target. That's a small win in hand. "
                           "Bank it instead of holding out for the full target."),
                "action": f"Sell {symbol} and bank the ${gain_usd:,.2f}.",
            })
            continue
        if gain_pct <= DRIFT_PCT:
            flags.append({
                "symbol": symbol, "kind": "drifting", "priority": 4,
                "headline": f"{symbol} is drifting toward the stop.",
                "detail": (f"You're down ${abs(gain_usd):,.2f} ({gain_pct:+.1%}) on {symbol}, "
                           f"and your stop is ${stop:,.2f}. Don't widen the stop — let it do "
                           "its job, or cut early on purpose. Don't drift."),
                "action": f"Decide on {symbol} now: hold to the stop, or cut early deliberately.",
            })
            continue
    if portfolio_value:
        for position in positions or []:
            symbol = str(position.get("symbol", "")).upper()
            entry = float(position.get("entry_price", 0) or 0)
            quantity = float(position.get("quantity", 0) or 0)
            current = float(current_prices.get(symbol, 0) or 0)
            if entry <= 0 or quantity <= 0 or current <= 0:
                continue
            share = _position_value(position, current) / portfolio_value
            if share > max_concentration_pct:
                flags.append({
                    "symbol": symbol, "kind": "concentrated", "priority": 5,
                    "headline": f"Too much in one name — {symbol} is {share:.0%} of the pot.",
                    "detail": (f"{symbol} is worth ${_position_value(position, current):,.2f}, "
                               f"{share:.0%} of the portfolio, over the {max_concentration_pct:.0%} "
                               "limit. One name should never carry the pot."),
                    "action": f"Trim {symbol} back under {max_concentration_pct:.0%} of the pot.",
                })
    flags.sort(key=lambda flag: flag["priority"])
    return flags


def _slipping(position: dict, current: float,
              history: pd.DataFrame | None) -> tuple[float, float] | None:
    """Was this position up more than it is now? Needs history with
    a "date" and "close" column, filtered to bars since the entry
    date. Returns (peak gain $, peak gain %) when the peak gain has
    given back more than 40% — otherwise None."""
    if history is None or len(history) < 2 or "close" not in history.columns:
        return None
    entry = float(position.get("entry_price", 0) or 0)
    quantity = float(position.get("quantity", 0) or 0)
    if entry <= 0 or quantity <= 0:
        return None
    bars = history
    entry_date = str(position.get("entry_date", "") or "")
    if entry_date and "date" in history.columns:
        try:
            bars = history[pd.to_datetime(history["date"]).dt.date.astype(str) >= entry_date]
        except Exception:  # noqa: BLE001 — bad dates: use all bars
            bars = history
    if bars.empty:
        return None
    peak_close = float(bars["close"].max())
    peak_gain_pct = (peak_close - entry) / entry
    if peak_gain_pct < 0.05:
        return None  # never up enough to call it a slipping win
    now_gain_pct = (current - entry) / entry
    if now_gain_pct <= 0:
        return None  # the win is already gone — the stop/drift flags own it
    given_back = (peak_gain_pct - now_gain_pct) / peak_gain_pct
    if given_back <= SLIP_BACK_FRACTION:
        return None
    return (round((peak_close - entry) * quantity, 2), round(peak_gain_pct, 4))


def summarize_watch(flags: list[dict]) -> str:
    """The watch as one Ava-voice paragraph for her answers."""
    if not flags:
        return ("Small wins watch: nothing to bank or cut right now — no small "
                "win is slipping, nothing is past its stop, and no name is "
                "carrying too much of the pot.")
    bank = [f for f in flags if f["kind"] in ("bank_it", "slipping")]
    cut = [f for f in flags if f["kind"] in ("cut_it", "drifting")]
    conc = [f for f in flags if f["kind"] == "concentrated"]
    parts = []
    if bank:
        parts.append("Bank the small wins: " + "; ".join(
            f"{f['symbol']} — {f['detail']}" for f in bank))
    if cut:
        parts.append("Cut the losers: " + "; ".join(
            f"{f['symbol']} — {f['detail']}" for f in cut))
    if conc:
        parts.append("Too much in one name: " + "; ".join(
            f"{f['symbol']} — {f['detail']}" for f in conc))
    return "Small wins watch: " + " ".join(parts)
