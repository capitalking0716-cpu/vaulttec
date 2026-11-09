"""Phase 2 signal + scanner tests — explainable, capped, ranked."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics import (
    explain_signal_plain, generate_signal, scan_watchlist, signal_checks,
    top_opportunities,
)
from vaulttec.market.data import SampleDataProvider

PROVIDER = SampleDataProvider()


def _rising(n=120):
    return pd.DataFrame({"close": [100 + i * 0.5 for i in range(n)]})


def _falling(n=120):
    return pd.DataFrame({"close": [200 - i * 0.5 for i in range(n)]})


def test_rising_prices_give_long_signal_with_evidence():
    sig = generate_signal("TEST", _rising())
    assert sig.direction == "long"
    assert 0.5 <= sig.confidence <= 0.85  # capped, never "certain"
    assert "guarantee" in sig.evidence.lower() or "not a prediction" in sig.evidence


def test_falling_prices_give_short_signal():
    sig = generate_signal("TEST", _falling())
    assert sig.direction == "short"


def test_flat_prices_give_neutral_low_confidence():
    flat = pd.DataFrame({"close": [100.0] * 120})
    sig = generate_signal("TEST", flat)
    assert sig.direction == "neutral"
    assert sig.confidence <= 0.45


def test_signal_checks_are_independent_and_explained():
    checks = signal_checks("TEST", _rising())
    assert len(checks) >= 2
    assert all(c["side"] in ("bullish", "bearish", "neutral") for c in checks)
    assert all(c["evidence"] for c in checks)


def test_explain_signal_plain_mentions_risk():
    sig = generate_signal("TEST", _rising())
    text = explain_signal_plain(sig, _rising())
    assert "stop-loss" in text
    assert "could go wrong" in text


def test_scanner_ranks_strongest_first():
    results = scan_watchlist(["AAPL", "MSFT", "NVDA", "SPY", "BTC-USD"],
                             provider_name="sample")
    assert len(results) == 5
    scores = [r["score"] for r in results if r["direction"] != "neutral"]
    assert scores == sorted(scores, reverse=True)
    assert all("evidence" in r and r["evidence"] for r in results)
    assert all(r["source"] == "sample" for r in results)


def test_top_opportunities_respects_confidence_floor():
    top = top_opportunities(provider_name="sample", limit=3, min_confidence=0.55)
    assert len(top) <= 3
    assert all(r["confidence"] >= 0.55 for r in top)
    assert all(r["direction"] != "neutral" for r in top)
