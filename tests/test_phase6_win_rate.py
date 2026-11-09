"""Phase 6 — win-rate tests (high-confidence, volume, combined).

The real run uses cached delayed real history from yfinance; these
tests never touch the network. They use deterministic stub histories
and check the gates, the combined runner, the pooling/verdict rules
(including the small-sample flag), and report saving.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.win_rate import (
    ALL_WINDOWS,
    HIGH_CONFIDENCE_MIN,
    VARIANT_KEYS,
    _pool_key,
    confidence_gate,
    render_markdown,
    run_combined_validation,
    run_filtered_variant,
    run_phase6,
    run_phase6_window,
    save_report,
    volume_gate,
)


def _history(days: int = 150, fall_from: int | None = None,
             rise_from: int | None = None, volume_spike_at: int | None = None) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100, then an optional steady 1%/day fall (RSI drops below
    30, so the mean-reversion trigger fires) and/or a steady 1%/day
    rise (trend/MACD turn bullish). Volume is 1,000,000 except for
    an optional 2,000,000 spike on one bar."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2025-08-26"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if fall_from is not None and fall_from <= i < fall_from + 20:
            price *= 0.99
        if rise_from is not None and i >= rise_from:
            price *= 1.01
        close = price
        volume = 2_000_000 if volume_spike_at == i else 1_000_000
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": volume})
    return pd.DataFrame(rows)


class StubProvider:
    def __init__(self, history):
        self.history = history

    def get_history(self, symbol, days=180):
        return self.history.copy()


def test_variant_keys_are_the_three_new_tests_plus_baselines():
    assert set(VARIANT_KEYS) == {
        "rsi_wide6", "rsi_highconf", "rsi_volume",
        "bollinger_wide6", "bollinger_highconf", "bollinger_volume",
        "combined",
    }
    assert HIGH_CONFIDENCE_MIN == 0.70


def test_all_windows_are_oos_plus_fresh_1_to_4_no_overlap():
    labels = [w[0] for w in ALL_WINDOWS]
    assert labels == ["OOS-1", "OOS-2", "OOS-3",
                      "FRESH-1", "FRESH-2", "FRESH-3", "FRESH-4"]
    assert len(set(labels)) == len(labels)


def test_confidence_gate_needs_four_bullish_checks():
    # Rising history: trend up (2) + EMA (1) + MACD (1) = 4 bullish
    # checks -> confidence exactly 0.70, so the gate passes.
    assert confidence_gate("AAPL", _history(rise_from=80)) is True
    # Falling history: the checks are bearish, so no long signal and
    # the gate fails — even though the mean-reversion trigger fires.
    assert confidence_gate("AAPL", _history(fall_from=80)) is False
    # Flat history: neutral signal, confidence 0.40.
    assert confidence_gate("AAPL", _history()) is False


def test_volume_gate_needs_above_average_volume():
    # Constant volume: ratio is 1.0, not above it — gate fails.
    assert volume_gate(_history()) is False
    # Last bar at 2x volume: ratio above 1.0 — gate passes.
    assert volume_gate(_history(volume_spike_at=149)) is True
    # No volume column at all: never passes on missing data.
    assert volume_gate(_history().drop(columns=["volume"])) is False


def test_filtered_variant_keeps_wide6_stop_on_every_trade():
    falling = _history(fall_from=60)
    for strategy in ("rsi", "bollinger"):
        for gate in ("highconf", "volume"):
            result = run_filtered_variant(
                strategy, f"{strategy}_{gate}", gate, {"AAPL": falling})
            assert result["stop_pct"] == 0.06
            assert result["take_pct"] == 0.09
            for trade in result["trades"]:
                assert trade["stop_loss"] == round(trade["entry"] * 0.94, 2)
                assert trade["take_profit"] > trade["entry"]
    # The volume gate with constant volume blocks everything on this
    # stub; the high-confidence gate blocks a falling history too.
    # That is the gate working, not a bug — see the real report,
    # where the high-confidence gate passed only 2 of 172 signals.
    assert run_filtered_variant(
        "rsi", "rsi_volume", "volume", {"AAPL": falling})["trades_placed"] == 0


def test_filtered_variant_trades_when_the_gate_passes():
    # Falling history with a volume spike on a trigger bar (bar 75 is
    # on the 5-day grid and inside the fall, when RSI is below 30):
    # the volume gate passes and wide-6 trades are placed.
    falling = _history(fall_from=60, volume_spike_at=75)
    result = run_filtered_variant(
        "rsi", "rsi_volume", "volume", {"AAPL": falling})
    assert result["trades_placed"] >= 1
    assert result["wins"] + result["losses"] == result["trades_placed"]


def test_combined_buys_the_rise_and_never_double_exposes_a_day():
    rising = _history(rise_from=80)
    result = run_combined_validation({"AAPL": rising})
    assert result["trades_placed"] >= 1
    assert result["stop_pct"] == 0.06
    assert result["take_pct"] == 0.09
    # Every trade came from exactly one source leg, and the per-source
    # counts add up to the trade count — no day produced two trades.
    assert sum(result["per_source_trades"].values()) == result["trades_placed"]
    assert result["per_source_trades"].get("macd", 0) >= 1
    for trade in result["trades"]:
        assert trade["stop_loss"] == round(trade["entry"] * 0.94, 2)
        assert trade["source_strategy"] in ("rsi", "bollinger", "macd")


def test_combined_on_flat_history_only_bollinger_fires():
    # On a perfectly flat history the Bollinger Bands collapse to zero
    # width, so close == lower band and the Bollinger trigger fires —
    # a real quirk of the trigger as written (the live-paper runner
    # guards against zero-width bands; the validation runners do not).
    # RSI never fires (RSI is undefined on flat prices) and MACD never
    # crosses (both lines sit at zero), so every trade here must be
    # Bollinger-sourced. This documents the quirk rather than hiding it.
    result = run_combined_validation({"AAPL": _history()})
    assert result["trades_placed"] >= 1
    assert set(result["per_source_trades"]) == {"bollinger"}


def test_run_phase6_window_runs_all_seven_variants_on_stub_data():
    start = str(_history()["date"].iloc[30])[:10]
    window, _ = run_phase6_window(
        "P6-test", start, "2025-08-27", "out-of-sample",
        symbols=["AAPL"], provider=StubProvider(_history(fall_from=60)))
    assert set(window["results"]) == set(VARIANT_KEYS)
    for key in VARIANT_KEYS:
        result = window["results"][key]
        assert result["wins"] + result["losses"] == result["trades_placed"]
        assert result["stop_pct"] == 0.06
        assert result["take_pct"] == 0.09


def test_pool_key_sums_only_the_windows_given_and_applies_the_rule():
    def _window(label, pnl, trades=10, wins=6):
        return {"label": label, "results": {"rsi_volume": {
            "trades_placed": trades, "wins": wins, "total_pnl_usd": pnl,
            "win_rate_pct": wins / trades * 100}}}

    pooled = _pool_key([_window("FRESH-1", 100.0), _window("FRESH-2", -20.0)],
                       "rsi_volume")
    assert pooled["total_pnl_usd"] == 80.0
    assert pooled["trades"] == 20
    assert pooled["positive_windows"] == 1
    assert pooled["worth_keeping_pool"] is False  # only 1 positive window
    pooled2 = _pool_key([_window("FRESH-1", 100.0), _window("FRESH-2", 50.0)],
                        "rsi_volume")
    assert pooled2["worth_keeping_pool"] is True
    # Positive P&L but win rate at the 40% break-even: does not pass.
    pooled3 = _pool_key([_window("FRESH-1", 50.0, trades=10, wins=4),
                         _window("FRESH-2", 50.0, trades=10, wins=4)],
                        "rsi_volume")
    assert pooled3["worth_keeping_pool"] is False


def test_phase6_report_saves_and_states_the_caveats(tmp_path):
    empty_pool = {"variant_key": "combined", "variant": "Combined",
                  "trades": 0, "wins": 0, "win_rate_pct": 0.0,
                  "total_pnl_usd": 0.0, "total_pnl_pct": 0.0,
                  "expectancy_usd": 0.0, "per_window_pnl_usd": {},
                  "per_window_win_rate_pct": {}, "per_window_trades": {},
                  "positive_windows": 0, "windows_total": 0,
                  "worth_keeping_pool": False}
    pooled = {key: dict(empty_pool, variant_key=key) for key in VARIANT_KEYS}
    report = {
        "generated_at": "2026-11-09T00:00:00",
        "title": "VaultTec — Phase 6 Win-Rate Test Report",
        "method": "test method",
        "data_source": "yfinance, from data/fresh-cache/",
        "verdict_rule": "test rule",
        "macd_alone_reference": {"oos_pooled_pnl_usd": 1432.96,
                                 "fresh_pooled_pnl_usd": 2899.45},
        "windows": [],
        "pooled_oos": pooled,
        "pooled_fresh": pooled,
        "verdict": {key: {"worth_keeping": False, "fresh_pool_passes": False,
                          "oos_pooled_pnl_positive": False,
                          "fresh_trades": 0, "oos_trades": 0,
                          "small_sample_fresh": True, "small_sample_oos": True,
                          "verdict_rule": "test"} for key in VARIANT_KEYS},
        "combined_vs_legs": {
            pool: {"combined_pnl_usd": 0.0, "combined_win_rate_pct": 0.0,
                   "combined_expectancy_usd": 0.0, "combined_trades": 0,
                   "rsi_wide6_pnl_usd": 0.0, "bollinger_wide6_pnl_usd": 0.0,
                   "beats_rsi_wide6_pnl": False,
                   "beats_bollinger_wide6_pnl": False,
                   "beats_both_legs_pnl": False, "note": "test"}
            for pool in ("oos", "fresh")},
        "note": "Past performance does not guarantee future results.",
    }
    json_path, md_path = save_report(report, tmp_path)
    assert json_path.name == "phase6-win-rate-report.json"
    assert md_path.name == "phase6-win-rate-report.md"
    saved = json.loads(json_path.read_text())
    assert saved["title"].startswith("VaultTec — Phase 6")
    text = md_path.read_text()
    assert "does not promise profits" in text
    assert "Past performance does not guarantee future results" in text
    assert "Small-sample warning" in text
    assert "combined" in text


def test_run_phase6_is_callable():
    assert callable(run_phase6)
