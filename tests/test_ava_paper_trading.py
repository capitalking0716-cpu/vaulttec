"""Ava's paper trading — paper only, OUR strategy, evidence per trade.

Ava implements the validated wide-6 strategy (RSI + Bollinger
mean-reversion with MACD as the complement, one shared pot) from
the scanner signals under those exact rules. She never invents her
own strategy, never freelances entries, and never touches live
trading: the trader refuses to run when either live lock is on.
"""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vaulttec.ava.lessons as lessons_mod
import vaulttec.ava.paper_trading as pt_mod
from vaulttec.analytics.win_rate import run_combined_validation
from vaulttec.ava.paper_trading import (
    AvaPaperTrader,
    assert_paper_only,
    load_evidence,
    run_ava_paper_simulation,
)


def _history(days: int = 250, fall_from: int | None = None,
             rise_from: int | None = None, scale: float = 1.0) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real data):
    flat at 100, then an optional steady 1%/day fall (RSI drops below
    30, so the mean-reversion trigger fires) and/or a steady 1%/day
    rise (MACD turns bullish). Dates end on the FRESH-5 end date."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2022-09-12"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if fall_from is not None and fall_from <= i < fall_from + 20:
            price *= 0.99
        if rise_from is not None and i >= rise_from:
            price *= 1.01
        close = price
        rows.append({"date": date, "open": round(open_p * scale, 2),
                     "high": round(max(open_p, close) * 1.002 * scale, 2),
                     "low": round(min(open_p, close) * 0.998 * scale, 2),
                     "close": round(close * scale, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def _clean_env(monkeypatch):
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ALPACA_PAPER", raising=False)


def test_paper_only_guard_refuses_live(monkeypatch):
    monkeypatch.setenv("VAULTTEC_LIVE_TRADING_ENABLED", "true")
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        assert_paper_only()
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        AvaPaperTrader(starting_cash=100.0)
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED")
    monkeypatch.setenv("ALPACA_PAPER", "false")
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        assert_paper_only()
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        AvaPaperTrader(starting_cash=100.0)


def test_paper_only_guard_passes_when_paper(monkeypatch, tmp_path):
    _clean_env(monkeypatch)
    assert_paper_only()  # no raise
    trader = AvaPaperTrader(starting_cash=100.0,
                            evidence_file=tmp_path / "evidence.jsonl")
    assert trader.starting_cash == 100.0


def test_trader_matches_combined_run_on_same_data(tmp_path, monkeypatch):
    """Ava implements OUR strategy: same loop as the Phase 6 combined
    run, so on the same histories and cash her trades and P&L must
    match the combined runner exactly — she does not freelance."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    histories = {"AAPL": _history(fall_from=150, rise_from=210),
                 "MSFT": _history(fall_from=150, rise_from=210)}
    expected = run_combined_validation(histories, window_start="2022-03-14",
                                       starting_cash=100.0,
                                       symbols=["AAPL", "MSFT"])
    trader = AvaPaperTrader(starting_cash=100.0,
                            evidence_file=tmp_path / "evidence.jsonl")
    summary = trader.run_window("FRESH-5", histories,
                                window_start="2022-03-14",
                                symbols=["AAPL", "MSFT"])
    assert summary["trades_placed"] == expected["trades_placed"]
    assert summary["total_pnl_usd"] == expected["total_pnl_usd"]
    assert summary["wins"] == expected["wins"]
    assert summary["win_rate_pct"] == expected["win_rate_pct"]


def test_evidence_written_per_trade_and_lessons_learned(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    histories = {"AAPL": _history(fall_from=150, rise_from=210)}
    trader = AvaPaperTrader(starting_cash=100.0, evidence_file=evidence_file)
    summary = trader.run_window("FRESH-5", histories,
                                window_start="2022-03-14", symbols=["AAPL"])
    assert summary["trades_placed"] > 0
    assert summary["evidence_records"] == summary["trades_placed"]
    assert summary["lessons_learned"] == summary["trades_placed"]
    rows = [json.loads(line) for line in
            evidence_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == summary["trades_placed"]
    for row in rows:
        assert row["status"] == "placed"
        assert row["symbol"] == "AAPL"
        assert row["signal"] in ("rsi", "bollinger", "macd")
        assert 0.0 <= row["confidence"] <= 0.85
        assert row["entry"] > 0 and row["stop"] > 0 and row["target"] > row["entry"]
        assert row["position_size"] > 0
        assert row["risk_usd"] > 0
        assert "Against first" in row["reasoning"]
        assert "For:" in row["reasoning"]
        assert row["exit_reason"]
        assert row["pnl_usd"] is not None
        assert row["when"]
    lessons = lessons_mod.load_lessons(limit=100)
    assert len(lessons) == summary["trades_placed"]
    assert all("AAPL" in lesson["symbol"] for lesson in lessons)


def test_blocked_trades_logged_with_reason(tmp_path, monkeypatch):
    """A $20 pot cannot size Bitcoin at ~$60,000: the trade is
    blocked as too small and the reason is written to the evidence
    log — never silently dropped."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    histories = {"BTC-USD": _history(fall_from=150, scale=600.0)}
    trader = AvaPaperTrader(starting_cash=20.0, evidence_file=evidence_file)
    summary = trader.run_window("FRESH-5", histories,
                                window_start="2022-03-14", symbols=["BTC-USD"])
    assert summary["trades_placed"] == 0
    assert summary["skipped_too_small"] > 0
    assert summary["too_small_by_symbol"] == {"BTC-USD": summary["skipped_too_small"]}
    rows = [json.loads(line) for line in
            evidence_file.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all(row["status"] == "blocked" for row in rows)
    assert all("Too small" in row["block_reason"] for row in rows)
    assert all(row["symbol"] == "BTC-USD" for row in rows)


def test_load_evidence_reads_the_log(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    histories = {"AAPL": _history(fall_from=150, rise_from=210)}
    trader = AvaPaperTrader(starting_cash=100.0, evidence_file=evidence_file)
    trader.run_window("FRESH-5", histories,
                      window_start="2022-03-14", symbols=["AAPL"])
    monkeypatch.setattr(pt_mod, "evidence_path", lambda: evidence_file)
    rows = load_evidence(limit=5)
    assert rows
    assert rows[0]["symbol"] == "AAPL"
    assert rows[0]["status"] == "placed"
    monkeypatch.setattr(pt_mod, "evidence_path",
                        lambda: tmp_path / "no-such-log.jsonl")
    assert load_evidence() == []


def test_run_ava_paper_simulation_pools_windows(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    histories = {"AAPL": _history(fall_from=150, rise_from=210)}
    result = run_ava_paper_simulation(
        [("FRESH-5", "2022-03-14", histories),
         ("FRESH-5-again", "2022-03-14", histories)],
        starting_cash=100.0, evidence_path=tmp_path / "evidence.jsonl")
    assert result["windows_run"] == ["FRESH-5", "FRESH-5-again"]
    assert result["trades_placed"] == 2 * result["per_window"][0]["trades_placed"]
    assert result["lessons_learned"] == result["trades_placed"]
    assert result["evidence_records"] == result["trades_placed"]
    assert result["total_pnl_usd"] == 2 * result["per_window"][0]["total_pnl_usd"]
