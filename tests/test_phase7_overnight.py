"""Phase 7 — overnight test (combined on new fresh windows, crypto-only,
wider symbols, MACD in the 2022 bear window).

The real run fetches delayed real history from yfinance (cache first);
these tests never touch the network. They use deterministic stub
histories and check the window definitions, the symbols parameter,
the pooling / per-symbol maths, and the report rendering.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.exit_test import run_variant_validation, variant_by_id
from vaulttec.analytics.fresh_window import FRESH_WINDOWS
from vaulttec.analytics.mean_reversion import OOS_WINDOWS
from vaulttec.analytics.overnight_phase7 import (
    CRYPTO_SYMBOLS,
    FRESH_5,
    FRESH_6,
    NEW_FRESH_WINDOWS,
    NEW_SYMBOLS,
    VARIANT_KEYS,
    _pool_windows,
    per_symbol_stats,
    render_markdown,
    render_plain_summary,
    run_phase7_window,
    save_report,
)
from vaulttec.analytics.trend_and_stress import STRESS_WINDOW, run_trend_validation
from vaulttec.analytics.win_rate import WIDE6, run_combined_validation
from vaulttec.market.data import SCAN_UNIVERSE


def _history(days: int = 250, fall_from: int | None = None,
             rise_from: int | None = None) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100, then an optional steady 1%/day fall (RSI drops below
    30, so the mean-reversion trigger fires) and/or a steady 1%/day
    rise (MACD turns bullish). Dates end on the FRESH-5 end date so
    trade_start_index can find the FRESH-5 window start."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2022-09-12"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if fall_from is not None and fall_from <= i < fall_from + 20:
            price *= 0.99
        if rise_from is not None and i >= rise_from:
            price *= 1.01
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


class StubProvider:
    def __init__(self, history):
        self.history = history

    def get_history(self, symbol, days=180):
        return self.history.copy()


def _window_dict(label: str, variant_rows: dict) -> dict:
    """Minimal window dict for pooling tests: variant key ->
    (trades, wins, pnl, win_rate)."""
    return {
        "label": label,
        "results": {
            key: {"trades_placed": t, "wins": w, "total_pnl_usd": p,
                  "win_rate_pct": round(w / t * 100, 1) if t else 0.0,
                  "expectancy_usd": round(p / t, 2) if t else 0.0,
                  "trades": []}
            for key, (t, w, p) in variant_rows.items()
        },
    }


def test_new_windows_do_not_overlap_any_earlier_window():
    all_windows = list(OOS_WINDOWS) + list(FRESH_WINDOWS) + [STRESS_WINDOW] + NEW_FRESH_WINDOWS
    labels = [w[0] for w in all_windows]
    assert labels == ["OOS-1", "OOS-2", "OOS-3",
                      "FRESH-1", "FRESH-2", "FRESH-3", "FRESH-4",
                      "FRESH-5", "FRESH-6"]
    assert len(set(labels)) == len(labels)
    # Contiguous chain, no gaps and no overlaps: each new window ends
    # the day the next one starts.
    assert FRESH_6[2] == FRESH_5[1]  # FRESH-6 ends where FRESH-5 starts
    assert FRESH_5[2] == STRESS_WINDOW[1]  # FRESH-5 ends where FRESH-4 starts
    # Each new window is a 6-month span (182 calendar days, matching
    # the 180-day trading windows used before — the span includes
    # both endpoints' dates).
    for label, start, end in NEW_FRESH_WINDOWS:
        assert (pd.Timestamp(end) - pd.Timestamp(start)).days == 182
    assert FRESH_5 == ("FRESH-5", "2022-03-14", "2022-09-12")
    assert FRESH_6 == ("FRESH-6", "2021-09-13", "2022-03-14")


def test_wider_symbols_are_genuinely_new():
    # AMZN / TSLA / JPM were named in the brief but are already in
    # the original 12 — they must NOT appear in the new-symbol list.
    assert not (set(NEW_SYMBOLS) & set(SCAN_UNIVERSE))
    assert set(NEW_SYMBOLS) == {"AMD", "NFLX", "AVGO", "COST", "HD", "V"}
    assert "AMZN" not in NEW_SYMBOLS and "TSLA" not in NEW_SYMBOLS
    assert "JPM" not in NEW_SYMBOLS
    # Crypto list is BTC + ETH (already in the universe) plus SOL.
    assert CRYPTO_SYMBOLS == ["BTC-USD", "ETH-USD", "SOL-USD"]


def test_symbols_parameter_is_respected_by_all_three_runners():
    falling = _history(fall_from=150)
    rising = _history(rise_from=150)
    # A symbol outside SCAN_UNIVERSE is traded when passed in.
    result = run_variant_validation("rsi", WIDE6, {"AMD": falling},
                                    symbols=["AMD"])
    assert result["trades_placed"] > 0
    assert result["per_symbol_trades"] == {"AMD": result["trades_placed"]}
    assert result["stop_pct"] == 0.06 and result["take_pct"] == 0.09
    # A symbol that is passed but missing from histories is skipped,
    # never invented — zero trades, no crash.
    assert run_variant_validation("rsi", WIDE6, {}, symbols=["AMD"])["trades_placed"] == 0
    assert run_trend_validation("macd", {"AMD": rising}, symbols=["AMD"])["trades_placed"] > 0
    assert run_trend_validation("macd", {}, symbols=["AMD"])["trades_placed"] == 0
    combined = run_combined_validation({"AMD": falling}, symbols=["AMD"])
    assert combined["trades_placed"] > 0
    assert combined["per_symbol_trades"] == {"AMD": combined["trades_placed"]}
    assert run_combined_validation({}, symbols=["AMD"])["trades_placed"] == 0
    # Default (no symbols) still means the scan universe.
    defaulted = run_variant_validation("rsi", WIDE6, {"AAPL": falling, "AMD": falling})
    assert set(defaulted["per_symbol_trades"]) == {"AAPL"}


def test_phase7_window_runs_all_four_variants_on_stubs():
    history = _history(fall_from=150, rise_from=210)
    provider = StubProvider(history)
    window, histories = run_phase7_window(
        "FRESH-5", "2022-03-14", "2022-09-12",
        ["AAPL", "AMD"], variants=VARIANT_KEYS, provider=provider)
    assert window["label"] == "FRESH-5"
    assert window["symbols_traded"] == ["AAPL", "AMD"]
    assert window["failed_symbols"] == {}
    for key in VARIANT_KEYS:
        assert window["results"][key]["stop_pct"] == 0.06
        assert window["results"][key]["take_pct"] == 0.09
        for trade in window["results"][key]["trades"]:
            assert trade["stop_loss"] == round(trade["entry"] * 0.94, 2)
    # The falling-then-rising stub fires both mean-reversion and
    # trend entries, so the combined run places trades from both.
    assert window["results"]["combined"]["trades_placed"] > 0
    assert set(window["results"]["combined"]["per_source_trades"]) <= {"rsi", "bollinger", "macd"}


def test_phase7_window_records_failed_symbols_instead_of_crashing():
    class FailingProvider:
        def get_history(self, symbol, days=180):
            if symbol == "AMD":
                raise ValueError("yfinance returned no history for AMD after 3 attempts")
            return _history(fall_from=150)

    window, _histories = run_phase7_window(
        "FRESH-5", "2022-03-14", "2022-09-12",
        ["AAPL", "AMD"], variants=("rsi_wide6",), provider=FailingProvider())
    assert window["failed_symbols"] == {
        "AMD": "ValueError: yfinance returned no history for AMD after 3 attempts"}
    assert window["symbols_traded"] == ["AAPL"]
    assert window["results"]["rsi_wide6"]["trades_placed"] > 0


def test_pool_windows_maths():
    windows = [
        _window_dict("FRESH-5", {"combined": (10, 6, 100.0)}),
        _window_dict("FRESH-6", {"combined": (20, 10, -50.0)}),
    ]
    pooled = _pool_windows(windows, "combined")
    assert pooled["trades"] == 30
    assert pooled["wins"] == 16
    assert pooled["win_rate_pct"] == 53.3
    assert pooled["total_pnl_usd"] == 50.0
    assert pooled["expectancy_usd"] == 1.67
    assert pooled["per_window_pnl_usd"] == {"FRESH-5": 100.0, "FRESH-6": -50.0}
    assert pooled["positive_windows"] == 1
    assert pooled["windows_total"] == 2
    # Empty pool: no trades, no crash, zeroed figures.
    assert _pool_windows([], "combined")["trades"] == 0
    assert _pool_windows([], "combined")["total_pnl_usd"] == 0.0


def test_per_symbol_stats_aggregates_trade_rows():
    windows = [{
        "label": "FRESH-5",
        "results": {"rsi_wide6": {"trades": [
            {"symbol": "AMD", "pnl_usd": 90.0},
            {"symbol": "AMD", "pnl_usd": -60.0},
            {"symbol": "NFLX", "pnl_usd": 45.0},
        ]}},
    }, {
        "label": "FRESH-6",
        "results": {"rsi_wide6": {"trades": [
            {"symbol": "AMD", "pnl_usd": 10.0},
            {"symbol": "NFLX", "pnl_usd": -60.0},
        ]}},
    }]
    stats = per_symbol_stats(windows, "rsi_wide6")
    assert stats["AMD"] == {"trades": 3, "wins": 2, "pnl_usd": 40.0,
                            "win_rate_pct": 66.7, "expectancy_usd": 13.33}
    assert stats["NFLX"] == {"trades": 2, "wins": 1, "pnl_usd": -15.0,
                             "win_rate_pct": 50.0, "expectancy_usd": -7.5}


def _minimal_report() -> dict:
    return {
        "generated_at": "2026-11-10T00:00:00",
        "title": "VaultTec — Phase 7 Overnight Test Report",
        "method": "test method",
        "data_source": "test data",
        "new_windows_definition": [
            {"label": "FRESH-5", "start": "2022-03-14", "end": "2022-09-12"},
            {"label": "FRESH-6", "start": "2021-09-13", "end": "2022-03-14"},
        ],
        "prior_results_reference": {
            "phase6_fresh_1_to_4": {
                "rsi_wide6": {"total_pnl_usd": 1878.13},
                "bollinger_wide6": {"total_pnl_usd": 1046.71},
                "combined": {"trades": 354, "total_pnl_usd": 5575.29,
                             "expectancy_usd": 15.75},
            },
        },
        "verdict_rules": {
            "item1": "rule 1", "item2": "rule 2",
            "item3": "rule 3", "item4": "rule 4",
        },
        "verdicts": {
            "item1_combined_holds_up": True,
            "item1_combined_beats_all_legs_pnl": False,
            "item1_expectancy_holds_up_in_falling_market": True,
            "item2_rsi_holds_up": True,
            "item2_bollinger_holds_up": False,
            "item2_macd_holds_up": True,
            "item3_rsi_holds_up": True,
            "item3_bollinger_holds_up": True,
            "item4_macd_holds_up_in_bear_window": False,
            "item4_macd_beats_mr_in_bear_window": False,
        },
        "item1_combined_new_fresh": {
            "status": "complete",
            "status_note": "",
            "windows": [{
                "label": "FRESH-5", "start": "2022-03-14", "end": "2022-09-12",
                "history": {"AAPL": {"rows": 250}}, "failed_symbols": {},
                "results": {
                    key: {"trades_placed": 10, "win_rate_pct": 60.0,
                          "total_pnl_usd": 100.0, "expectancy_usd": 10.0,
                          "avg_win_usd": 50.0, "avg_loss_usd": -50.0,
                          "max_drawdown_pct": -1.0, "blocked_by_risk": 0,
                          "per_symbol_trades": {"AAPL": 10}, "trades": []}
                    for key in VARIANT_KEYS
                },
            }],
            "pooled": {
                key: {"trades": 10, "win_rate_pct": 60.0, "total_pnl_usd": 100.0,
                      "expectancy_usd": 10.0, "positive_windows": 1,
                      "windows_total": 1}
                for key in VARIANT_KEYS
            },
            "combined_vs_legs": {
                "combined_trades": 10, "combined_win_rate_pct": 60.0,
                "combined_pnl_usd": 100.0, "combined_expectancy_usd": 10.0,
                "rsi_wide6_pnl_usd": 50.0, "bollinger_wide6_pnl_usd": 40.0,
                "macd_pnl_usd": 30.0, "rsi_wide6_expectancy_usd": 5.0,
                "bollinger_wide6_expectancy_usd": 4.0, "macd_expectancy_usd": 3.0,
                "beats_both_mr_legs_pnl": True, "beats_macd_pnl": True,
                "beats_all_legs_pnl": False,
                "note": "shared pot note",
            },
            "verdict": {},
        },
        "item2_crypto": {
            "status": "complete",
            "status_note": "",
            "sol_usd_fetched_cleanly": True,
            "sol_usd_failures": {},
            "pooled": {
                key: {"trades": 10, "win_rate_pct": 60.0, "total_pnl_usd": 100.0,
                      "expectancy_usd": 10.0, "positive_windows": 5,
                      "windows_total": 6}
                for key in ("rsi_wide6", "bollinger_wide6", "macd")
            },
            "per_symbol": {
                key: {"BTC-USD": {"trades": 5, "win_rate_pct": 60.0,
                                  "pnl_usd": 50.0, "expectancy_usd": 10.0}}
                for key in ("rsi_wide6", "bollinger_wide6", "macd")
            },
            "windows": [{
                "label": "FRESH-1", "start": "2024-03-04", "end": "2024-09-01",
                "history": {"BTC-USD": {"rows": 250}}, "failed_symbols": {},
                "results": {
                    key: {"trades_placed": 10, "win_rate_pct": 60.0,
                          "total_pnl_usd": 100.0, "expectancy_usd": 10.0,
                          "avg_win_usd": 50.0, "avg_loss_usd": -50.0,
                          "max_drawdown_pct": -1.0, "blocked_by_risk": 0,
                          "per_symbol_trades": {"BTC-USD": 10}, "trades": []}
                    for key in ("rsi_wide6", "bollinger_wide6", "macd")
                },
            }],
            "verdict": {},
        },
        "item3_wider_symbols": {
            "status": "complete",
            "status_note": "",
            "note": "wider note",
            "pooled": {
                key: {"trades": 10, "win_rate_pct": 60.0, "total_pnl_usd": 100.0,
                      "expectancy_usd": 10.0, "positive_windows": 2,
                      "windows_total": 3}
                for key in ("rsi_wide6", "bollinger_wide6")
            },
            "per_symbol": {
                key: {"AMD": {"trades": 5, "win_rate_pct": 60.0,
                              "pnl_usd": 50.0, "expectancy_usd": 10.0}}
                for key in ("rsi_wide6", "bollinger_wide6")
            },
            "verdict": {
                key: {"positive_symbols": 5, "symbols_total": 6}
                for key in ("rsi_wide6", "bollinger_wide6")
            },
            "windows": [{
                "label": "FRESH-1", "start": "2024-03-04", "end": "2024-09-01",
                "history": {"AMD": {"rows": 250}}, "failed_symbols": {},
                "results": {
                    key: {"trades_placed": 10, "win_rate_pct": 60.0,
                          "total_pnl_usd": 100.0, "expectancy_usd": 10.0,
                          "avg_win_usd": 50.0, "avg_loss_usd": -50.0,
                          "max_drawdown_pct": -1.0, "blocked_by_risk": 0,
                          "per_symbol_trades": {"AMD": 10}, "trades": []}
                    for key in ("rsi_wide6", "bollinger_wide6")
                },
            }],
        },
        "item4_macd_bear": {
            "status": "complete",
            "status_note": "",
            "window_dates": {"start": "2022-03-14", "end": "2022-09-12"},
            "macd_fresh5": {"trades": 10, "win_rate_pct": 50.0,
                            "total_pnl_usd": -20.0, "expectancy_usd": -2.0,
                            "max_drawdown_pct": -2.0,
                            "per_symbol_trades": {"AAPL": 10}},
            "macd_fresh6_for_context": {"trades": 5, "win_rate_pct": 60.0,
                                        "total_pnl_usd": 30.0,
                                        "per_symbol_trades": {"AAPL": 5}},
            "mr_wide6_fresh5_pnl_usd": {"rsi": 50.0, "bollinger": 40.0},
            "verdict": {},
        },
        "item_status": {
            "item1_combined_new_fresh": "complete",
            "item2_crypto": "complete",
            "item3_wider_symbols": "complete",
            "item4_macd_bear": "complete",
            "small_cap": "complete",
        },
        "small_cap": {
            "status": "complete",
            "status_note": "",
            "capital_levels_usd": [10000.0, 100.0, 50.0, 20.0],
            "method_note": "small cap method note",
            "windows": [{
                "label": "FRESH-1", "start": "2024-03-04", "end": "2024-09-01",
                "results_by_capital": {
                    f"{cap:.2f}": {
                        key: {"trades": 5, "total_pnl_usd": 1.25,
                              "skipped_too_small": 0}
                        for key in ("rsi_wide6", "bollinger_wide6", "macd")
                    } for cap in (10000.0, 100.0, 50.0, 20.0)
                },
            }],
            "pooled_by_capital": {
                f"{cap:.2f}": {
                    key: {"trades": 5, "win_rate_pct": 60.0, "total_pnl_usd": 1.25,
                          "pnl_per_window_usd": 1.25, "expectancy_usd": 0.25,
                          "skipped_too_small": 0, "too_small_by_symbol": {},
                          "blocked_by_risk": 0, "windows_run": 1}
                    for key in ("rsi_wide6", "bollinger_wide6", "macd")
                } for cap in (10000.0, 100.0, 50.0, 20.0)
            },
        },
        "fetch_failures": [],
        "note": "honest note",
    }


def test_render_markdown_and_plain_summary(tmp_path):
    report = _minimal_report()
    md = render_markdown(report)
    assert "# VaultTec — Phase 7 Overnight Test Report" in md
    assert "FRESH-5" in md and "FRESH-6" in md
    assert "Item 1" in md and "Item 4" in md
    assert "does not promise profits" in md
    plain = render_plain_summary(report)
    assert "plain version" in plain
    assert "expectancy" not in plain  # no jargon in the plain summary
    assert "P&L" not in plain
    assert "no real money was used" in plain
    json_path, md_path, plain_path = save_report(report, tmp_path)
    assert json_path.exists() and md_path.exists() and plain_path.exists()
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["verdicts"]["item1_combined_holds_up"] is True
    assert md_path.read_text(encoding="utf-8") == md
    assert plain_path.read_text(encoding="utf-8") == plain


def _skipped_window(label, start, end):
    return {
        "label": label, "start": start, "end": end,
        "skipped": True,
        "skip_reason": "No cached history for this window.",
        "symbols_not_attempted": ["AAPL", "MSFT"],
        "history": {}, "failed_symbols": {}, "results": {},
    }


def test_cache_only_window_lists_not_attempted_symbols(tmp_path, monkeypatch):
    # Only AAPL is cached for FRESH-5: the window must run AAPL and
    # list AMD as not attempted — the record must name the symbols
    # that were never tried, not just the ones that were.
    import vaulttec.analytics.overnight_phase7 as p7
    from vaulttec.analytics import fresh_window
    from vaulttec.analytics.fresh_window import CachedDatedProvider

    monkeypatch.setattr(fresh_window, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        p7, "CachedDatedProvider",
        lambda inner, label: CachedDatedProvider(inner, label, cache_dir=tmp_path))
    _history(fall_from=150).to_parquet(tmp_path / "FRESH-5_AAPL.parquet", index=False)
    window, _histories = p7.run_phase7_window(
        "FRESH-5", "2022-03-14", "2022-09-12",
        ["AAPL", "AMD"], variants=("rsi_wide6",), cache_only=True)
    assert not window.get("skipped")
    assert window["symbols_traded"] == ["AAPL"]
    assert window["symbols_not_attempted"] == ["AMD"]


def test_render_blocked_items_say_not_tested_not_zero():
    report = _minimal_report()
    report["item1_combined_new_fresh"]["status"] = "blocked"
    report["item1_combined_new_fresh"]["status_note"] = "FRESH-5/6 need a Yahoo fetch."
    report["item1_combined_new_fresh"]["windows"] = [
        _skipped_window("FRESH-5", "2022-03-14", "2022-09-12"),
        _skipped_window("FRESH-6", "2021-09-13", "2022-03-14"),
    ]
    report["item2_crypto"]["status"] = "blocked"
    report["item2_crypto"]["status_note"] = "No crypto window ran."
    report["item2_crypto"]["windows"] = [
        _skipped_window("FRESH-1", "2024-03-04", "2024-09-01"),
    ]
    report["item3_wider_symbols"]["status"] = "blocked"
    report["item3_wider_symbols"]["status_note"] = "None of the new symbols is cached."
    report["item3_wider_symbols"]["windows"] = [
        _skipped_window("FRESH-1", "2024-03-04", "2024-09-01"),
    ]
    report["item4_macd_bear"]["status"] = "blocked"
    report["item4_macd_bear"]["status_note"] = "FRESH-5 did not run."
    report["item4_macd_bear"]["macd_fresh5"] = None
    report["item4_macd_bear"]["macd_fresh6_for_context"] = None
    report["item4_macd_bear"]["mr_wide6_fresh5_pnl_usd"] = {"rsi": None, "bollinger": None}
    report["small_cap"]["status"] = "blocked"
    report["small_cap"]["status_note"] = "No small-cap window ran."
    md = render_markdown(report)
    assert md.count("NOT TESTED") >= 5
    assert "No cached history for this window." in md
    plain = render_plain_summary(report)
    assert plain.count("NOT TESTED") >= 5
    assert "expectancy" not in plain
    assert "P&L" not in plain
    assert "no real money was used" in plain


def test_render_partial_item2_marks_partial():
    report = _minimal_report()
    report["item2_crypto"]["status"] = "partial"
    report["item2_crypto"]["status_note"] = "Ran 4 of 6 windows."
    report["item2_crypto"]["windows"] = [
        report["item2_crypto"]["windows"][0],
        _skipped_window("FRESH-5", "2022-03-14", "2022-09-12"),
    ]
    md = render_markdown(report)
    assert "PARTIAL" in md
    assert "Ran 4 of 6 windows." in md
    plain = render_plain_summary(report)
    assert "partial answer" in plain
    assert "expectancy" not in plain
    assert "P&L" not in plain
