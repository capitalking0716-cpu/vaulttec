"""Market data providers — one interface, swappable backends.

Phase 1 default: SampleDataProvider — deterministic, offline, free.
Phase 2: both providers now return full OHLCV history (open, high, low,
close, volume) so technical analysis, scanners, and backtests all work
from the same frame. YFinanceProvider is delayed real data (free); when
it is unavailable or returns nothing, ``fetch_history`` / ``fetch_quote``
fall back to the sample provider automatically and say so — the app
always works, with or without internet, and never pretends sample data
is real market data.
A licensed real-time provider is a later decision.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import pandas as pd


@dataclass
class Quote:
    symbol: str
    price: float
    change_pct: float
    volume: int
    source: str = "sample"  # "sample" (offline demo data) or "yfinance" (delayed real)


# Phase 2 scan universe: stocks + crypto the scanner can rank.
# Crypto symbols use the Yahoo "-USD" form, matching the existing
# allowed-markets check (a symbol ending in "-USD" is crypto).
SCAN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "SPY", "AMZN", "GOOGL", "META", "TSLA",
    "JPM", "JNJ", "BTC-USD", "ETH-USD",
]


class SampleDataProvider:
    """Deterministic sample prices so the app runs with no internet/key."""

    BASE_PRICES = {
        "AAPL": 232.40, "MSFT": 428.15, "NVDA": 131.20, "SPY": 587.30,
        "AMZN": 201.50, "GOOGL": 168.30, "META": 585.20, "TSLA": 248.90,
        "JPM": 244.60, "JNJ": 152.40,
        "BTC-USD": 97450.0, "ETH-USD": 3420.0,
    }

    def get_quote(self, symbol: str) -> Quote:
        base = self.BASE_PRICES.get(symbol.upper(), 100.0)
        seed = sum(ord(c) for c in symbol)
        rng = random.Random(seed)
        change = rng.uniform(-1.8, 1.8)
        return Quote(symbol.upper(), round(base * (1 + change / 100), 2),
                     round(change, 2), rng.randint(1_000_000, 80_000_000),
                     source="sample")

    def get_history(self, symbol: str, days: int = 60) -> pd.DataFrame:
        base = self.BASE_PRICES.get(symbol.upper(), 100.0)
        rng = random.Random(sum(ord(c) for c in symbol))
        rows, price = [], base * 0.92
        # normalize() so the same symbol gives the same history all day —
        # Timestamp.today() carries the current time, which would otherwise
        # make two calls in one day differ by microseconds.
        dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days)
        for date in dates:
            open_p = price
            price *= 1 + rng.uniform(-0.015, 0.018)
            close = price
            high = max(open_p, close) * (1 + rng.uniform(0, 0.006))
            low = min(open_p, close) * (1 - rng.uniform(0, 0.006))
            volume = rng.randint(800_000, 80_000_000)
            rows.append({"date": date, "open": round(open_p, 2), "high": round(high, 2),
                         "low": round(low, 2), "close": round(close, 2), "volume": volume})
        return pd.DataFrame(rows)


class YFinanceProvider:
    """Delayed real quotes via yfinance. Raises a clear error if unavailable."""

    def get_quote(self, symbol: str) -> Quote:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = float(info["lastPrice"])
        prev = float(info["previousClose"])
        change = (price - prev) / prev * 100 if prev else 0.0
        return Quote(symbol.upper(), round(price, 2), round(change, 2),
                     int(info.get("lastVolume") or 0), source="yfinance")

    def get_history(self, symbol: str, days: int = 60) -> pd.DataFrame:
        import yfinance as yf

        df = yf.Ticker(symbol).history(period=f"{days}d")
        if df.empty:
            raise ValueError(f"yfinance returned no history for {symbol}")
        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"] if c in df.columns]
        return df[cols]


def get_provider(name: str = "sample"):
    if name == "yfinance":
        return YFinanceProvider()
    return SampleDataProvider()


def fetch_history(symbol: str, days: int = 60, provider_name: str = "sample") -> tuple[pd.DataFrame, str]:
    """History for a symbol, with automatic fallback.

    Tries the requested provider first; if it fails (no internet, no
    data, yfinance missing), falls back to the sample provider and
    returns ``"sample"`` as the source so the UI can label it honestly.
    Returns (history_frame, source). Never raises for a data failure.
    """
    provider = get_provider(provider_name)
    try:
        if provider_name not in ("sample", "yfinance"):
            raise ValueError(f"unknown data provider: {provider_name}")
        history = provider.get_history(symbol, days=days)
        if history is None or history.empty or "close" not in history.columns:
            raise ValueError("empty history")
        return history, provider_name
    except Exception:
        return SampleDataProvider().get_history(symbol, days=days), "sample"


def fetch_quote(symbol: str, provider_name: str = "sample") -> Quote:
    """Quote for a symbol, with the same automatic sample fallback."""
    try:
        quote = get_provider(provider_name).get_quote(symbol)
        if quote is None or not math.isfinite(quote.price):
            raise ValueError("bad quote")
        return quote
    except Exception:
        return SampleDataProvider().get_quote(symbol)
