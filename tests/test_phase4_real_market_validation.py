"""Phase 4 Step 1 — real-market validation tests.

The real run fetches delayed real history from yfinance; these tests
never touch the network. They inject stub providers into
``run_validation`` / ``run_backtests`` and check the plumbing that
matters: real data is labelled real, a failed symbol is recorded and
skipped (never silently replaced with sample data), and the Phase 4
report saves under its own filenames with its own title.
"""
import json
import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.validation import (
    fetch_histories,
    run_backtests,
    run_validation,
    save_report,
)


def _stub_history(seed: int = 42, days: int = 180) -> pd.DataFrame:
    """Synthetic OHLCV frame (test stub only — never presented as real
    market data). Trends up hard mid-series so long signals fire."""
    rng = random.Random(seed)
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2026-11-06"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if 90 <= i < 120:  # strong uptrend: indicators should call long
            ret = 0.008
        else:
            ret = rng.uniform(-0.005, 0.005)
        price *= 1 + ret
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2),
                     "volume": 1_000_000})
    return pd.DataFrame(rows)


class StubProvider:
    """Deterministic stub history for every symbol."""

    def get_history(self, symbol, days=180):
        return _stub_history(seed=sum(ord(c) for c in symbol), days=days)


class FailOneProvider(StubProvider):
    """Fails for NVDA only — the validation must record and skip it."""

    def get_history(self, symbol, days=180):
        if symbol == "NVDA":
            raise ConnectionError("yfinance request failed")
        return super().get_history(symbol, days=days)


def test_real_run_is_labelled_real_and_uses_stub_history():
    report = run_validation(symbols=["AAPL", "MSFT"], target_trades=3,
                            provider_name="yfinance", provider=StubProvider())
    assert report["provider"] == "yfinance"
    assert report["data_source"].startswith("yfinance")
    assert "Phase 4" in report["title"]
    assert report["failed_symbols"] == {}
    assert set(report["history"]) == {"AAPL", "MSFT"}
    assert report["history"]["AAPL"]["rows"] == 180
    assert report["trades_placed"] == 3
    assert report["wins"] + report["losses"] == 3
    for t in report["trades"]:
        assert t["stop_loss"] < t["entry"] < t["take_profit"]
        assert (t["take_profit"] - t["entry"]) / (t["entry"] - t["stop_loss"]) >= 1.5


def test_failed_symbol_is_recorded_and_never_replaced_with_sample():
    report = run_validation(symbols=["AAPL", "NVDA"], target_trades=3,
                            provider_name="yfinance", provider=FailOneProvider())
    assert "NVDA" in report["failed_symbols"]
    assert "NVDA" not in report["history"]
    assert "NVDA" not in report["symbols_traded"]
    assert all(t["symbol"] == "AAPL" for t in report["trades"])
    # Still labelled real — the failed symbol was skipped, not swapped.
    assert report["data_source"].startswith("yfinance")


def test_fetch_histories_records_failures():
    histories, failed, summary = fetch_histories(FailOneProvider(), ["AAPL", "NVDA"], 180)
    assert set(histories) == {"AAPL"}
    assert "NVDA" in failed
    assert summary["AAPL"]["rows"] == 180


def test_backtests_run_on_stub_history():
    # run_backtests builds its own provider, so exercise it on the
    # sample provider (same code path, offline) and check the shape.
    result = run_backtests(provider_name="sample", symbols=["AAPL"], days=180)
    assert set(result["per_symbol"]) == {"AAPL"}
    assert result["failed_symbols"] == {}
    for name in ("SMA crossover", "MACD crossover", "RSI mean-reversion",
                 "Bollinger mean-reversion"):
        assert name in result["aggregate"]
        assert result["aggregate"][name]["symbols_with_trades"] >= 0


def test_phase4_report_saves_under_own_filenames(tmp_path):
    report = run_validation(symbols=["AAPL"], target_trades=2,
                            provider_name="yfinance", provider=StubProvider())
    json_path, md_path = save_report(report, tmp_path, stem="phase4-real-market-validation-report")
    assert json_path.name == "phase4-real-market-validation-report.json"
    assert md_path.name == "phase4-real-market-validation-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["data_source"].startswith("yfinance")
    text = md_path.read_text()
    assert "Phase 4 Real-Market Validation Report" in text
    assert "does not promise profits" in text
    assert "yfinance" in text
