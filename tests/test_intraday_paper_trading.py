"""Intraday paper trading tests — stub providers only, no network.

The real run fetches delayed real hourly history from yfinance;
these tests never touch the network. They check the runner's
guarantees: a separate state dir and pot from the daily runner,
only completed in-session hourly bars traded, no look-ahead,
idempotency per hour, exit logic (stop / target / 10-session time
exit), session reporting (only closed trades count as wins or
losses — open positions never do), fetch-failure handling (no
invented prices), and the kill-switch.
"""
import json
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.intraday_paper_trading import (
    _completed_hourly_bars,
    _in_session_bars,
    compute_summary,
    default_intraday_dir,
    load_state,
    render_report,
    render_session_report,
    run_intraday,
    session_summary,
)
from vaulttec.live_paper_trading import default_live_dir

SESSION_STARTS = [time(9, 30), time(10, 30), time(11, 30), time(12, 30),
                  time(13, 30), time(14, 30), time(15, 30)]
RUN_MON = datetime(2026, 11, 9, 10, 35)  # Monday; latest completed bar is 09:30


def _session_starts(start: str, end: str) -> list[datetime]:
    """Every in-session hourly bar start between two dates, Mon–Fri."""
    out = []
    for d in pd.bdate_range(start=start, end=end):
        for t in SESSION_STARTS:
            out.append(datetime.combine(d.date(), t))
    return out


def _starts_through(end_bar: datetime, weeks: int = 6) -> list[datetime]:
    """Session bar starts from ~6 weeks back up to ``end_bar``."""
    start = end_bar.date() - timedelta(days=7 * weeks)
    all_starts = _session_starts(start.isoformat(), end_bar.date().isoformat())
    return [s for s in all_starts if s <= end_bar]


def _hourly_bars(starts, closes, highs=None, lows=None):
    """OHLCV frame from bar starts + closes (test stub only — never
    presented as real data). High/low hug the close so exits fire
    only when a bar is built to breach them."""
    rows = []
    prev = closes[0]
    for i, (s, close) in enumerate(zip(starts, closes)):
        high = highs[i] if highs is not None else round(max(prev, close) * 1.002, 2)
        low = lows[i] if lows is not None else round(min(prev, close) * 0.998, 2)
        rows.append({"date": pd.Timestamp(s), "open": prev,
                     "high": high, "low": low,
                     "close": round(close, 2), "volume": 1_000_000})
        prev = close
    return pd.DataFrame(rows)


def _flat_hourly(end_bar: datetime, weeks: int = 6) -> pd.DataFrame:
    """Flat at 100 from ~6 weeks back up to ``end_bar``."""
    starts = _starts_through(end_bar, weeks)
    return _hourly_bars(starts, [100.0] * len(starts))


def _dip_hourly(end_bar: datetime, weeks: int = 6) -> pd.DataFrame:
    """Flat at 100, then a steady 1%/hour fall for the last 15 bars:
    RSI collapses below 30 on the final bar, so the trigger fires
    on the latest completed bar."""
    starts = _starts_through(end_bar, weeks)
    closes = []
    price = 100.0
    n = len(starts)
    for i in range(n):
        if i >= n - 15:
            price *= 0.99
        closes.append(round(price, 2))
    return _hourly_bars(starts, closes)


def _append_bar(frame: pd.DataFrame, start: datetime, close: float,
                high: float | None = None, low: float | None = None) -> pd.DataFrame:
    """One more hourly bar on the end of a frame (test stub only)."""
    prev = float(frame["close"].iloc[-1])
    row = {"date": pd.Timestamp(start), "open": prev,
           "high": high if high is not None else round(max(prev, close) * 1.002, 2),
           "low": low if low is not None else round(min(prev, close) * 0.998, 2),
           "close": round(close, 2), "volume": 1_000_000}
    return pd.concat([frame, pd.DataFrame([row])], ignore_index=True)


class StubProvider:
    """Returns the frame currently set per symbol (tests mutate it
    between runs to simulate new hours arriving)."""

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
        return _dip_hourly(datetime(2026, 11, 9, 9, 30))


