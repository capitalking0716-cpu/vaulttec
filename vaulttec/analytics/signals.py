"""Explainable signal generation (Phase 2).

A signal is an observation with evidence — never a guarantee.
Confidence is a score from how many *independent* checks agree
(trend, EMA, MACD, RSI, Bollinger, volume). Each check contributes
evidence in plain language, and the signal carries the full list so
the dashboard and the AI assistant can explain the
same trade the same way. No signal is ever presented as a promise,
and confidence is capped at 0.85 — no signal is ever "certain".

``generate_signal(symbol, history)`` keeps its Phase 1 signature so
existing callers (app.py, automation) keep working.
"""
from __future__ import annotations

import pandas as pd

from ..db.models import Signal
from ..market.indicators import analyse_indicators

MAX_CONFIDENCE = 0.85
BASE_CONFIDENCE = 0.50


def signal_checks(symbol: str, history: pd.DataFrame) -> list[dict]:
    """Run every independent check on a symbol's history.

    Returns a list of {"name", "side" ("bullish"/"bearish"/"neutral"),
    "weight", "evidence"} — one entry per check that fired. A check
    that says nothing contributes nothing, which is itself information.
    """
    ind = analyse_indicators(history)
    checks: list[dict] = []

    if ind["trend"] == "up":
        checks.append({"name": "trend", "side": "bullish", "weight": 2,
                       "evidence": "Short-term trend is up (10-day average above 30-day)."})
    elif ind["trend"] == "down":
        checks.append({"name": "trend", "side": "bearish", "weight": 2,
                       "evidence": "Short-term trend is down (10-day average below 30-day)."})

    if ind["ema12"] == ind["ema12"] and ind["ema26"] == ind["ema26"]:  # not NaN
        if ind["ema12"] > ind["ema26"]:
            checks.append({"name": "ema", "side": "bullish", "weight": 1,
                           "evidence": "Fast EMA is above the slow EMA — recent prices are above the longer-term average."})
        elif ind["ema12"] < ind["ema26"]:
            checks.append({"name": "ema", "side": "bearish", "weight": 1,
                           "evidence": "Fast EMA is below the slow EMA — recent prices are below the longer-term average."})

    macd_val, macd_sig = ind["macd"], ind["macd_signal"]
    if macd_val == macd_val and macd_sig == macd_sig:  # not NaN
        if macd_val > macd_sig:
            checks.append({"name": "macd", "side": "bullish", "weight": 1,
                           "evidence": "MACD is above its signal line — momentum has been rising recently."})
        else:
            checks.append({"name": "macd", "side": "bearish", "weight": 1,
                           "evidence": "MACD is below its signal line — momentum has been falling recently."})

    rsi_val = ind["rsi"]
    if rsi_val == rsi_val:  # not NaN
        if rsi_val <= 30:
            checks.append({"name": "rsi", "side": "bullish", "weight": 1,
                           "evidence": f"RSI is {rsi_val:.0f} — recently oversold, so a bounce is possible (not promised)."})
        elif rsi_val >= 70:
            checks.append({"name": "rsi", "side": "bearish", "weight": 1,
                           "evidence": f"RSI is {rsi_val:.0f} — recently overbought, so a cool-off is possible (not promised)."})

    price = ind["price"]
    upper, lower = ind["bollinger_upper"], ind["bollinger_lower"]
    if upper == upper and lower == lower:  # not NaN
        if price <= lower * 1.01:
            checks.append({"name": "bollinger", "side": "bullish", "weight": 1,
                           "evidence": "Price is near the lower Bollinger Band — it has fallen a lot recently."})
        elif price >= upper * 0.99:
            checks.append({"name": "bollinger", "side": "bearish", "weight": 1,
                           "evidence": "Price is near the upper Bollinger Band — it has risen a lot recently."})

    vol = ind["volume"]
    if vol["ratio"] >= 1.5:
        side = "bullish" if ind["trend"] == "up" else ("bearish" if ind["trend"] == "down" else "neutral")
        checks.append({"name": "volume", "side": side, "weight": 1,
                       "evidence": f"Volume is {vol['ratio']:.1f}× its 20-day average — this move has more people behind it than usual."})
    return checks


def generate_signal(symbol: str, history: pd.DataFrame) -> Signal:
    """Build an explainable signal from the independent checks.

    Direction: the side with the most weighted agreement. Confidence:
    0.50 base, +0.05 per weighted point of agreement, capped at 0.85;
    0.40 when the checks disagree or say nothing (neutral).
    """
    checks = signal_checks(symbol, history)
    bull = sum(c["weight"] for c in checks if c["side"] == "bullish")
    bear = sum(c["weight"] for c in checks if c["side"] == "bearish")
    total = bull + bear
    if bull > bear and bull >= 2:
        direction, confidence = "long", min(BASE_CONFIDENCE + 0.05 * bull, MAX_CONFIDENCE)
    elif bear > bull and bear >= 2:
        direction, confidence = "short", min(BASE_CONFIDENCE + 0.05 * bear, MAX_CONFIDENCE)
    else:
        direction, confidence = "neutral", 0.40

    if checks:
        evidence = "; ".join(c["evidence"] for c in checks)
        evidence += (f" {bull} bullish check(s) vs {bear} bearish check(s) agreed. "
                     "This is an observation, not a prediction or a guarantee.")
    else:
        evidence = ("No strong trend or momentum signal right now. "
                    "This is an observation, not a prediction or a guarantee.")
    return Signal(symbol=symbol, direction=direction, confidence=confidence, evidence=evidence)


def explain_signal_plain(signal: Signal, history: pd.DataFrame) -> str:
    """Full plain-language explanation of a signal for the dashboard and
    the assistant: what it says, why, what could go wrong, and what
    to check before any trade."""
    ind = analyse_indicators(history)
    lines = [
        f"{signal.symbol}: {signal.direction} signal, {signal.confidence:.0%} confidence.",
        f"Why: {signal.evidence}",
        f"In plain terms: {ind['rsi_text']} {ind['macd_text']} {ind['bollinger_text']}",
        f"Volume: {ind['volume']['label']}.",
    ]
    if ind["atr"] == ind["atr"]:
        lines.append(f"Typical daily move (ATR): about ${ind['atr']:.2f} — a stop-loss closer "
                     "than that can be hit by ordinary daily noise.")
    lines.append("What could go wrong: the trend can reverse, news can move the price, "
                 "and past patterns do not guarantee future results. Check the stop-loss "
                 "and position size before any trade — paper trading only.")
    return " ".join(lines)
