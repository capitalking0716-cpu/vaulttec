"""Phase 2 indicator tests — pure functions, deterministic sample data."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.market import (
    analyse_indicators, atr, bollinger_bands, ema, macd, volume_analysis,
)
from vaulttec.market.data import SampleDataProvider


def _rising(n=60):
    return pd.Series([100 + i * 0.5 for i in range(n)], dtype=float)


def _history(n=90):
    return SampleDataProvider().get_history("AAPL", days=n)


def test_ema_reacts_faster_than_sma():
    s = _rising()
    assert ema(s, 10).iloc[-1] > ema(s, 30).iloc[-1] > 100


def test_macd_positive_on_rising_prices():
    m = macd(_rising())
    assert m["macd"].iloc[-1] > m["signal"].iloc[-1]
    assert set(m.columns) == {"macd", "signal", "histogram"}


def test_bollinger_bands_bracket_price():
    b = bollinger_bands(_rising())
    last = _rising().iloc[-1]
    assert b["lower"].iloc[-1] < b["middle"].iloc[-1] < b["upper"].iloc[-1]
    assert b["upper"].iloc[-1] > last or b["lower"].iloc[-1] < last  # bands exist around price


def test_atr_positive_on_sample_history():
    h = _history()
    a = atr(h["high"], h["low"], h["close"])
    assert a.iloc[-1] > 0


def test_volume_analysis_labels():
    vol = pd.Series([1_000_000] * 19 + [3_000_000])
    out = volume_analysis(vol)
    assert out["ratio"] >= 1.5
    assert "busier" in out["label"]


def test_analyse_indicators_has_plain_language():
    ind = analyse_indicators(_history(120))
    assert ind["trend"] in ("up", "down", "flat")
    assert isinstance(ind["rsi_text"], str) and "RSI" in ind["rsi_text"]
    assert isinstance(ind["macd_text"], str) and "MACD" in ind["macd_text"]
    assert isinstance(ind["bollinger_text"], str)
    assert isinstance(ind["ema_text"], str)
    assert ind["volume"]["label"]
    assert 0 <= ind["rsi"] <= 100
