"""Live paper trading tests — stub providers only, no network.

The real run fetches delayed real history from yfinance; these
tests never touch the network. They check the runner's guarantees:
durable state, idempotency per day, exit logic (stop / target /
time), no look-ahead (only completed bars are traded), holiday /
no-new-bar handling, fetch-failure handling (no invented prices),
and the kill-switch.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.live_paper_trading import (
    HORIZON_BARS,
    compute_summary,
    load_state,
    render_report,
    run_live_day,
)

RUN_DATE = date(2026, 11, 9)  # a Monday; last completed stock bar is Fri 2026-11-06


def _bars(dates, closes):
    """OHLCV frame from a list of dates + closes (test stub only —
    never presented as real data). High/low hug the close so exits
    fire only when the close itself moves far enough."""
    rows = []
    prev = closes[0]
    for d, close in zip(dates, closes):
        rows.append({"date": pd.Timestamp(d), "open": prev,
                     "high": round(max(prev, close) * 1.002, 2),
                     "low": round(min(prev, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
        prev = close
    return pd.DataFrame(rows)


def _dip_history(end="2026-11-06", days=100):
    """Flat at 100, then a steady 1%/day fall for the last 15 bars:
    RSI collapses below 30 on the final bar, so the trigger fires
    on the latest completed bar."""
    dates = pd.bdate_range(end=end, periods=days)
    closes = []
    price = 100.0
    for i in range(days):
        if i >= days - 15:
            price *= 0.99
        closes.append(price)
    return _bars([str(d)[:10] for d in dates], closes)


class StubProvider:
    """Returns the frame currently set per symbol (tests mutate it
    between runs to simulate new days arriving)."""

    def __init__(self, frames):
        self.frames = frames  # symbol -> DataFrame
        self.calls = []

    def get_history(self, symbol, days=None):
        self.calls.append(symbol)
        return self.frames[symbol].copy()


class FailingProvider:
    def __init__(self, fail_symbols):
        self.fail_symbols = set(fail_symbols)
        self.calls = []

    def get_history(self, symbol, days=None):
        self.calls.append(symbol)
        if symbol in self.fail_symbols:
            raise ValueError(f"yfinance returned no history for {symbol}")
        return _dip_history()


def test_first_run_processes_only_the_latest_completed_bar(tmp_path):
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_live_day(run_date=RUN_DATE, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["symbols_processed"] == ["AAPL"]
    state = load_state(tmp_path)
    # Only the latest completed bar (Fri 2026-11-06) was processed;
    # the 99 earlier bars were warm-up only.
    assert state["last_processed_bar_date"]["AAPL"] == "2026-11-06"
    assert state["runs"] == 1
    # The dip trigger fires on that bar: one paper trade opened.
    assert summary["trades_opened"] == 1
    assert len(state["open_positions"]) == 1
    pos = state["open_positions"][0]
    assert pos["symbol"] == "AAPL" and pos["strategy"] == "rsi"
    assert pos["stop_loss"] == round(pos["entry_price"] * 0.94, 2)
    assert pos["take_profit"] > pos["entry_price"]
    assert state["cash_usd"] < 10_000.0  # virtual cash was spent
    assert (tmp_path / "state.json").exists()
    assert (tmp_path / "trades.jsonl").exists()
    assert (tmp_path / "live-paper-report.md").exists()


def test_second_run_same_day_is_a_noop(tmp_path):
    provider = StubProvider({"AAPL": _dip_history()})
    first = run_live_day(run_date=RUN_DATE, provider=provider,
                         live_dir=tmp_path, symbols=["AAPL"])
    second = run_live_day(run_date=RUN_DATE, provider=provider,
                          live_dir=tmp_path, symbols=["AAPL"])
    assert second["status"] == "already_processed"
    assert second["trades_opened"] == 0
    assert second["trades_closed"] == 0
    state = load_state(tmp_path)
    assert state["runs"] == 2  # the run happened, it just changed nothing
    assert len(state["open_positions"]) == 1
    assert len(state["closed_trades"]) == 0
    assert state["cash_usd"] == first["cash_usd"]


def test_state_persists_across_runs_and_position_survives(tmp_path):
    frames = {"AAPL": _dip_history()}
    provider = StubProvider(frames)
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    # Next day: one flat bar arrives (close == entry, no exit).
    # Business days: 2026-11-06 Fri -> 2026-11-09 Mon.
    last = frames["AAPL"].iloc[-1]
    new_row = {"date": pd.Timestamp("2026-11-09"), "open": last["close"],
               "high": round(last["close"] * 1.002, 2),
               "low": round(last["close"] * 0.998, 2),
               "close": last["close"], "volume": 1_000_000}
    frames["AAPL"] = pd.concat(
        [frames["AAPL"], pd.DataFrame([new_row])], ignore_index=True)
    summary = run_live_day(run_date=date(2026, 11, 10), provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 0  # already in a position
    assert summary["trades_closed"] == 0  # flat bar hits no exit
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 1
    assert state["open_positions"][0]["bars_held"] == 1
    assert state["last_processed_bar_date"]["AAPL"] == "2026-11-09"


def test_stop_loss_exit_real(tmp_path):
    frames = {"AAPL": _dip_history()}
    provider = StubProvider(frames)
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    entry = load_state(tmp_path)["open_positions"][0]["entry_price"]
    crash = round(entry * 0.93, 2)
    last = frames["AAPL"].iloc[-1]
    row = {"date": pd.Timestamp("2026-11-09"), "open": last["close"],
           "high": round(max(last["close"], crash) * 1.002, 2),
           "low": round(min(last["close"], crash) * 0.998, 2),
           "close": crash, "volume": 1_000_000}
    frames["AAPL"] = pd.concat(
        [frames["AAPL"], pd.DataFrame([row])], ignore_index=True)
    summary = run_live_day(run_date=date(2026, 11, 10), provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    state = load_state(tmp_path)
    assert state["open_positions"] == []
    trade = state["closed_trades"][0]
    assert trade["exit_reason"] == "stop-loss"
    assert trade["exit_price"] == round(entry * 0.94, 2)
    assert trade["pnl_usd"] < 0
    assert trade["days_held"] == 1


def test_take_profit_exit(tmp_path):
    frames = {"AAPL": _dip_history()}
    provider = StubProvider(frames)
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    entry = load_state(tmp_path)["open_positions"][0]["entry_price"]
    rally = round(entry * 1.10, 2)
    last = frames["AAPL"].iloc[-1]
    row = {"date": pd.Timestamp("2026-11-09"), "open": last["close"],
           "high": round(max(last["close"], rally) * 1.002, 2),
           "low": round(min(last["close"], rally) * 0.998, 2),
           "close": rally, "volume": 1_000_000}
    frames["AAPL"] = pd.concat(
        [frames["AAPL"], pd.DataFrame([row])], ignore_index=True)
    summary = run_live_day(run_date=date(2026, 11, 10), provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    trade = load_state(tmp_path)["closed_trades"][0]
    assert trade["exit_reason"] == "take-profit"
    assert trade["exit_price"] == round(entry * 1.09, 2) or trade["exit_price"] >= entry * 1.09 - 0.02
    assert trade["pnl_usd"] > 0


def test_no_same_bar_reentry_after_stop_out(tmp_path):
    """After a position stops out on a bar, the runner must NOT buy
    straight back into the same falling bar — the trigger is still
    firing (price fell further), but re-entering the same bar it
    just stopped out of would churn, and the validated walk-forward
    never re-entered inside one window."""
    frames = {"AAPL": _dip_history()}
    provider = StubProvider(frames)
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    entry = load_state(tmp_path)["open_positions"][0]["entry_price"]
    crash = round(entry * 0.93, 2)
    last = frames["AAPL"].iloc[-1]
    row = {"date": pd.Timestamp("2026-11-09"), "open": last["close"],
           "high": round(max(last["close"], crash) * 1.002, 2),
           "low": round(min(last["close"], crash) * 0.998, 2),
           "close": crash, "volume": 1_000_000}
    frames["AAPL"] = pd.concat(
        [frames["AAPL"], pd.DataFrame([row])], ignore_index=True)
    summary = run_live_day(run_date=date(2026, 11, 10), provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    assert summary["trades_opened"] == 0
    assert load_state(tmp_path)["open_positions"] == []


def test_time_exit_after_ten_bars(tmp_path):
    frames = {"AAPL": _dip_history()}
    provider = StubProvider(frames)
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    entry = load_state(tmp_path)["open_positions"][0]["entry_price"]
    # Ten flat business days: no stop, no target — the 10th bar
    # must close the position on the time exit.
    days = pd.bdate_range(start="2026-11-09", periods=10)
    for i, day in enumerate(days):
        last = frames["AAPL"].iloc[-1]
        row = {"date": day, "open": last["close"],
               "high": round(entry * 1.002, 2), "low": round(entry * 0.998, 2),
               "close": entry, "volume": 1_000_000}
        frames["AAPL"] = pd.concat(
            [frames["AAPL"], pd.DataFrame([row])], ignore_index=True)
        summary = run_live_day(run_date=(day + pd.Timedelta(days=1)).date(),
                               provider=provider, live_dir=tmp_path,
                               symbols=["AAPL"])
        if i < 9:
            assert summary["trades_closed"] == 0, f"closed early on bar {i + 1}"
    state = load_state(tmp_path)
    assert len(state["closed_trades"]) == 1
    trade = state["closed_trades"][0]
    assert trade["exit_reason"] == f"time exit ({HORIZON_BARS} days)"
    assert trade["days_held"] == HORIZON_BARS


def test_no_look_ahead_uncompleted_bar_is_never_traded(tmp_path):
    """The dip happens only on the run-date bar itself (still
    forming, not completed) — the runner must not trade on it."""
    dates = pd.bdate_range(end="2026-11-09", periods=100)
    # Flat at 100 through the last *completed* bar (Fri 2026-11-06);
    # the only down bar is Mon 2026-11-09 itself, which is not
    # completed yet on the run date.
    closes = [100.0] * 99 + [99.0]
    frames = {"AAPL": _bars([str(d)[:10] for d in dates], closes)}
    provider = StubProvider(frames)
    summary = run_live_day(run_date=RUN_DATE, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    # The latest *completed* bar is 2026-11-06, flat at 100 — no
    # trigger there, even though the uncompleted 2026-11-09 bar
    # (99.0) would trigger if it were traded on.
    assert summary["trades_opened"] == 0
    assert load_state(tmp_path)["open_positions"] == []
    assert load_state(tmp_path)["last_processed_bar_date"]["AAPL"] == "2026-11-06"


def test_holiday_or_weekend_with_no_new_bar_is_skipped(tmp_path):
    # Run on Monday (processes Fri bar), then run again on Sunday:
    # no new completed stock bar exists, so nothing happens.
    provider = StubProvider({"AAPL": _dip_history()})
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    summary = run_live_day(run_date=date(2026, 11, 15), provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "already_processed"
    assert summary["symbols_processed"] == []
    assert summary["trades_opened"] == 0
    assert summary["trades_closed"] == 0


def test_fetch_failure_is_recorded_and_invents_no_trade(tmp_path):
    provider = FailingProvider(fail_symbols={"AAPL"})
    summary = run_live_day(run_date=RUN_DATE, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "fetch_failed"
    assert summary["trades_opened"] == 0
    state = load_state(tmp_path)
    assert state["open_positions"] == []
    assert state["closed_trades"] == []
    assert state["cash_usd"] == 10_000.0  # untouched
    assert state["fetch_failures"].get("AAPL", 0) >= 1
    log = (tmp_path / "trades.jsonl").read_text()
    assert "fetch_failed" in log


def test_partial_fetch_failure_trades_the_symbols_that_work(tmp_path):
    provider = FailingProvider(fail_symbols={"MSFT"})
    summary = run_live_day(run_date=RUN_DATE, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL", "MSFT"])
    assert summary["status"] == "ok"
    assert summary["symbols_processed"] == ["AAPL"]
    assert "MSFT" in summary["failed_symbols"]
    assert summary["trades_opened"] == 1


def test_kill_switch_blocks_entries_without_fetching(tmp_path):
    (tmp_path / "STOP").write_text("stopped for testing\n")
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_live_day(run_date=RUN_DATE, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "stopped"
    assert provider.calls == []  # nothing was fetched
    assert summary["trades_opened"] == 0
    state = load_state(tmp_path)
    assert state["runs"] == 0  # a stopped run is not counted as a run


def test_default_live_dir_is_inside_the_vaulttec_project(tmp_path):
    """Regression: default_live_dir() must resolve to
    <project root>/live_paper — the module lives at
    vaulttec/vaulttec/live_paper_trading.py, so parents[1] is the
    project root. (An earlier parents[2] wrote state one folder
    too high, next to the project instead of inside it.)"""
    from vaulttec.live_paper_trading import LIVE_DIR_NAME, default_live_dir

    assert default_live_dir().name == LIVE_DIR_NAME
    assert default_live_dir().parent.name == "vaulttec"
    assert default_live_dir().parent.joinpath("app.py").exists()


def test_report_states_paper_only_and_no_profit_promise(tmp_path):
    provider = StubProvider({"AAPL": _dip_history()})
    run_live_day(run_date=RUN_DATE, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    state = load_state(tmp_path)
    text = render_report(state)
    assert "PAPER ONLY" in text
    assert "no real money" in text.lower()
    assert "does not guarantee future results" in text
    assert "wide-6" in text
    summary = compute_summary(state)
    assert summary["paper_only"] is True
    assert summary["closed_trades"] == 0
    assert summary["open_positions"] == 1
    assert summary["portfolio_value_usd"] > 0
    # The saved report file says the same thing.
    saved = (tmp_path / "live-paper-report.md").read_text()
    assert "PAPER ONLY" in saved
    log_lines = [json.loads(line) for line in
                 (tmp_path / "trades.jsonl").read_text().splitlines()]
    assert any(e["event"] == "trade_opened" for e in log_lines)
    assert all(e.get("paper_only") for e in log_lines)
