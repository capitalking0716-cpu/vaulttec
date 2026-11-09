"""Backtesting + historical data analysis (Phase 2).

Backtests show what *would* have happened, not what *will* happen.
Never present backtest results as expected future returns.
Historical analysis describes what *did* happen — returns, volatility,
drawdowns, trends — in plain language, so the user can judge a market
before trusting any signal about it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..market.indicators import bollinger_bands, macd, rsi, sma


def max_drawdown_pct(equity_curve: list[float]) -> float:
    """Worst peak-to-trough fall of an equity curve, in percent (<= 0)."""
    peak, worst = 0.0, 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak * 100)
    return round(worst, 2)


def _summarise(name: str, returns: list[float], equity: list[float]) -> dict:
    """Shared result shape for every backtest in the suite."""
    trades = len(returns)
    wins = sum(1 for r in returns if r > 0)
    return {
        "strategy": name,
        "total_return_pct": round(sum(returns) * 100, 2),
        "trades": trades,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "max_drawdown_pct": max_drawdown_pct(equity),
        "note": "Historical only. Past performance does not guarantee future results.",
    }


def backtest_rsi(history: pd.DataFrame, window: int = 14) -> dict:
    """Buy when RSI falls below 30 (oversold), sell when it rises above 70.
    Mean-reversion idea: prices that fell hard may bounce. Same honesty
    rules as the SMA backtest — this is what *did* happen, not a promise."""
    closes = history["close"].reset_index(drop=True)
    r = rsi(closes, window)
    position, entry, returns, equity = 0, 0.0, [], [1.0]
    for i in range(1, len(closes)):
        if pd.isna(r.iloc[i]):
            continue
        if position == 0 and r.iloc[i] < 30:
            position, entry = 1, closes.iloc[i]
        elif position == 1 and r.iloc[i] > 70:
            ret = (closes.iloc[i] - entry) / entry
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))
            position = 0
    return _summarise("RSI mean-reversion (buy <30, sell >70)", returns, equity)


def backtest_bollinger_bands(history: pd.DataFrame, window: int = 20) -> dict:
    """Buy when the close touches the lower Bollinger Band, sell when it
    touches the upper Band. Mean-reversion idea, same honesty rules."""
    closes = history["close"].reset_index(drop=True)
    bands = bollinger_bands(closes, window)
    position, entry, returns, equity = 0, 0.0, [], [1.0]
    for i in range(1, len(closes)):
        if pd.isna(bands["lower"].iloc[i]) or pd.isna(bands["upper"].iloc[i]):
            continue
        if position == 0 and closes.iloc[i] <= bands["lower"].iloc[i]:
            position, entry = 1, closes.iloc[i]
        elif position == 1 and closes.iloc[i] >= bands["upper"].iloc[i]:
            ret = (closes.iloc[i] - entry) / entry
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))
            position = 0
    return _summarise("Bollinger mean-reversion (buy lower band, sell upper band)", returns, equity)


def run_backtest_suite(history: pd.DataFrame) -> dict:
    """Run every backtest strategy on the same history and compare them.

    Returns {"symbol": ..., "strategies": [one result dict per strategy],
    "best_by_return": <strategy name or None>, "note": ...}. All figures
    are historical only — a strategy that won in the past may lose next.
    A strategy with zero trades is reported as zero trades, not hidden.
    """
    strategies = [
        backtest_sma_crossover(history),
        backtest_macd_crossover(history),
        backtest_rsi(history),
        backtest_bollinger_bands(history),
    ]
    # Give each result a readable name for the comparison table.
    names = ["SMA crossover", "MACD crossover", "RSI mean-reversion", "Bollinger mean-reversion"]
    for result, name in zip(strategies, names):
        result["strategy"] = name
    traded = [s for s in strategies if s["trades"] > 0]
    best = max(traded, key=lambda s: s["total_return_pct"])["strategy"] if traded else None
    return {
        "strategies": strategies,
        "best_by_return": best,
        "note": "Historical only. Past performance does not guarantee future results. "
                "No strategy here is a recommendation to trade.",
    }


def backtest_sma_crossover(history: pd.DataFrame, short: int = 10, long: int = 30) -> dict:
    """Buy when short SMA crosses above long SMA, sell on the reverse cross.
    Returns total return, number of trades, and win rate on historical data."""
    closes = history["close"].reset_index(drop=True)
    s, l = sma(closes, short), sma(closes, long)
    position, entry, returns, wins, trades, equity = 0, 0.0, [], 0, 0, [1.0]
    for i in range(1, len(closes)):
        if pd.isna(s.iloc[i]) or pd.isna(l.iloc[i]):
            continue
        if position == 0 and s.iloc[i] > l.iloc[i] and s.iloc[i - 1] <= l.iloc[i - 1]:
            position, entry = 1, closes.iloc[i]
        elif position == 1 and s.iloc[i] < l.iloc[i] and s.iloc[i - 1] >= l.iloc[i - 1]:
            ret = (closes.iloc[i] - entry) / entry
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))
            wins += ret > 0
            trades += 1
            position = 0
    total = sum(returns)
    return {
        "strategy": "SMA crossover",
        "total_return_pct": round(total * 100, 2),
        "trades": trades,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "max_drawdown_pct": max_drawdown_pct(equity),
        "note": "Historical only. Past performance does not guarantee future results.",
    }


def backtest_macd_crossover(history: pd.DataFrame) -> dict:
    """Buy when MACD crosses above its signal line, sell on the reverse.
    Same honesty rules as the SMA backtest."""
    closes = history["close"].reset_index(drop=True)
    m = macd(closes)
    position, entry, returns, wins, trades, equity = 0, 0.0, [], 0, 0, [1.0]
    for i in range(1, len(closes)):
        if pd.isna(m["macd"].iloc[i]) or pd.isna(m["signal"].iloc[i]):
            continue
        if position == 0 and m["macd"].iloc[i] > m["signal"].iloc[i] and m["macd"].iloc[i - 1] <= m["signal"].iloc[i - 1]:
            position, entry = 1, closes.iloc[i]
        elif position == 1 and m["macd"].iloc[i] < m["signal"].iloc[i] and m["macd"].iloc[i - 1] >= m["signal"].iloc[i - 1]:
            ret = (closes.iloc[i] - entry) / entry
            returns.append(ret)
            equity.append(equity[-1] * (1 + ret))
            wins += ret > 0
            trades += 1
            position = 0
    total = sum(returns)
    return {
        "strategy": "MACD crossover",
        "total_return_pct": round(total * 100, 2),
        "trades": trades,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "max_drawdown_pct": max_drawdown_pct(equity),
        "note": "Historical only. Past performance does not guarantee future results.",
    }


def analyse_history(history: pd.DataFrame) -> dict:
    """Describe what a price history *did* — returns, volatility,
    worst drawdown, trend, and volume — in numbers and plain language.

    Works on any history frame with a ``close`` column; ``volume`` is
    used when present. Returns an empty-data result (not an error)
    when there is too little history to analyse.
    """
    closes = history["close"].reset_index(drop=True)
    if len(closes) < 5:
        return {"days": len(closes), "summary": "Not enough history to analyse yet — need at least 5 days of prices.",
                "total_return_pct": 0.0, "volatility_pct": 0.0, "max_drawdown_pct": 0.0,
                "best_day_pct": 0.0, "worst_day_pct": 0.0, "trend": "flat", "volume_trend": "no volume data"}
    returns = closes.pct_change().dropna()
    total_return = (closes.iloc[-1] / closes.iloc[0] - 1) * 100
    volatility = float(returns.std() * 100)  # daily, in percent
    running_max = closes.cummax()
    drawdown = (closes - running_max) / running_max
    max_dd = float(drawdown.min() * 100)
    best_day = float(returns.max() * 100)
    worst_day = float(returns.min() * 100)
    s10 = sma(closes, 10).iloc[-1]
    s30 = sma(closes, 30).iloc[-1] if len(closes) >= 30 else float("nan")
    if pd.isna(s30):
        trend_label = "flat"
    elif s10 > s30 * 1.01:
        trend_label = "up"
    elif s10 < s30 * 0.99:
        trend_label = "down"
    else:
        trend_label = "flat"
    if "volume" in history.columns and len(history) >= 20:
        recent_vol = float(history["volume"].tail(10).mean())
        older_vol = float(history["volume"].head(max(1, len(history) - 10)).mean())
        volume_trend = ("rising — more trading lately" if recent_vol > older_vol * 1.1
                        else "falling — less trading lately" if recent_vol < older_vol * 0.9
                        else "steady")
    else:
        volume_trend = "no volume data"
    calm = "calm — small daily moves" if volatility < 1.0 else ("choppy — noticeable daily moves" if volatility < 2.5 else "very jumpy — big daily moves")
    summary = (
        f"Over the last {len(closes)} days this price moved {total_return:+.1f}% overall. "
        f"Day to day it has been {calm} (typical daily move about {volatility:.1f}%). "
        f"The worst fall from a peak was {max_dd:.1f}%. "
        f"Best single day {best_day:+.1f}%, worst day {worst_day:+.1f}%. "
        f"Trend: {trend_label}. Volume is {volume_trend}. "
        "This describes the past — it does not predict the next move."
    )
    return {
        "days": len(closes),
        "total_return_pct": round(float(total_return), 2),
        "volatility_pct": round(volatility, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "best_day_pct": round(best_day, 2),
        "worst_day_pct": round(worst_day, 2),
        "trend": trend_label,
        "volume_trend": volume_trend,
        "summary": summary,
    }
