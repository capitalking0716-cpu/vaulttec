"""Technical indicators — pure functions, no network, no UI. Testable.

Phase 1: SMA, RSI, trend.
Phase 2: EMA, MACD, Bollinger Bands, volume analysis, ATR, and a
plain-language explainer for every indicator. An indicator is an
observation about past prices — never a prediction or a guarantee.
Each indicator function returns raw numbers; the ``explain_*`` helpers
turn those numbers into plain language for the dashboard.
"""
from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential moving average — reacts faster than SMA because it
    weights recent prices more heavily."""
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (0-100). >70 often overbought, <30 oversold —
    context only, never a trade signal on its own."""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def macd(series: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> pd.DataFrame:
    """MACD: fast EMA minus slow EMA, plus a signal line (EMA of MACD)
    and a histogram (MACD minus signal). MACD above its signal line
    suggests rising momentum; below it, falling momentum."""
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    })


def bollinger_bands(series: pd.Series, window: int = 20,
                    num_std: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands: a middle band (SMA) with upper/lower bands
    num_std standard deviations away. Price near the upper band means
    it has moved up a lot recently; near the lower band, down a lot.
    Narrow bands mean quiet prices; wide bands mean big moves."""
    middle = sma(series, window)
    std = series.rolling(window=window).std()
    return pd.DataFrame({
        "middle": middle,
        "upper": middle + num_std * std,
        "lower": middle - num_std * std,
        "bandwidth": (middle + num_std * std - (middle - num_std * std)) / middle,
    })


def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        window: int = 14) -> pd.Series:
    """Average True Range — how much the price typically moves in a day.
    Used to size stop-losses in plain language ('this stock usually
    moves about $X a day, so a stop closer than that gets hit by noise')."""
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(window=window).mean()


def volume_analysis(volume: pd.Series, window: int = 20) -> dict:
    """Volume in plain terms: is today / recently busier than usual?

    A price move on high volume carries more weight than the same move
    on low volume — more people were actually trading.
    Returns the latest volume, its 20-day average, the ratio, and a
    plain-language label.
    """
    if len(volume) == 0:
        return {"latest": 0, "average": 0.0, "ratio": 0.0, "label": "no volume data"}
    latest = float(volume.iloc[-1])
    avg = float(volume.rolling(window=window).mean().iloc[-1]) if len(volume) >= window else float(volume.mean())
    ratio = latest / avg if avg else 0.0
    if ratio >= 1.5:
        label = "much busier than usual — a lot of trading today"
    elif ratio >= 1.2:
        label = "busier than usual"
    elif ratio <= 0.6:
        label = "quieter than usual — fewer people trading"
    else:
        label = "about normal volume"
    return {"latest": latest, "average": round(avg, 0), "ratio": round(ratio, 2), "label": label}


def trend(series: pd.Series, short: int = 10, long: int = 30) -> str:
    """Trend from moving-average crossover: up / down / flat."""
    if len(series) < long:
        return "flat"
    short_ma = series.rolling(short).mean().iloc[-1]
    long_ma = series.rolling(long).mean().iloc[-1]
    if short_ma > long_ma * 1.01:
        return "up"
    if short_ma < long_ma * 0.99:
        return "down"
    return "flat"


# --- Plain-language explainers (Phase 2) ---------------------------------
# Each returns a short, honest sentence: what the indicator says, and
# what it does NOT mean. Used by the dashboard, the scanner, and the
# AI assistant so every indicator is explained the same way everywhere.

def explain_rsi(value: float) -> str:
    if pd.isna(value):
        return "RSI: not enough data yet."
    if value >= 70:
        return (f"RSI is {value:.0f} — the price has risen a lot recently and may be "
                "overbought, so it could cool off. That alone is not a reason to sell.")
    if value <= 30:
        return (f"RSI is {value:.0f} — the price has fallen a lot recently and may be "
                "oversold, so it could bounce. That alone is not a reason to buy.")
    return f"RSI is {value:.0f} — in the middle range, no strong overbought or oversold reading."


def explain_macd(macd_value: float, signal_value: float) -> str:
    if pd.isna(macd_value) or pd.isna(signal_value):
        return "MACD: not enough data yet."
    if macd_value > signal_value:
        return ("MACD is above its signal line — momentum has been rising recently. "
                "Momentum can turn quickly, so this is one clue, not a forecast.")
    return ("MACD is below its signal line — momentum has been falling recently. "
            "Momentum can turn quickly, so this is one clue, not a forecast.")


def explain_bollinger(price: float, upper: float, lower: float, middle: float) -> str:
    if any(pd.isna(v) for v in (price, upper, lower, middle)):
        return "Bollinger Bands: not enough data yet."
    if price >= upper * 0.99:
        return ("Price is near the upper Bollinger Band — it has moved up a lot "
                "recently. That can mean strong momentum, or that a pullback is due. "
                "The band is not a wall the price cannot cross.")
    if price <= lower * 1.01:
        return ("Price is near the lower Bollinger Band — it has moved down a lot "
                "recently. That can mean heavy selling, or that a bounce is due. "
                "The band is not a floor the price cannot cross.")
    if price > middle:
        return "Price is above the middle band — above its recent 20-day average."
    return "Price is below the middle band — below its recent 20-day average."


def explain_ema(price: float, ema_short: float, ema_long: float) -> str:
    if any(pd.isna(v) for v in (price, ema_short, ema_long)):
        return "EMA: not enough data yet."
    if ema_short > ema_long:
        return ("The fast EMA is above the slow EMA — recent prices are higher "
                "than the longer-term average, which points to an upward trend.")
    if ema_short < ema_long:
        return ("The fast EMA is below the slow EMA — recent prices are lower "
                "than the longer-term average, which points to a downward trend.")
    return "The fast and slow EMAs are about even — no clear trend direction."


def analyse_indicators(history: pd.DataFrame) -> dict:
    """Run every indicator on a history frame (needs ``close``; uses
    ``high``/``low``/``volume`` when present) and return the latest
    values plus a plain-language line for each. This is the single
    place the dashboard, scanner, and assistant all read indicators
    from, so they can never disagree.
    """
    closes = history["close"]
    price = float(closes.iloc[-1])
    last_rsi = float(rsi(closes).iloc[-1]) if len(closes) >= 15 else float("nan")
    macd_df = macd(closes)
    bb = bollinger_bands(closes)
    ema12 = float(ema(closes, 12).iloc[-1]) if len(closes) >= 12 else float("nan")
    ema26 = float(ema(closes, 26).iloc[-1]) if len(closes) >= 26 else float("nan")
    result = {
        "price": price,
        "trend": trend(closes),
        "rsi": last_rsi,
        "rsi_text": explain_rsi(last_rsi),
        "macd": float(macd_df["macd"].iloc[-1]) if len(closes) >= 26 else float("nan"),
        "macd_signal": float(macd_df["signal"].iloc[-1]) if len(closes) >= 26 else float("nan"),
        "macd_text": explain_macd(
            float(macd_df["macd"].iloc[-1]) if len(closes) >= 26 else float("nan"),
            float(macd_df["signal"].iloc[-1]) if len(closes) >= 26 else float("nan")),
        "bollinger_upper": float(bb["upper"].iloc[-1]) if len(closes) >= 20 else float("nan"),
        "bollinger_middle": float(bb["middle"].iloc[-1]) if len(closes) >= 20 else float("nan"),
        "bollinger_lower": float(bb["lower"].iloc[-1]) if len(closes) >= 20 else float("nan"),
        "bollinger_text": explain_bollinger(
            price,
            float(bb["upper"].iloc[-1]) if len(closes) >= 20 else float("nan"),
            float(bb["lower"].iloc[-1]) if len(closes) >= 20 else float("nan"),
            float(bb["middle"].iloc[-1]) if len(closes) >= 20 else float("nan")),
        "ema12": ema12,
        "ema26": ema26,
        "ema_text": explain_ema(price, ema12, ema26),
    }
    if {"high", "low"}.issubset(history.columns):
        atr_value = atr(history["high"], history["low"], closes)
        result["atr"] = float(atr_value.iloc[-1]) if len(closes) >= 15 else float("nan")
    else:
        result["atr"] = float("nan")
    if "volume" in history.columns:
        result["volume"] = volume_analysis(history["volume"])
    else:
        result["volume"] = {"latest": 0, "average": 0.0, "ratio": 0.0, "label": "no volume data"}
    return result
