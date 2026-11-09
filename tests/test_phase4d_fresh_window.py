"""Phase 4d — fresh-window test tests.

The real run fetches delayed real history from yfinance; these tests
never touch the network. They use deterministic stub histories and
check the fresh windows are genuinely fresh, the verdict rule, and
report saving.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.exit_test import run_window_exits, variant_by_id
from vaulttec.analytics.fresh_window import (
    FRESH_VARIANT_IDS,
    FRESH_WINDOWS,
    CachedDatedProvider,
    _pool_fresh,
    render_markdown,
    run_fresh_window_test,
    save_report,
)
from vaulttec.analytics.mean_reversion import OOS_WINDOWS


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


class DipProvider:
    def get_history(self, symbol, days=180):
        return _dip_history()


def test_fresh_windows_are_three_and_do_not_overlap_each_other():
    assert len(FRESH_WINDOWS) == 3
    spans = sorted((s, e) for _, s, e in FRESH_WINDOWS)
    for (_, e1), (s2, _) in zip(spans, spans[1:]):
        assert e1 <= s2


def test_fresh_windows_never_touch_oos_or_phase4_windows():
    # All fresh windows end on or before OOS-3 starts (2024-09-01);
    # OOS-1/2/3 all start on or after 2024-09-01, and Phase 4 starts
    # 2026-02-23 — so no fresh bar was used to select the winners.
    assert max(e for _, _, e in FRESH_WINDOWS) <= "2024-09-01"
    assert min(s for _, s, _ in OOS_WINDOWS) >= "2024-09-01"
    for _, fs, fe in FRESH_WINDOWS:
        for _, os_, oe in OOS_WINDOWS:
            assert fe <= os_ or fs >= oe


def test_fresh_variants_are_only_baseline_and_the_two_winners():
    assert set(FRESH_VARIANT_IDS) == {"baseline", "wide-5", "wide-6"}
    assert variant_by_id("wide-5").stop_pct == 0.05
    assert variant_by_id("wide-5").take_pct == 0.075
    assert variant_by_id("wide-6").stop_pct == 0.06
    assert variant_by_id("wide-6").take_pct == 0.09
    assert variant_by_id("baseline").stop_pct == 0.03


def test_pool_fresh_holds_up_rule():
    def _window(label, pnl, trades=10, wins=6):
        return {"label": label, "strategies": {"rsi": {"wide-5": {
            "trades_placed": trades, "wins": wins, "total_pnl_usd": pnl,
            "win_rate_pct": wins / trades * 100}}}}

    # Positive pooled, >40% win, positive 2 of 3 windows: holds up.
    windows = [_window("FRESH-1", 100.0), _window("FRESH-2", -20.0),
               _window("FRESH-3", 50.0)]
    pooled = _pool_fresh(windows, "rsi", "wide-5")
    assert pooled["total_pnl_usd"] == 130.0
    assert pooled["positive_windows"] == 2
    assert pooled["holds_up"] is True
    # Positive pooled but positive in only 1 window: does NOT hold up.
    windows = [_window("FRESH-1", 200.0), _window("FRESH-2", -20.0),
               _window("FRESH-3", -30.0)]
    assert _pool_fresh(windows, "rsi", "wide-5")["holds_up"] is False
    # Positive pooled, 2 positive windows, but win rate at/below 40%:
    # does NOT hold up (wide stop must earn its bigger losses).
    windows = [_window("FRESH-1", 100.0, trades=10, wins=4),
               _window("FRESH-2", -20.0, trades=10, wins=4),
               _window("FRESH-3", 50.0, trades=10, wins=4)]
    assert _pool_fresh(windows, "rsi", "wide-5")["holds_up"] is False


def test_pool_fresh_never_mixes_in_selection_windows():
    # Pooling only the windows passed in: a selection-window result
    # passed by mistake would change the total, so the function must
    # only sum what it is given — checked by construction here with
    # a single-window list.
    def _window(label, pnl):
        return {"label": label, "strategies": {"rsi": {"wide-5": {
            "trades_placed": 10, "wins": 6, "total_pnl_usd": pnl,
            "win_rate_pct": 60.0}}}}
    pooled = _pool_fresh([_window("FRESH-1", 42.0)], "rsi", "wide-5")
    assert pooled["total_pnl_usd"] == 42.0
    assert pooled["windows_total"] == 1


def test_run_window_exits_runs_only_the_fresh_variants_on_stub_data():
    from vaulttec.analytics.fresh_window import FRESH_VARIANTS

    start = str(_dip_history()["date"].iloc[30])[:10]
    window, _ = run_window_exits(
        "FRESH-test", start, "2024-09-01", "fresh — never used for selection",
        symbols=["AAPL"], provider=DipProvider(), variants=FRESH_VARIANTS)
    assert window["sample"] == "fresh — never used for selection"
    assert set(window["strategies"]["rsi"]) == {"baseline", "wide-5", "wide-6"}
    assert set(window["strategies"]["bollinger"]) == {"baseline", "wide-5", "wide-6"}
    for strategy in ("rsi", "bollinger"):
        for variant_id in FRESH_VARIANT_IDS:
            result = window["strategies"][strategy][variant_id]
            assert result["trades_placed"] >= 0
            assert result["wins"] + result["losses"] == result["trades_placed"]


def test_fresh_window_report_saves_and_states_the_caveat(tmp_path):
    window, _ = run_window_exits(
        "FRESH-test", "2024-03-04", "2024-09-01", "fresh — never used for selection",
        symbols=["AAPL"], provider=DipProvider(),
        variants=tuple(variant_by_id(v) for v in FRESH_VARIANT_IDS))
    report = {
        "generated_at": "2026-11-09T00:00:00",
        "title": "VaultTec — Phase 4d Fresh-Window Test Report",
        "method": "test method",
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "verdict_rule": "test verdict rule",
        "fresh_windows_definition": [
            {"label": "FRESH-1", "start": "2024-03-04", "end": "2024-09-01"}],
        "selection_windows_not_used": {
            "phase4c_pooled_selection_results": {
                "rsi": {"wide-5": {"trades": 67, "win_rate_pct": 59.7, "total_pnl_usd": 1517.23}},
                "bollinger": {"wide-5": {"trades": 40, "win_rate_pct": 65.0, "total_pnl_usd": 888.92}},
            }},
        "variants": [{"id": "wide-5", "label": "Wider stop", "stop_pct": 0.05,
                      "take_pct": 0.075, "horizon_days": 10, "use_filter": False,
                      "signal_exit": False, "description": "test"}],
        "fresh_windows": [window],
        "pooled_fresh": {
            "rsi": {"wide-5": {"trades": 1, "wins": 1, "win_rate_pct": 100.0,
                               "total_pnl_usd": 10.0, "total_pnl_pct": 0.1,
                               "expectancy_usd": 10.0,
                               "per_window_pnl_usd": {"FRESH-test": 10.0},
                               "per_window_win_rate_pct": {"FRESH-test": 100.0},
                               "per_window_trades": {"FRESH-test": 1},
                               "positive_windows": 1, "windows_total": 1,
                               "holds_up": True}},
            "bollinger": {"wide-5": {"trades": 1, "wins": 0, "win_rate_pct": 0.0,
                                     "total_pnl_usd": -10.0, "total_pnl_pct": -0.1,
                                     "expectancy_usd": -10.0,
                                     "per_window_pnl_usd": {"FRESH-test": -10.0},
                                     "per_window_win_rate_pct": {"FRESH-test": 0.0},
                                     "per_window_trades": {"FRESH-test": 1},
                                     "positive_windows": 0, "windows_total": 1,
                                     "holds_up": False}},
        },
        "verdict": {
            "rsi": {"best_variant_by_pooled_fresh_pnl": "wide-5",
                    "best_pooled_fresh_pnl_usd": 10.0,
                    "variants_holding_up": ["wide-5"],
                    "verdict_rule": "test verdict rule"},
            "bollinger": {"best_variant_by_pooled_fresh_pnl": "wide-5",
                          "best_pooled_fresh_pnl_usd": -10.0,
                          "variants_holding_up": [],
                          "verdict_rule": "test verdict rule"},
        },
        "note": "Past performance does not guarantee future results.",
    }
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.name == "phase4d-fresh-window-report.json"
    assert md_path.name == "phase4d-fresh-window-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["title"].startswith("VaultTec — Phase 4d")
    text = md_path.read_text()
    assert "does not promise profits" in text
    assert "Past performance does not guarantee future results" in text
    assert "fresh" in text.lower()
    assert "wide-5" in text


def test_cached_provider_fetches_once_then_reads_from_disk(tmp_path):
    calls = {"n": 0}

    class CountingProvider:
        def get_history(self, symbol, days=180):
            calls["n"] += 1
            return _dip_history()

    cached = CachedDatedProvider(CountingProvider(), "FRESH-test", cache_dir=tmp_path)
    first = cached.get_history("AAPL")
    second = cached.get_history("AAPL")
    assert calls["n"] == 1  # second call was a cache hit, no network
    assert first.equals(second)
    assert (tmp_path / "FRESH-test_AAPL.parquet").exists()
    # A different symbol is a separate cache entry.
    cached.get_history("MSFT")
    assert calls["n"] == 2


def test_run_fresh_window_test_is_callable():
    assert callable(run_fresh_window_test)