def test_default_dir_is_separate_from_daily():
    assert default_intraday_dir().name == "live_paper_intraday"
    assert default_intraday_dir() != default_live_dir()
    assert default_live_dir().name == "live_paper"


def test_first_run_processes_only_latest_completed_bar(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["session"] == "2026-11-09"
    assert summary["symbols_processed"] == ["AAPL"]
    state = load_state(tmp_path)
    # Only the latest completed bar (Mon 09:30) was processed; the
    # ~200 earlier bars were warm-up only.
    assert state["last_processed_bar"]["AAPL"] == "2026-11-09T09:30:00"
    assert state["runs"] == 1
    # The dip trigger fires on that bar: one paper trade opened.
    assert summary["trades_opened"] == 1
    assert len(state["open_positions"]) == 1
    pos = state["open_positions"][0]
    assert pos["symbol"] == "AAPL" and pos["strategy"] == "rsi"
    assert pos["stop_loss"] == round(pos["entry_price"] * 0.94, 2)
    assert pos["take_profit"] > pos["entry_price"]
    assert pos["entry_date"] == "2026-11-09"
    assert pos["entry_bar"] == "2026-11-09T09:30:00"
    assert pos["sessions_held"] == 0
    assert state["cash_usd"] < 10_000.0  # virtual cash was spent
    assert state["starting_cash_usd"] == 10_000.0
    assert (tmp_path / "state.json").exists()
    assert (tmp_path / "trades.jsonl").exists()
    assert (tmp_path / "live-paper-intraday-report.md").exists()


def test_second_run_same_hour_is_a_noop(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    first = run_intraday(run_time=RUN_MON, provider=provider,
                         live_dir=tmp_path, symbols=["AAPL"])
    assert first["status"] == "ok"
    second = run_intraday(run_time=RUN_MON, provider=provider,
                          live_dir=tmp_path, symbols=["AAPL"])
    assert second["status"] == "already_processed"
    assert second["trades_opened"] == 0
    assert second["trades_closed"] == 0
    state = load_state(tmp_path)
    assert state["runs"] == 2  # the run happened, it just changed nothing
    assert len(state["open_positions"]) == 1
    assert len(state["closed_trades"]) == 0


def test_next_hour_processes_next_bar(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    run_intraday(run_time=RUN_MON, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    entry = load_state(tmp_path)["open_positions"][0]["entry_price"]
    provider.frames["AAPL"] = _append_bar(
        provider.frames["AAPL"], datetime(2026, 11, 9, 10, 30), entry)
    summary = run_intraday(run_time=datetime(2026, 11, 9, 11, 35),
                           provider=provider, live_dir=tmp_path,
                           symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["symbols_processed"] == ["AAPL"]
    assert summary["trades_opened"] == 0  # position already open
    state = load_state(tmp_path)
    assert state["last_processed_bar"]["AAPL"] == "2026-11-09T10:30:00"
    assert len(state["open_positions"]) == 1
    assert state["open_positions"][0]["bars_held"] == 1


def test_forming_bar_is_not_traded(tmp_path):
    # Flat at 100 through Mon 09:30 (no trigger), then a 10:30 bar
    # that drops 15% in one hour — it must not open a trade until
    # its hour has fully ended.
    frame = _flat_hourly(datetime(2026, 11, 9, 9, 30))
    frame = _append_bar(frame, datetime(2026, 11, 9, 10, 30), 85.0)
    provider = StubProvider({"AAPL": frame})
    first = run_intraday(run_time=RUN_MON, provider=provider,
                         live_dir=tmp_path, symbols=["AAPL"])
    assert first["trades_opened"] == 0
    assert load_state(tmp_path)["last_processed_bar"]["AAPL"] == "2026-11-09T09:30:00"
    # An hour later the 10:30 bar is complete: the dip is real now.
    second = run_intraday(run_time=datetime(2026, 11, 9, 11, 35),
                          provider=provider, live_dir=tmp_path,
                          symbols=["AAPL"])
    assert second["trades_opened"] == 1
    assert load_state(tmp_path)["open_positions"][0]["entry_price"] == 85.0


def test_completed_hourly_bars_cutoff():
    frame = _hourly_bars(
        [datetime(2026, 11, 10, 9, 30), datetime(2026, 11, 10, 10, 30),
         datetime(2026, 11, 10, 11, 30)], [100.0, 100.0, 100.0])
    # At 10:35 only the 09:30 bar (ended 10:30) is complete.
    done = _completed_hourly_bars(frame, datetime(2026, 11, 10, 10, 35))
    assert list(done["date"]) == [pd.Timestamp("2026-11-10 09:30:00")]
    # At 11:30 the 10:30 bar (ended 11:30) joins it.
    done = _completed_hourly_bars(frame, datetime(2026, 11, 10, 11, 30))
    assert len(done) == 2
    # A minute earlier it does not.
    done = _completed_hourly_bars(frame, datetime(2026, 11, 10, 11, 29))
    assert len(done) == 1


def test_out_of_session_bars_ignored(tmp_path):
    # A dip at 08:30 (before the open) must not open a trade; the
    # in-session bars are flat, so nothing fires.
    frame = _flat_hourly(datetime(2026, 11, 9, 9, 30))
    pre = pd.DataFrame([{"date": pd.Timestamp("2026-11-09 08:30:00"),
                         "open": 100.0, "high": 100.2, "low": 84.8,
                         "close": 85.0, "volume": 1_000_000}])
    frame = pd.concat([pre, frame], ignore_index=True)
    frame = _append_bar(frame, datetime(2026, 11, 9, 17, 30), 85.0)
    provider = StubProvider({"AAPL": frame})
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["trades_opened"] == 0
    assert len(load_state(tmp_path)["open_positions"]) == 0
    assert load_state(tmp_path)["last_processed_bar"]["AAPL"] == "2026-11-09T09:30:00"


def test_crypto_bars_only_in_session():
    # Crypto-style hourly bars on the hour, around the clock: only
    # the 10:00–15:00 starts fall inside the 9:30–4:00 session.
    starts = [datetime(2026, 11, 10, h, 0) for h in range(24)]
    frame = _hourly_bars(starts, [100.0] * 24)
    kept = _in_session_bars(frame)
    assert [d.hour for d in kept["date"]] == [10, 11, 12, 13, 14, 15]
    # Stock-style bars (09:30–15:30) all survive.
    stock = _hourly_bars(
        [datetime(2026, 11, 10, 9, 30) + timedelta(minutes=60 * i)
         for i in range(7)], [100.0] * 7)
    assert len(_in_session_bars(stock)) == 7


def _open_position(tmp_path, provider):
    """Run 1 (Mon 10:35) on a dip history; returns the position."""
    run_intraday(run_time=RUN_MON, provider=provider,
                 live_dir=tmp_path, symbols=["AAPL"])
    return load_state(tmp_path)["open_positions"][0]


def test_stop_hit_closes_at_stop(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    pos = _open_position(tmp_path, provider)
    entry, stop = pos["entry_price"], pos["stop_loss"]
    provider.frames["AAPL"] = _append_bar(
        provider.frames["AAPL"], datetime(2026, 11, 10, 9, 30), entry,
        low=round(stop - 1.0, 2))
    summary = run_intraday(run_time=datetime(2026, 11, 10, 10, 35),
                           provider=provider, live_dir=tmp_path,
                           symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    assert summary["session_wins"] == 0
    assert summary["session_losses"] == 1
    state = load_state(tmp_path)
    closed = state["closed_trades"][0]
    assert closed["exit_reason"] == "stop-loss"
    assert closed["exit_price"] == stop
    assert closed["pnl_usd"] < 0
    assert closed["exit_session"] == "2026-11-10"
    assert closed["sessions_held"] == 1


def test_target_hit_closes_at_target(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    pos = _open_position(tmp_path, provider)
    entry, take = pos["entry_price"], pos["take_profit"]
    provider.frames["AAPL"] = _append_bar(
        provider.frames["AAPL"], datetime(2026, 11, 10, 9, 30), entry,
        high=round(take + 1.0, 2))
    summary = run_intraday(run_time=datetime(2026, 11, 10, 10, 35),
                           provider=provider, live_dir=tmp_path,
                           symbols=["AAPL"])
    assert summary["trades_closed"] == 1
    assert summary["session_wins"] == 1
    assert summary["session_losses"] == 0
    state = load_state(tmp_path)
    closed = state["closed_trades"][0]
    assert closed["exit_reason"] == "take-profit"
    assert closed["exit_price"] == take
    assert closed["pnl_usd"] > 0


def test_time_exit_after_ten_sessions(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    pos = _open_position(tmp_path, provider)
    entry = pos["entry_price"]
    # Ten more sessions, one flat 09:30 bar each. The position must
    # survive nine of them and exit on the first bar of the tenth.
    sessions = pd.bdate_range(start="2026-11-10", end="2026-11-23")
    assert len(sessions) == 10
    for i, d in enumerate(sessions):
        provider.frames["AAPL"] = _append_bar(
            provider.frames["AAPL"],
            datetime.combine(d.date(), time(9, 30)), entry)
        summary = run_intraday(
            run_time=datetime.combine(d.date(), time(10, 35)),
            provider=provider, live_dir=tmp_path, symbols=["AAPL"])
        state = load_state(tmp_path)
        if i < 9:
            assert summary["trades_closed"] == 0, f"closed too early on {d.date()}"
            assert len(state["open_positions"]) == 1
            assert state["open_positions"][0]["sessions_held"] == i + 1
    state = load_state(tmp_path)
    closed = state["closed_trades"][0]
    assert closed["exit_reason"] == "time exit (10 sessions)"
    assert closed["sessions_held"] == 10
    assert closed["days_held"] == 10
    assert closed["exit_session"] == "2026-11-23"
    assert summary["session_wins"] + summary["session_losses"] == 1


def test_total_fetch_failure_records_no_trades(tmp_path):
    provider = FailingProvider(fail_symbols={"AAPL"})
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "fetch_failed"
    assert summary["trades_opened"] == 0
    assert summary["trades_closed"] == 0
    state = load_state(tmp_path)
    assert state["cash_usd"] == 10_000.0
    assert state["open_positions"] == []
    assert state["closed_trades"] == []
    assert state["fetch_failures"]["AAPL"] == 1


def test_partial_fetch_failure_other_symbol_still_trades(tmp_path):
    # FailingProvider returns the dip history for symbols it does
    # not fail, so AAPL trades while MSFT is recorded as failed.
    provider = FailingProvider(fail_symbols={"MSFT"})
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL", "MSFT"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 1
    assert "MSFT" in summary["failed_symbols"]
    assert load_state(tmp_path)["fetch_failures"]["MSFT"] == 1


def test_kill_switch_blocks_without_fetching(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    (tmp_path / "STOP").write_text("stop\n", encoding="utf-8")
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "stopped"
    assert provider.calls == []  # nothing fetched
    assert summary["trades_opened"] == 0
    state = load_state(tmp_path)
    assert state["open_positions"] == []
    # Removing the switch lets the next run trade.
    (tmp_path / "STOP").unlink()
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "ok"
    assert summary["trades_opened"] == 1


def test_disabled_state_blocks(tmp_path):
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    state = load_state(tmp_path)
    state["enabled"] = False
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    summary = run_intraday(run_time=RUN_MON, provider=provider,
                           live_dir=tmp_path, symbols=["AAPL"])
    assert summary["status"] == "stopped"
    assert provider.calls == []


def test_session_report_counts_only_closed_trades(tmp_path):
    # Run 1 (Mon): AAPL, MSFT and GOOGL all open on the dip.
    frames = {s: _dip_hourly(datetime(2026, 11, 9, 9, 30))
              for s in ("AAPL", "MSFT", "GOOGL")}
    provider = StubProvider(frames)
    first = run_intraday(run_time=RUN_MON, provider=provider,
                         live_dir=tmp_path,
                         symbols=["AAPL", "MSFT", "GOOGL"])
    assert first["trades_opened"] == 3
    state = load_state(tmp_path)
    entries = {p["symbol"]: p for p in state["open_positions"]}
    # Run 2 (Tue 09:30 bar): AAPL hits its stop (a loss), MSFT hits
    # its target (a win), GOOGL is flat and stays open.
    for symbol, kwargs in (
            ("AAPL", {"low": round(entries["AAPL"]["stop_loss"] - 1.0, 2)}),
            ("MSFT", {"high": round(entries["MSFT"]["take_profit"] + 1.0, 2)}),
            ("GOOGL", {})):
        entry = entries[symbol]["entry_price"]
        provider.frames[symbol] = _append_bar(
            provider.frames[symbol], datetime(2026, 11, 10, 9, 30),
            entry, **kwargs)
    second = run_intraday(run_time=datetime(2026, 11, 10, 10, 35),
                          provider=provider, live_dir=tmp_path,
                          symbols=["AAPL", "MSFT", "GOOGL"])
    assert second["trades_closed"] == 2
    assert second["session_wins"] == 1
    assert second["session_losses"] == 1
    assert second["total_pnl_usd"] == second["session_pnl_usd"]
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 1  # GOOGL only
    assert state["open_positions"][0]["symbol"] == "GOOGL"

    # The session report: Tue has 1 win + 1 loss; Mon has none.
    tue = session_summary(state, "2026-11-10")
    assert tue["wins"] == 1 and tue["losses"] == 1 and tue["closed"] == 2
    assert tue["session_pnl_usd"] == second["session_pnl_usd"]
    assert tue["total_pnl_usd"] == second["total_pnl_usd"]
    assert tue["open_count"] == 1
    assert tue["open_positions"][0]["symbol"] == "GOOGL"
    assert "unrealised_pnl_usd" in tue["open_positions"][0]
    mon = session_summary(state, "2026-11-09")
    assert mon["wins"] == 0 and mon["losses"] == 0 and mon["closed"] == 0

    text = render_session_report(state, "2026-11-10")
    assert "Wins: **1**" in text
    assert "losses: **1**" in text
    assert "Still open — not wins or losses" in text
    assert "GOOGL" in text
    assert "Total profit so far" in text
    # The running report carries the same latest-session numbers.
    full = render_report(state)
    assert "This session — 2026-11-10" in full
    summary = compute_summary(state)
    assert summary["wins"] == 1 and summary["losses"] == 1
    assert summary["latest_session"]["session"] == "2026-11-10"


def test_flat_position_never_renders_minus_zero_unrealised(tmp_path):
    # Real yfinance closes are unrounded (e.g. 2127.1249) while the
    # stored last close is rounded to cents (2127.12): a flat open
    # position used to render as -$0.00. It must be $+0.00.
    state = load_state(tmp_path)
    state["open_positions"] = [{
        "symbol": "ETH-USD", "strategy": "rsi",
        "entry_date": "2026-11-09", "entry_bar": "2026-11-09T15:30:00",
        "entry_price": 2127.1249, "quantity": 0.4701,
        "stop_loss": 1999.49, "take_profit": 2318.57,
        "bars_held": 0, "sessions_held": 0, "last_session": "2026-11-09",
    }]
    state["last_close"] = {"ETH-USD": 2127.12}
    summary = session_summary(state, "2026-11-10")
    assert summary["open_positions"][0]["unrealised_pnl_usd"] == 0.0
    assert summary["unrealised_pnl_usd"] == 0.0
    text = render_session_report(state, "2026-11-10")
    assert "-0.00" not in text
    assert "+0.00" in text


def test_intraday_state_separate_from_daily(tmp_path):
    intra_dir = tmp_path / "intra"
    daily_dir = tmp_path / "live_paper"
    provider = StubProvider({"AAPL": _dip_hourly(datetime(2026, 11, 9, 9, 30))})
    run_intraday(run_time=RUN_MON, provider=provider,
                 live_dir=intra_dir, symbols=["AAPL"])
    # The daily runner's directory was never touched.
    assert not daily_dir.exists()
    state = load_state(intra_dir)
    assert state["starting_cash_usd"] == 10_000.0
    assert len(state["open_positions"]) == 1
