"""Ava's daily paper trading tests — stub providers only, no network.

The real run fetches delayed real history from yfinance; these
tests never touch the network. They check the daily runner's
guarantees: the paper-only guard, durable state, idempotency per
day (no duplicate trades across days), exit logic (stop / target /
time), evidence written per trade, one lesson per close, the MACD
complement firing when mean-reversion does not, no-data handling
(nothing invented), and the kill-switch.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vaulttec.ava.lessons as lessons_mod
from test_ava_paper_trading import _history
from test_live_paper_trading import RUN_DATE, StubProvider, _bars, _dip_history
from vaulttec.ava.daily_trading import (
    compute_summary,
    load_state,
    run_ava_daily,
    save_state,
)

MONDAY = RUN_DATE  # Mon 2026-11-09; last completed stock bar is Fri 2026-11-06
TUESDAY = date(2026, 11, 10)


def _clean_env(monkeypatch):
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ALPACA_PAPER", raising=False)


def _evidence_rows(evidence_file: Path) -> list[dict]:
    if not evidence_file.exists():
        return []
    return [json.loads(line) for line in
            evidence_file.read_text(encoding="utf-8").splitlines()]


def _next_bar_frame(dip: pd.DataFrame, bar_date: str, open_: float,
                    high: float, low: float, close: float) -> pd.DataFrame:
    """The dip history plus one new completed bar (test stub only)."""
    extra = pd.DataFrame([{"date": pd.Timestamp(bar_date), "open": open_,
                           "high": high, "low": low, "close": close,
                           "volume": 1_000_000}])
    return pd.concat([dip, extra], ignore_index=True)


class FailingProvider:
    def __init__(self, fail_symbols):
        self.fail_symbols = set(fail_symbols)
        self.calls = []

    def get_history(self, symbol, days=None):
        self.calls.append(symbol)
        if symbol in self.fail_symbols:
            raise ValueError(f"yfinance returned no history for {symbol}")
        return _dip_history()


def test_paper_only_guard_refuses_live(monkeypatch, tmp_path):
    monkeypatch.setenv("VAULTTEC_LIVE_TRADING_ENABLED", "true")
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        run_ava_daily(run_date=MONDAY, ava_dir=tmp_path,
                      evidence_file=tmp_path / "evidence.jsonl",
                      symbols=["AAPL"])
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED")
    monkeypatch.setenv("ALPACA_PAPER", "false")
    with pytest.raises(RuntimeError, match="live trading is enabled"):
        run_ava_daily(run_date=MONDAY, ava_dir=tmp_path,
                      evidence_file=tmp_path / "evidence.jsonl",
                      symbols=["AAPL"])


def test_first_run_opens_one_trade_and_writes_evidence(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_ava_daily(run_date=MONDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 1
    assert summary["trades_closed"] == 0
    state = load_state(tmp_path)
    assert state["last_processed_bar_date"]["AAPL"] == "2026-11-06"
    assert state["runs"] == 1
    assert len(state["open_positions"]) == 1
    pos = state["open_positions"][0]
    assert pos["symbol"] == "AAPL" and pos["strategy"] == "rsi"
    assert pos["trade_id"] == "AVA-2026-11-09-AAPL"
    assert pos["stop_loss"] == round(pos["entry_price"] * 0.94, 2)
    assert pos["take_profit"] > pos["entry_price"]
    assert state["cash_usd"] < 100.0  # her $100 pot was spent, not $10,000
    assert state["cash_usd"] > 85.0  # 10% position cap: about $10 a trade
    assert (tmp_path / "state.json").exists()
    assert (tmp_path / "ava-daily-report.md").exists()
    rows = _evidence_rows(evidence_file)
    assert len(rows) == 1
    row = rows[0]
    assert row["run"] == "daily" and row["run_date"] == "2026-11-09"
    assert row["trade_id"] == "AVA-2026-11-09-AAPL"
    assert row["status"] == "placed" and row["symbol"] == "AAPL"
    assert row["signal"] == "rsi"
    assert 0.0 <= row["confidence"] <= 0.85
    assert row["entry"] > 0 and row["stop"] > 0 and row["target"] > row["entry"]
    assert row["position_size"] > 0 and row["risk_usd"] > 0
    assert "Against first" in row["reasoning"]
    assert "For:" in row["reasoning"]
    assert "exit" not in row or row.get("exit") is None


def test_second_run_same_day_is_a_noop_with_no_duplicate_evidence(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    provider = StubProvider({"AAPL": _dip_history()})
    first = run_ava_daily(run_date=MONDAY, provider=provider,
                          ava_dir=tmp_path, evidence_file=evidence_file,
                          symbols=["AAPL"])
    assert first["trades_opened"] == 1
    second = run_ava_daily(run_date=MONDAY, provider=provider,
                           ava_dir=tmp_path, evidence_file=evidence_file,
                           symbols=["AAPL"])
    assert second["status"] == "already_processed"
    assert second["trades_opened"] == 0
    assert second["trades_closed"] == 0
    assert len(_evidence_rows(evidence_file)) == 1  # no duplicate record
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 1
    assert len(state["closed_trades"]) == 0


def test_next_day_flat_bar_does_not_duplicate_the_trade(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    dip = _dip_history()
    provider = StubProvider({"AAPL": dip})
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=tmp_path, evidence_file=evidence_file,
                  symbols=["AAPL"])
    flat = _next_bar_frame(dip, "2026-11-09", 86.06, 86.5, 85.5, 86.0)
    provider.frames["AAPL"] = flat
    summary = run_ava_daily(run_date=TUESDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 0  # already in the position
    assert summary["trades_closed"] == 0
    assert len(_evidence_rows(evidence_file)) == 1
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 1
    assert state["open_positions"][0]["bars_held"] == 1


def test_stop_hit_closes_trade_writes_closed_evidence_and_lesson(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    dip = _dip_history()
    provider = StubProvider({"AAPL": dip})
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=tmp_path, evidence_file=evidence_file,
                  symbols=["AAPL"])
    state = load_state(tmp_path)
    stop = state["open_positions"][0]["stop_loss"]
    # Next bar dives through the stop.
    crash = _next_bar_frame(dip, "2026-11-09", 86.06, 86.5, stop - 1.0, stop - 0.5)
    provider.frames["AAPL"] = crash
    summary = run_ava_daily(run_date=TUESDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 0  # no re-entry on the exit bar
    assert summary["trades_closed"] == 1
    assert summary["realised_pnl_usd"] < 0
    assert summary["lessons_learned"] == 1
    rows = _evidence_rows(evidence_file)
    assert len(rows) == 2
    closed = rows[1]
    assert closed["status"] == "closed"
    assert closed["trade_id"] == "AVA-2026-11-09-AAPL"
    assert closed["exit_reason"] == "stop-loss"
    assert closed["exit"] == stop
    assert closed["pnl_usd"] < 0 and closed["won"] is False
    assert closed["run"] == "daily" and closed["run_date"] == "2026-11-10"
    lessons = lessons_mod.load_lessons(limit=100)
    assert len(lessons) == 1
    assert lessons[0]["symbol"] == "AAPL" and lessons[0]["won"] is False
    assert "stop did its job" in lessons[0]["lesson"]
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 0
    assert len(state["closed_trades"]) == 1
    assert state["closed_trades"][0]["trade_id"] == "AVA-2026-11-09-AAPL"


def test_target_hit_closes_as_a_win(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    dip = _dip_history()
    provider = StubProvider({"AAPL": dip})
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=tmp_path, evidence_file=evidence_file,
                  symbols=["AAPL"])
    state = load_state(tmp_path)
    target = state["open_positions"][0]["take_profit"]
    # Next bar pops through the target.
    pop = _next_bar_frame(dip, "2026-11-09", 86.06, target + 1.0, 86.0, target + 0.5)
    provider.frames["AAPL"] = pop
    summary = run_ava_daily(run_date=TUESDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    assert summary["realised_pnl_usd"] > 0
    rows = _evidence_rows(evidence_file)
    assert rows[1]["exit_reason"] == "take-profit"
    assert rows[1]["won"] is True
    lessons = lessons_mod.load_lessons(limit=100)
    assert len(lessons) == 1 and lessons[0]["won"] is True


def test_time_exit_after_ten_bars(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    dip = _dip_history()
    provider = StubProvider({"AAPL": dip})
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=tmp_path, evidence_file=evidence_file,
                  symbols=["AAPL"])
    state = load_state(tmp_path)
    state["open_positions"][0]["bars_held"] = 9  # one bar from the exit
    save_state(tmp_path, state)
    flat = _next_bar_frame(dip, "2026-11-09", 86.06, 86.5, 85.5, 86.0)
    provider.frames["AAPL"] = flat
    summary = run_ava_daily(run_date=TUESDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    rows = _evidence_rows(evidence_file)
    assert "time exit" in rows[1]["exit_reason"]
    assert rows[1]["days_held"] == 10


def test_macd_complement_fires_when_mean_reversion_does_not(tmp_path, monkeypatch):
    """Flat, then a steady rise: RSI/Bollinger never fire, but the
    MACD crossover on the first rising bar does — and only once,
    not again on the following days."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    rising = _history(days=250, rise_from=210)
    # Day 1: latest completed bar is 2022-08-03 (flat). No trade.
    provider = StubProvider({"AAPL": rising.iloc[:210]})
    first = run_ava_daily(run_date=date(2022, 8, 4), provider=provider,
                          ava_dir=tmp_path, evidence_file=evidence_file,
                          symbols=["AAPL"])
    assert first["trades_opened"] == 0
    # Day 2: latest completed bar is 2022-08-04, the MACD cross.
    provider.frames["AAPL"] = rising.iloc[:211]
    second = run_ava_daily(run_date=date(2022, 8, 5), provider=provider,
                           ava_dir=tmp_path, evidence_file=evidence_file,
                           symbols=["AAPL"])
    assert second["trades_opened"] == 1
    rows = _evidence_rows(evidence_file)
    assert len(rows) == 1
    assert rows[0]["signal"] == "macd"
    assert rows[0]["trade_id"] == "AVA-2022-08-05-AAPL"
    # Day 3: still in the position — no duplicate trade.
    provider.frames["AAPL"] = rising.iloc[:212]
    third = run_ava_daily(run_date=date(2022, 8, 6), provider=provider,
                          ava_dir=tmp_path, evidence_file=evidence_file,
                          symbols=["AAPL"])
    assert third["trades_opened"] == 0
    assert len(_evidence_rows(evidence_file)) == 1


