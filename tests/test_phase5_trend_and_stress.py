"""Phase 5 — trend-following complement + fresh stress window tests.

The real run fetches delayed real history from yfinance; these tests
never touch the network. They use deterministic stub histories and
check the trend triggers, the wide-6 runner, the pooling/verdict
rules, the FRESH-4 window's freshness, and report saving.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.exit_test import variant_by_id
from vaulttec.analytics.fresh_window import FRESH_WINDOWS
from vaulttec.analytics.mean_reversion import OOS_WINDOWS
from vaulttec.analytics.trend_and_stress import (
    MR_WIDE6_REFERENCE,
    STRESS_WINDOW,
    TREND_STRATEGIES,
    _pool_stress,
    _pool_trend,
    render_markdown,
    run_phase5,
    run_trend_validation,
    run_trend_window,
    save_report,
    trend_trigger,
)


def _rising_history(days: int = 150) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100 for 80 days, then a steady 1%/day rise. SMA-10
    crosses above SMA-30 once the rise is under way, and MACD
    crosses above its signal line too. The rise starts after row
    60, where the validation run starts trading, so the cross is
    inside the traded range — a steady rise produces exactly one
    cross, at the first rise bar."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if i >= 80:
            price *= 1.01
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def _falling_history(days: int = 150) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only): flat at 100 for 80 days,
    then a steady 1%/day fall. The fast SMA stays below the slow
    SMA — no SMA up-crossover, so no SMA trend buy should fire.
    (MACD is different: its line can cross back above its signal
    while still negative as a steady fall's momentum decelerates in
    EMA terms, so no never-fires claim is made for MACD here.)"""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if i >= 80:
            price *= 0.99
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def _flat_history(days: int = 150) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only): constant price — both
    MACD lines sit at exactly zero, so no crossover can fire."""
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    return pd.DataFrame({"date": dates, "open": 100.0, "high": 100.0,
                         "low": 100.0, "close": 100.0, "volume": 1_000_000})


class RisingProvider:
    def get_history(self, symbol, days=180):
        return _rising_history()


def test_trend_strategies_are_sma_and_macd_with_wide6_exits():
    assert set(TREND_STRATEGIES) == {"sma", "macd"}
    wide6 = variant_by_id("wide-6")
    assert wide6.stop_pct == 0.06
    assert wide6.take_pct == 0.09
    assert wide6.horizon_days == 10


def test_sma_trigger_fires_on_up_cross_only():
    history = _rising_history()
    # Find the first bar where the trigger fires: it must fire at
    # least once on a rising history, and never on a falling one.
    fired = [i for i in range(30, len(history))
             if trend_trigger("sma", history.iloc[: i + 1])]
    assert fired, "SMA up-cross never fired on a steadily rising history"
    falling = _falling_history()
    assert not any(trend_trigger("sma", falling.iloc[: i + 1])
                   for i in range(30, len(falling)))


def test_macd_trigger_fires_on_up_cross_only():
    history = _rising_history()
    fired = [i for i in range(30, len(history))
             if trend_trigger("macd", history.iloc[: i + 1])]
    assert fired, "MACD up-cross never fired on a steadily rising history"
    # On a flat history both MACD lines sit at zero — no cross.
    flat = _flat_history()
    assert not any(trend_trigger("macd", flat.iloc[: i + 1])
                   for i in range(30, len(flat)))
    # Note: no never-fires claim is made for a falling history — a
    # MACD line can cross back above its signal line while still
    # negative as a steady fall's EMA momentum decelerates, so a
    # MACD buy can fire in a downtrend. That is real MACD behaviour,
    # not a bug, and it matters for reading the live results.


def test_trend_trigger_needs_defined_indicators():
    short = _rising_history(days=10)
    assert trend_trigger("sma", short) is False
    assert trend_trigger("macd", short) is False
    assert trend_trigger("sma", _rising_history(days=1)) is False


def test_trend_trigger_rejects_unknown_strategy():
    import pytest

    with pytest.raises(ValueError):
        trend_trigger("nope", _rising_history())


def test_run_trend_validation_buys_the_rise_not_the_fall():
    rising = run_trend_validation("sma", {"AAPL": _rising_history()})
    assert rising["trades_placed"] >= 1
    assert rising["wins"] + rising["losses"] == rising["trades_placed"]
    assert rising["stop_pct"] == 0.06
    assert rising["take_pct"] == 0.09
    for trade in rising["trades"]:
        assert trade["stop_loss"] == round(trade["entry"] * 0.94, 2)
        assert trade["take_profit"] > trade["entry"]
        assert trade["exit_reason"] in (
            "stop-loss", "take-profit", "time exit (10 days)")
    falling = run_trend_validation("sma", {"AAPL": _falling_history()})
    assert falling["trades_placed"] == 0
    macd_rising = run_trend_validation("macd", {"AAPL": _rising_history()})
    assert macd_rising["trades_placed"] >= 1


def test_run_trend_window_runs_both_strategies_on_stub_data():
    start = str(_rising_history()["date"].iloc[30])[:10]
    window, _ = run_trend_window(
        "TREND-test", start, "2025-08-27", "out-of-sample",
        symbols=["AAPL"], provider=RisingProvider())
    assert set(window["strategies"]) == {"sma", "macd"}
    for strategy in TREND_STRATEGIES:
        result = window["strategies"][strategy]
        assert result["trades_placed"] >= 0
        assert result["wins"] + result["losses"] == result["trades_placed"]
        assert result["walk_forward_step_days"] == 1


def test_stress_window_is_one_fresh_window_earlier_than_fresh3():
    label, start, end = STRESS_WINDOW
    assert label == "FRESH-4"
    assert (start, end) == ("2022-09-12", "2023-03-10")
    # It ends the day FRESH-3 starts, so it touches no earlier window.
    fresh3 = next(w for w in FRESH_WINDOWS if w[0] == "FRESH-3")
    assert end <= fresh3[1]
    assert end <= min(s for _, s, _ in OOS_WINDOWS)
    for _, fs, fe in FRESH_WINDOWS:
        assert end <= fs or start >= fe
    for _, os_, oe in OOS_WINDOWS:
        assert end <= os_ or start >= oe


def test_pool_trend_sums_only_the_windows_given():
    def _window(label, pnl, trades=10, wins=6):
        return {"label": label, "strategies": {"sma": {
            "trades_placed": trades, "wins": wins, "total_pnl_usd": pnl,
            "win_rate_pct": wins / trades * 100}}}

    pooled = _pool_trend([_window("OOS-1", 100.0), _window("OOS-2", -20.0)],
                         "sma")
    assert pooled["total_pnl_usd"] == 80.0
    assert pooled["trades"] == 20
    assert pooled["positive_windows"] == 1
    assert pooled["windows_total"] == 2
    # A single-window pool is just that window — no mixing.
    assert _pool_trend([_window("OOS-1", 42.0)], "sma")["total_pnl_usd"] == 42.0


def test_pool_stress_holds_up_rule_single_window():
    def _window(label, pnl, trades=10, wins=6):
        return {"label": label, "strategies": {"rsi": {"wide-6": {
            "trades_placed": trades, "wins": wins, "total_pnl_usd": pnl,
            "win_rate_pct": wins / trades * 100}}}}

    # Positive P&L and >40% win on the single window: holds up.
    assert _pool_stress([_window("FRESH-4", 50.0)], "rsi", "wide-6")["holds_up"] is True
    # Negative P&L: does not hold up.
    assert _pool_stress([_window("FRESH-4", -50.0)], "rsi", "wide-6")["holds_up"] is False
    # Positive P&L but win rate at/below 40%: does not hold up.
    assert _pool_stress(
        [_window("FRESH-4", 50.0, trades=10, wins=4)], "rsi", "wide-6")["holds_up"] is False


def test_mr_wide6_reference_matches_phase4c_and_4d_reports():
    # The comparison baseline for the trend verdicts — quoted from
    # the earlier reports, so a typo here would move the verdict.
    assert MR_WIDE6_REFERENCE["rsi"]["oos2_pnl_usd"] == 63.26
    assert MR_WIDE6_REFERENCE["bollinger"]["oos2_pnl_usd"] == 482.00
    assert MR_WIDE6_REFERENCE["rsi"]["oos_pooled_pnl_usd"] == 1441.19
    assert MR_WIDE6_REFERENCE["bollinger"]["oos_pooled_pnl_usd"] == 880.48
    assert MR_WIDE6_REFERENCE["rsi"]["fresh_pooled_pnl_usd"] == 1226.24
    assert MR_WIDE6_REFERENCE["bollinger"]["fresh_pooled_pnl_usd"] == 1043.47


def test_phase5_report_saves_and_states_the_caveats(tmp_path):
    start = str(_rising_history()["date"].iloc[30])[:10]
    window, _ = run_trend_window(
        "TREND-test", start, "2025-08-27", "out-of-sample",
        symbols=["AAPL"], provider=RisingProvider())
    report = {
        "generated_at": "2026-11-09T00:00:00",
        "title": "VaultTec — Phase 5 Trend-Following & Stress Test Report",
        "method": "test method",
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "trend_verdict_rule": "test trend rule",
        "stress_verdict_rule": "test stress rule",
        "mean_reversion_wide6_reference": MR_WIDE6_REFERENCE,
        "trend_windows": [window],
        "trend_insample_window": window,
        "pooled_trend": {
            "sma": {
                "oos_pooled": {"trades": 1, "wins": 1, "win_rate_pct": 100.0,
                               "total_pnl_usd": 10.0, "total_pnl_pct": 0.1,
                               "expectancy_usd": 10.0,
                               "per_window_pnl_usd": {"TREND-test": 10.0},
                               "per_window_win_rate_pct": {"TREND-test": 100.0},
                               "per_window_trades": {"TREND-test": 1},
                               "positive_windows": 1, "windows_total": 1},
                "fresh_pooled": {"trades": 0, "wins": 0, "win_rate_pct": 0.0,
                                 "total_pnl_usd": 0.0, "total_pnl_pct": 0.0,
                                 "expectancy_usd": 0.0,
                                 "per_window_pnl_usd": {},
                                 "per_window_win_rate_pct": {},
                                 "per_window_trades": {},
                                 "positive_windows": 0, "windows_total": 0},
                "all_windows_pooled_incl_insample": {"trades": 1, "wins": 1,
                                                     "win_rate_pct": 100.0,
                                                     "total_pnl_usd": 10.0,
                                                     "total_pnl_pct": 0.1,
                                                     "expectancy_usd": 10.0,
                                                     "per_window_pnl_usd": {"TREND-test": 10.0},
                                                     "per_window_win_rate_pct": {"TREND-test": 100.0},
                                                     "per_window_trades": {"TREND-test": 1},
                                                     "positive_windows": 1, "windows_total": 1},
            },
            "macd": {
                "oos_pooled": {"trades": 0, "wins": 0, "win_rate_pct": 0.0,
                               "total_pnl_usd": 0.0, "total_pnl_pct": 0.0,
                               "expectancy_usd": 0.0,
                               "per_window_pnl_usd": {},
                               "per_window_win_rate_pct": {},
                               "per_window_trades": {},
                               "positive_windows": 0, "windows_total": 0},
                "fresh_pooled": {"trades": 0, "wins": 0, "win_rate_pct": 0.0,
                                 "total_pnl_usd": 0.0, "total_pnl_pct": 0.0,
                                 "expectancy_usd": 0.0,
                                 "per_window_pnl_usd": {},
                                 "per_window_win_rate_pct": {},
                                 "per_window_trades": {},
                                 "positive_windows": 0, "windows_total": 0},
                "all_windows_pooled_incl_insample": {"trades": 0, "wins": 0,
                                                     "win_rate_pct": 0.0,
                                                     "total_pnl_usd": 0.0,
                                                     "total_pnl_pct": 0.0,
                                                     "expectancy_usd": 0.0,
                                                     "per_window_pnl_usd": {},
                                                     "per_window_win_rate_pct": {},
                                                     "per_window_trades": {},
                                                     "positive_windows": 0, "windows_total": 0},
            },
        },
        "trend_verdict": {
            "sma": {"oos2_pnl_usd": 10.0,
                    "mr_wide6_oos2_pnl_usd": {"rsi": 63.26, "bollinger": 482.00},
                    "beats_mr_in_oos2": False, "beats_mr_pooled_oos": False,
                    "beats_mr_pooled_fresh": False, "verdict_rule": "test"},
            "macd": {"oos2_pnl_usd": 0.0,
                     "mr_wide6_oos2_pnl_usd": {"rsi": 63.26, "bollinger": 482.00},
                     "beats_mr_in_oos2": False, "beats_mr_pooled_oos": False,
                     "beats_mr_pooled_fresh": False, "verdict_rule": "test"},
        },
        "stress_windows": [],
        "pooled_stress": {
            "rsi": {"wide-6": {"trades": 0, "wins": 0, "win_rate_pct": 0.0,
                               "total_pnl_usd": 0.0, "expectancy_usd": 0.0,
                               "holds_up": False}},
            "bollinger": {"wide-6": {"trades": 0, "wins": 0, "win_rate_pct": 0.0,
                                     "total_pnl_usd": 0.0, "expectancy_usd": 0.0,
                                     "holds_up": False}},
        },
        "stress_verdict": {
            "rsi": {"best_variant_by_pooled_stress_pnl": "wide-6",
                    "best_pooled_stress_pnl_usd": 0.0,
                    "wide6_holds_up": False, "variants_holding_up": [],
                    "verdict_rule": "test"},
            "bollinger": {"best_variant_by_pooled_stress_pnl": "wide-6",
                          "best_pooled_stress_pnl_usd": 0.0,
                          "wide6_holds_up": False, "variants_holding_up": [],
                          "verdict_rule": "test"},
        },
        "note": "Past performance does not guarantee future results.",
    }
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.name == "phase5-trend-and-stress-report.json"
    assert md_path.name == "phase5-trend-and-stress-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["title"].startswith("VaultTec — Phase 5")
    text = md_path.read_text()
    assert "does not promise profits" in text
    assert "Past performance does not guarantee future results" in text
    assert "FRESH-4" in text
    assert "wide-6" in text


def test_run_phase5_is_callable():
    assert callable(run_phase5)
