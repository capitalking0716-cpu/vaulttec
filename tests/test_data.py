"""Phase 2 data tests — OHLCV history, yfinance fallback to sample."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.market.data import (
    SCAN_UNIVERSE, SampleDataProvider, fetch_history, fetch_quote, get_provider,
)


def test_sample_history_is_ohlcv():
    h = SampleDataProvider().get_history("AAPL", days=60)
    assert list(h.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert len(h) == 60
    assert (h["high"] >= h["low"]).all()
    assert (h["high"] >= h["close"]).all()


def test_sample_history_is_deterministic():
    a = SampleDataProvider().get_history("MSFT", days=30)
    b = SampleDataProvider().get_history("MSFT", days=30)
    assert a.equals(b)


def test_scan_universe_covers_stocks_and_crypto():
    assert "AAPL" in SCAN_UNIVERSE and "BTC-USD" in SCAN_UNIVERSE
    assert len(SCAN_UNIVERSE) >= 10


def test_fetch_history_falls_back_to_sample_when_provider_fails():
    # "yfinance" provider with a bogus symbol path: force failure by
    # asking for a provider name that raises — fetch_history catches
    # any failure and returns sample data labelled honestly.
    history, source = fetch_history("AAPL", days=30, provider_name="nonexistent")
    assert source == "sample"
    assert len(history) == 30
    assert "close" in history.columns


def test_fetch_quote_falls_back_to_sample():
    q = fetch_quote("AAPL", provider_name="nonexistent")
    assert q.source == "sample"
    assert q.price > 0
    assert q.symbol == "AAPL"


def test_get_provider_defaults_to_sample():
    assert isinstance(get_provider(), SampleDataProvider)