def test_too_small_trade_is_blocked_with_a_reason(tmp_path, monkeypatch):
    """A $100 pot cannot size a ~$200,000 stock: the trade is blocked
    as too small and the reason is written to the evidence log —
    never silently dropped, never placed."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    # The fall must END on the latest bar: a dip 80 bars ago has an
    # RSI that already recovered, and the daily runner only ever
    # trades the latest completed bar.
    huge = _history(days=170, fall_from=150, scale=2000.0)
    provider = StubProvider({"BTC-USD": huge})
    summary = run_ava_daily(run_date=date(2022, 9, 13), provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["BTC-USD"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 0
    assert summary["skipped_too_small"] > 0
    rows = _evidence_rows(evidence_file)
    assert rows
    assert all(row["status"] == "blocked" for row in rows)
    assert all("Too small" in row["block_reason"] for row in rows)
    state = load_state(tmp_path)
    assert state["open_positions"] == []
    assert state["cash_usd"] == 100.0


def test_total_fetch_failure_is_not_run_no_data(tmp_path, monkeypatch):
    """Every symbol fails to fetch: the run is recorded as not run —
    no data. No evidence, no trades, no cash change, no invented
    prices."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    provider = FailingProvider({"AAPL", "MSFT"})
    summary = run_ava_daily(run_date=MONDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL", "MSFT"])
    assert summary["status"] == "not_run_no_data"
    assert summary["reason"] == "not run — no data: all symbols failed to fetch"
    assert summary["trades_opened"] == 0
    assert not evidence_file.exists()  # nothing written at all
    state = load_state(tmp_path)
    assert state["open_positions"] == []
    assert state["cash_usd"] == 100.0
    assert state["fetch_failures"] == {"AAPL": 1, "MSFT": 1}
    assert state["run_history"][-1]["status"] == "not_run_no_data"


def test_kill_switch_blocks_the_run_without_fetching(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    (tmp_path / "STOP").write_text("stopped", encoding="utf-8")
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_ava_daily(run_date=MONDAY, provider=provider,
                            ava_dir=tmp_path, evidence_file=evidence_file,
                            symbols=["AAPL"])
    assert summary["status"] == "stopped"
    assert provider.calls == []  # never fetched
    assert summary["trades_opened"] == 0
    assert not evidence_file.exists()
    state = load_state(tmp_path)
    assert state["run_history"][-1]["status"] == "stopped"


def test_compute_summary_reports_the_pot_plainly(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    evidence_file = tmp_path / "evidence.jsonl"
    provider = StubProvider({"AAPL": _dip_history()})
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=tmp_path, evidence_file=evidence_file,
                  symbols=["AAPL"])
    s = compute_summary(load_state(tmp_path))
    assert s["starting_cash_usd"] == 100.0
    assert s["cash_usd"] < 100.0
    assert s["portfolio_value_usd"] == round(s["cash_usd"] + s["holdings_value_usd"], 2)
    assert s["closed_trades"] == 0 and s["win_rate_pct"] == 0.0
    assert s["open_positions"] == 1
