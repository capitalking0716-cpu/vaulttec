"""Phase 4b — mean-reversion follow-up tests.

The real run fetches delayed real history from yfinance; these tests
never touch the network. They use deterministic stub histories with
a sharp fall (so RSI goes oversold and price touches the lower
Bollinger Band) and check the trigger logic, the risk-managed
validation plumbing, the native backtest plumbing, window labelling,
and failure handling.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.mean_reversion import (
    DatedYFinanceProvider,
    OOS_WINDOWS,
    mean_reversion_trigger,
    render_markdown,
    run_native_backtest,
    run_strategy_validation,
    run_window,
    save_report,
    trade_start_index,
)


def _dip_history(days: int = 150) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100, then a steady 1%/day fall for 15 days (RSI collapses,
    price breaks the lower Bollinger Band), then a recovery."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if i < 40:
            price *= 1.001  # gentle uptrend first, so volatility is non-zero
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


class DipProvider:
    def get_history(self, symbol, days=180):
        return _dip_history()


class FailOneProvider(DipProvider):
    def get_history(self, symbol, days=180):
        if symbol == "NVDA":
            raise ConnectionError("yfinance request failed")
        return super().get_history(symbol, days=days)


def test_rsi_trigger_fires_after_a_sharp_fall_not_on_flat_prices():
    history = _dip_history()
    # Mid-fall (index 50): RSI should be oversold after 10 down days.
    assert mean_reversion_trigger("rsi", history.iloc[:51]) is True
    # Flat start: RSI is undefined / not oversold.
    assert mean_reversion_trigger("rsi", history.iloc[:30]) is False


def test_bollinger_trigger_fires_when_price_breaks_the_lower_band():
    history = _dip_history()
    # Early in the fall the price breaks the lower band; as the fall
    # continues the band widens and the price moves back inside it.
    assert mean_reversion_trigger("bollinger", history.iloc[:45]) is True
    assert mean_reversion_trigger("bollinger", history.iloc[:30]) is False


def test_trade_start_index_uses_window_start_date():
    history = _dip_history()
    idx = trade_start_index(history, "2025-08-01")
    assert history["date"].iloc[idx] >= pd.Timestamp("2025-08-01")
    assert history["date"].iloc[idx - 1] < pd.Timestamp("2025-08-01")


def test_trade_start_index_handles_tz_aware_dates():
    # yfinance returns tz-aware dates; the window start is tz-naive.
    history = _dip_history()
    history["date"] = pd.to_datetime(history["date"]).dt.tz_localize("America/New_York")
    idx = trade_start_index(history, "2025-08-01")
    assert history["date"].iloc[idx].tz_localize(None) >= pd.Timestamp("2025-08-01")


def test_dated_provider_fetches_warmup_before_window_start():
    provider = DatedYFinanceProvider("2025-08-27", "2026-02-23")
    assert str(provider.fetch_start) == "2025-07-18"
    assert str(provider.start) == "2025-08-27"
    assert str(provider.end) == "2026-02-23"


def test_oos_windows_do_not_overlap_each_other_or_phase4():
    # Windows are (start, end-exclusive) and ordered newest-first;
    # each must end on/before the next one's start, and the newest
    # must end before the Phase 4 stock window starts (2026-02-23).
    spans = sorted((s, e) for _, s, e in OOS_WINDOWS)
    for (_, e1), (s2, _) in zip(spans, spans[1:]):
        assert e1 <= s2
    assert max(e for _, _, e in OOS_WINDOWS) <= "2026-02-23"


def test_strategy_validation_places_risk_checked_trades_on_stub():
    histories = {"AAPL": _dip_history(), "MSFT": _dip_history()}
    # Window starts at row 30 of the stub — before the dip at rows 40-54.
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    for strategy in ("rsi", "bollinger"):
        result = run_strategy_validation(strategy, histories, window_start=start)
        assert result["trades_placed"] >= 1
        assert result["wins"] + result["losses"] == result["trades_placed"]
        assert result["blocked_by_risk"] == 0
        for t in result["trades"]:
            assert t["stop_loss"] < t["entry"] < t["take_profit"]
            assert (t["take_profit"] - t["entry"]) / (t["entry"] - t["stop_loss"]) >= 1.5
            assert t["exit_reason"] in ("stop-loss", "take-profit", "time exit (10 days)")
        assert result["max_drawdown_pct"] <= 0.0


def test_native_backtest_runs_on_stub_and_reports_per_symbol():
    histories = {"AAPL": _dip_history()}
    start = str(histories["AAPL"]["date"].iloc[30])[:10]
    for strategy in ("rsi", "bollinger"):
        result = run_native_backtest(strategy, histories, window_start=start)
        assert result["total_trades"] >= 1
        assert result["symbols_with_trades"] == 1
        assert "AAPL" in result["per_symbol"]
        assert result["per_symbol"]["AAPL"]["trades"] >= 1


def test_run_window_with_stub_provider_labels_out_of_sample_and_skips_failures():
    start = str(_dip_history()["date"].iloc[30])[:10]
    window = run_window("OOS-test", start, "2025-08-27",
                        "out-of-sample", symbols=["AAPL", "NVDA"],
                        provider=FailOneProvider())
    assert window["sample"] == "out-of-sample"
    assert "NVDA" in window["failed_symbols"]
    assert "NVDA" not in window["symbols_traded"]
    assert window["symbols_traded"] == ["AAPL"]
    for strategy in ("rsi", "bollinger"):
        assert window["strategies"][strategy]["variant_a_validation"]["trades_placed"] >= 1
        assert window["strategies"][strategy]["variant_b_native_backtest"]["total_trades"] >= 1


def test_followup_report_saves_and_states_the_caveat(tmp_path):
    window = run_window("OOS-test", "2025-08-27", "2026-02-23",
                        "out-of-sample", symbols=["AAPL"], provider=DipProvider())
    report = {
        "generated_at": "2026-11-09T00:00:00",
        "title": "VaultTec — Phase 4b Mean-Reversion Follow-Up Report",
        "method": "test method",
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "oos_windows": [window],
        "insample_window": window,
        "pooled_out_of_sample": {
            "rsi": {
                "variant_a_validation_oos_pooled": {
                    "trades": 1, "wins": 1, "win_rate_pct": 100.0,
                    "total_pnl_usd": 10.0, "total_pnl_pct": 0.1,
                    "per_window_pnl_usd": {"OOS-test": 10.0},
                    "per_window_win_rate_pct": {"OOS-test": 100.0}},
                "variant_b_native_backtest_oos_pooled": {
                    "total_trades": 1, "mean_total_return_pct_per_window": {"OOS-test": 5.0},
                    "mean_of_window_means_pct": 5.0, "windows_positive": 1, "windows_total": 1}},
            "bollinger": {
                "variant_a_validation_oos_pooled": {
                    "trades": 1, "wins": 0, "win_rate_pct": 0.0,
                    "total_pnl_usd": -10.0, "total_pnl_pct": -0.1,
                    "per_window_pnl_usd": {"OOS-test": -10.0},
                    "per_window_win_rate_pct": {"OOS-test": 0.0}},
                "variant_b_native_backtest_oos_pooled": {
                    "total_trades": 1, "mean_total_return_pct_per_window": {"OOS-test": -2.0},
                    "mean_of_window_means_pct": -2.0, "windows_positive": 0, "windows_total": 1}},
        },
        "note": "Past performance does not guarantee future results.",
    }
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.name == "phase4b-mean-reversion-followup-report.json"
    assert md_path.name == "phase4b-mean-reversion-followup-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["title"].startswith("VaultTec — Phase 4b")
    text = md_path.read_text()
    assert "does not promise profits" in text
    assert "Past performance does not guarantee future results" in text
    assert "out-of-sample" in text
