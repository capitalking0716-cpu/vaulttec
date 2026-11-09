"""Phase 4c — exit test tests.

The real run fetches delayed real history from yfinance; these tests
never touch the network. They use deterministic stub histories and
check the downtrend filter, the signal exit, each exit variant's
rules, the combined-variant selection rule, and report saving.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.exit_test import (
    BASE_VARIANTS,
    COMBINED_CANDIDATES,
    combined_variant,
    downtrend_filter,
    mean_reversion_exit_signal,
    render_markdown,
    run_variant_validation,
    run_window_exits,
    save_report,
    select_best_variant,
    variant_by_id,
)
from vaulttec.analytics.mean_reversion import OOS_WINDOWS


def _history(prices: list[float], end: str = "2025-08-26") -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp(end), periods=len(prices))
    rows = []
    for date, close in zip(dates, prices):
        rows.append({"date": date, "open": round(close, 2),
                     "high": round(close * 1.002, 2),
                     "low": round(close * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def _dip_history(days: int = 150) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100, then a steady 1%/day fall for 15 days (RSI collapses,
    price breaks the lower Bollinger Band), then a recovery."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if i < 40:
            price *= 1.001
        elif 40 <= i < 55:
            price *= 0.99
        elif 55 <= i < 80:
            price *= 1.02
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def _falling_history() -> pd.DataFrame:
    """60 flat days at 100, then 20 days falling 1%/day — a clear
    downtrend: price below a falling 50-day average."""
    prices = [100.0] * 60
    price = 100.0
    for _ in range(20):
        price *= 0.99
        prices.append(round(price, 2))
    return _history(prices)


def _rising_history() -> pd.DataFrame:
    """60 flat days at 100, then 20 days rising 1%/day — price above
    a rising 50-day average, so no downtrend."""
    prices = [100.0] * 60
    price = 100.0
    for _ in range(20):
        price *= 1.01
        prices.append(round(price, 2))
    return _history(prices)


class DipProvider:
    def get_history(self, symbol, days=180):
        return _dip_history()


class FailOneProvider(DipProvider):
    def get_history(self, symbol, days=180):
        if symbol == "NVDA":
            raise ConnectionError("yfinance request failed")
        return super().get_history(symbol, days=days)


def test_downtrend_filter_blocks_a_falling_market_not_a_rising_one():
    assert downtrend_filter(_falling_history()) is True
    assert downtrend_filter(_rising_history()) is False


def test_downtrend_filter_never_blocks_on_missing_data():
    # Fewer than 60 bars: the 50-day average cannot be defined yet.
    assert downtrend_filter(_history([100.0] * 30)) is False
    assert downtrend_filter(_history([100.0] * 59)) is False


def test_signal_exit_fires_when_rsi_recovers_above_70():
    prices = [100.0] * 20
    price = 100.0
    for _ in range(15):
        price *= 0.99
        prices.append(round(price, 2))
    for i in range(15):
        # One small down day inside the recovery so the RSI's loss
        # term is non-zero: with 14 straight up-days the RSI in
        # market/indicators.py is undefined (NaN), not 100.
        price *= 0.995 if i == 7 else 1.02
        prices.append(round(price, 2))
    history = _history(prices)
    assert mean_reversion_exit_signal("rsi", history) is True
    # Early in the fall the RSI is oversold, not reversed.
    assert mean_reversion_exit_signal("rsi", history.iloc[:36]) is False


def test_baseline_variant_keeps_phase4b_rules():
    variant = variant_by_id("baseline")
    assert variant.stop_pct == 0.03
    assert variant.take_pct == 0.045
    assert variant.horizon_days == 10
    assert variant.use_filter is False
    assert variant.signal_exit is False


def test_wide_variants_keep_1_5_to_1_after_cent_rounding():
    histories = {"AAPL": _dip_history(), "MSFT": _dip_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    for variant_id in ("wide-5", "wide-6"):
        result = run_variant_validation(
            "rsi", variant_by_id(variant_id), histories, window_start=start)
        assert result["trades_placed"] >= 1
        for t in result["trades"]:
            assert t["stop_loss"] < t["entry"] < t["take_profit"]
            assert (t["take_profit"] - t["entry"]) / (t["entry"] - t["stop_loss"]) >= 1.5
            assert t["days_held"] <= 10


def test_time_5d_variant_never_holds_longer_than_5_days():
    histories = {"AAPL": _dip_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    result = run_variant_validation(
        "rsi", variant_by_id("time-5d"), histories, window_start=start)
    assert result["trades_placed"] >= 1
    assert result["horizon_days"] == 5
    for t in result["trades"]:
        assert t["days_held"] <= 5
        assert t["exit_reason"] in ("stop-loss", "take-profit", "time exit (5 days)")


def test_signal_exit_variant_has_a_stop_but_no_fixed_target():
    histories = {"AAPL": _dip_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    result = run_variant_validation(
        "rsi", variant_by_id("signal-exit"), histories, window_start=start)
    assert result["trades_placed"] >= 1
    for t in result["trades"]:
        assert t["stop_loss"] < t["entry"]
        assert t["take_profit"] is None
        assert t["exit_reason"] in ("stop-loss", "signal exit (reversal)", "time exit (10 days)")
    assert "take-profit" not in result["exits"]


def test_filter_variant_skips_trades_the_baseline_takes():
    # A history that falls hard and stays down: the filter should
    # block at least some triggers the baseline trades.
    histories = {"AAPL": _falling_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    baseline = run_variant_validation(
        "rsi", variant_by_id("baseline"), histories, window_start=start)
    filtered = run_variant_validation(
        "rsi", variant_by_id("filter"), histories, window_start=start)
    assert filtered["skipped_filter"] >= 1
    assert filtered["trades_placed"] <= baseline["trades_placed"]


def test_expectancy_is_pnl_per_trade():
    histories = {"AAPL": _dip_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    result = run_variant_validation(
        "rsi", variant_by_id("baseline"), histories, window_start=start)
    assert result["trades_placed"] >= 1
    assert result["expectancy_usd"] == round(
        result["total_pnl_usd"] / result["trades_placed"], 2)
    assert result["wins"] + result["losses"] == result["trades_placed"]


def test_combined_variant_adds_the_filter_to_the_base_rules():
    base = variant_by_id("wide-5")
    combined = combined_variant(base)
    assert combined.id == "combined-wide-5-filter"
    assert combined.stop_pct == base.stop_pct
    assert combined.take_pct == base.take_pct
    assert combined.horizon_days == base.horizon_days
    assert combined.signal_exit == base.signal_exit
    assert combined.use_filter is True


def test_select_best_variant_picks_highest_pooled_pnl():
    pooled = {"rsi": {
        "wide-5": {"total_pnl_usd": 100.0},
        "wide-6": {"total_pnl_usd": -50.0},
        "time-5d": {"total_pnl_usd": 250.0},
        "signal-exit": {"total_pnl_usd": 200.0},
    }}
    assert select_best_variant(pooled, "rsi") == "time-5d"
    assert set(COMBINED_CANDIDATES) == {"wide-5", "wide-6", "time-5d", "signal-exit"}


def test_oos_windows_do_not_overlap_each_other_or_phase4():
    spans = sorted((s, e) for _, s, e in OOS_WINDOWS)
    for (_, e1), (s2, _) in zip(spans, spans[1:]):
        assert e1 <= s2
    assert max(e for _, _, e in OOS_WINDOWS) <= "2026-02-23"


def test_run_window_exits_with_stub_provider_labels_and_skips_failures():
    start = str(_dip_history()["date"].iloc[30])[:10]
    window, histories = run_window_exits(
        "OOS-test", start, "2025-08-27", "out-of-sample",
        symbols=["AAPL", "NVDA"], provider=FailOneProvider())
    assert window["sample"] == "out-of-sample"
    assert "NVDA" in window["failed_symbols"]
    assert window["symbols_traded"] == ["AAPL"]
    assert set(histories) == {"AAPL"}
    for strategy in ("rsi", "bollinger"):
        for variant in BASE_VARIANTS:
            result = window["strategies"][strategy][variant.id]
            assert result["variant_id"] == variant.id
            assert result["trades_placed"] >= 0
            assert result["wins"] + result["losses"] == result["trades_placed"]


def test_exit_test_report_saves_and_states_the_caveat(tmp_path):
    window, _ = run_window_exits(
        "OOS-test", "2025-08-27", "2026-02-23", "out-of-sample",
        symbols=["AAPL"], provider=DipProvider())
    report = {
        "generated_at": "2026-11-09T00:00:00",
        "title": "VaultTec — Phase 4c Exit Test Report",
        "method": "test method",
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "downtrend_filter_rule": "test filter rule",
        "combined_selection_rule": "test selection rule",
        "verdict_rules": "test verdict rules",
        "variants": [{"id": "baseline", "label": "Baseline", "stop_pct": 0.03,
                      "take_pct": 0.045, "horizon_days": 10, "use_filter": False,
                      "signal_exit": False, "description": "test"}],
        "combined_selection": {
            "rsi": {"best_base_variant": "wide-5", "combined_variant_id": "combined-wide-5-filter",
                    "reason": "test reason"},
            "bollinger": {"best_base_variant": "wide-5", "combined_variant_id": "combined-wide-5-filter",
                          "reason": "test reason"},
        },
        "oos_windows": [window],
        "insample_window": window,
        "pooled_out_of_sample": {
            "rsi": {"baseline": {"trades": 1, "wins": 1, "win_rate_pct": 100.0,
                                 "total_pnl_usd": 10.0, "total_pnl_pct": 0.1,
                                 "expectancy_usd": 10.0,
                                 "per_window_pnl_usd": {"OOS-test": 10.0},
                                 "per_window_win_rate_pct": {"OOS-test": 100.0},
                                 "per_window_trades": {"OOS-test": 1},
                                 "oos2_pnl_usd": 10.0, "oos2_win_rate_pct": 100.0,
                                 "survives_oos2": True, "worth_keeping": True}},
            "bollinger": {"baseline": {"trades": 1, "wins": 0, "win_rate_pct": 0.0,
                                       "total_pnl_usd": -10.0, "total_pnl_pct": -0.1,
                                       "expectancy_usd": -10.0,
                                       "per_window_pnl_usd": {"OOS-test": -10.0},
                                       "per_window_win_rate_pct": {"OOS-test": 0.0},
                                       "per_window_trades": {"OOS-test": 1},
                                       "oos2_pnl_usd": -10.0, "oos2_win_rate_pct": 0.0,
                                       "survives_oos2": False, "worth_keeping": False}},
        },
        "verdict": {
            "rsi": {"best_variant_by_pooled_pnl": "baseline", "best_pooled_pnl_usd": 10.0,
                    "variants_surviving_oos2": ["baseline"], "variants_worth_keeping": ["baseline"]},
            "bollinger": {"best_variant_by_pooled_pnl": "baseline", "best_pooled_pnl_usd": -10.0,
                          "variants_surviving_oos2": [], "variants_worth_keeping": []},
        },
        "note": "Past performance does not guarantee future results.",
    }
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.name == "phase4c-exit-test-report.json"
    assert md_path.name == "phase4c-exit-test-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["title"].startswith("VaultTec — Phase 4c")
    text = md_path.read_text()
    assert "does not promise profits" in text
    assert "Past performance does not guarantee future results" in text
    assert "out-of-sample" in text
    assert "combined-wide-5-filter" in text
