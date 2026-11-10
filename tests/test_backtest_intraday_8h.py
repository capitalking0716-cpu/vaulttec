"""8-hour intraday backtest tests — stub providers only, no network.

These tests lock in the backtest's guarantees: the window is
exactly the most recent 8 completed hourly bars (a still-forming
bar and any bar after the window end are never traded), the
checkpoints drive the real runner bar by bar in order with the
first call's warm-up landing on the first window bar, the $100
pot scales (10% per trade, fractional shares — a $95k-priced
symbol still trades at 0.0001 shares), and no look-ahead ever
happens. Prices here are fabricated for determinism; the real
backtest uses real yfinance bars.
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.backtest_intraday_8h import (  # noqa: E402
    build_checkpoints,
    run_backtest,
    verify_first_checkpoint,
    window_bars,
)

NY = ZoneInfo("America/New_York")
NOW = datetime(2026, 11, 11, 12, 16, tzinfo=NY)

# Sessions: Thu 11-05, Fri 11-06, Mon 11-09, Tue 11-10, Wed 11-11.
# Stock bars start 9:30, 10:30, 11:30, 12:30, 13:30, 14:30, 15:30.
# Crypto bars start 10:00, 11:00, 12:00, 13:00, 14:00, 15:00.
STOCK_STARTS = ["09:30", "10:30", "11:30", "12:30", "13:30", "14:30", "15:30"]
CRYPTO_STARTS = ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"]
DAYS = ["2026-11-05", "2026-11-06", "2026-11-09", "2026-11-10", "2026-11-11"]


def _frame(starts, closes_by_slot):
    """closes_by_slot: list of (day_index, slot_index, close). All
    other closes default to the series base (100 / 95,000)."""
    rows = []
    for day_idx, day in enumerate(DAYS):
        for slot_idx, start in enumerate(starts):
            close = closes_by_slot.get((day_idx, slot_idx))
            if close is None:
                close = 100.0
            dt = datetime.fromisoformat(f"{day}T{start}:00")
            rows.append({"date": dt, "open": close, "high": close,
                         "low": close, "close": close, "volume": 1000})
    return pd.DataFrame(rows)


def _test_frame():
    """Flat 100, then a drop to 85 at Tue 14:30 (fires the mean-
    reversion trigger), flat 85, then a bounce to 95 at Wed 9:30
    (high 95 clears the 92.65 target). Wed 11:30 (close 50) and
    Wed 12:30 (close 200) are still-forming / future bars that
    must never be touched."""
    closes = {(3, 5): 85.0, (3, 6): 85.0, (4, 0): 95.0, (4, 1): 95.0,
              (4, 2): 50.0, (4, 3): 200.0}
    return _frame(STOCK_STARTS, closes)


def _high_frame():
    """A $95,000-priced symbol: flat, then a drop to $80,000 at
    Tue 14:30 (fires), flat after — it stays open to the end of
    the window, so fractional sizing at $100 is exercised."""
    rows = []
    for day_idx, day in enumerate(DAYS):
        for slot_idx, start in enumerate(STOCK_STARTS):
            close = 95000.0
            if (day_idx, slot_idx) in {(3, 5), (3, 6), (4, 0), (4, 1),
                                       (4, 2), (4, 3)}:
                close = 80000.0
            dt = datetime.fromisoformat(f"{day}T{start}:00")
            rows.append({"date": dt, "open": close, "high": close,
                         "low": close, "close": close, "volume": 10})
    return pd.DataFrame(rows)


def _crypto_frame():
    """Flat 1,000, never triggers — it only exercises the mixed
    stock/crypto checkpoint grid."""
    closes = {}
    return _frame(CRYPTO_STARTS, closes)


class StubProvider:
    def __init__(self, frames):
        self._frames = frames

    def get_history(self, symbol, days=None):
        return self._frames[symbol].copy()


def _frames():
    return {"TEST": _test_frame(), "HIGH": _high_frame(),
            "CRYP": _crypto_frame()}


def _run(tmp_path):
    return run_backtest(
        symbols=["TEST", "HIGH", "CRYP"], cash=100.0, n_bars=8,
        now=NOW, provider=StubProvider(_frames()),
        scratch_dir=tmp_path / "scratch")


def test_window_is_last_8_completed_bars():
    frame = _test_frame()
    bars = window_bars(frame, NOW.replace(tzinfo=None), n=8)
    assert len(bars) == 8
    first = pd.Timestamp(bars["date"].iloc[0]).to_pydatetime()
    last = pd.Timestamp(bars["date"].iloc[-1]).to_pydatetime()
    assert first == datetime(2026, 11, 10, 10, 30)
    assert last == datetime(2026, 11, 11, 10, 30)
    # The still-forming 11:30 bar and the future 12:30 bar are out.
    dates = [pd.Timestamp(d).to_pydatetime() for d in bars["date"]]
    assert datetime(2026, 11, 11, 11, 30) not in dates
    assert datetime(2026, 11, 11, 12, 30) not in dates


def test_checkpoints_cover_window_in_order():
    frames = _frames()
    now_naive = NOW.replace(tzinfo=None)
    window = {s: window_bars(frames[s], now_naive, 8) for s in frames}
    checkpoints = build_checkpoints(window)
    assert checkpoints == sorted(checkpoints)
    # First checkpoint is just past the joint first completion
    # (stock Tue 10:30 completes 11:30; crypto Tue 10:00 completes
    # 11:00) — 11:35.
    assert checkpoints[0] == datetime(2026, 11, 10, 11, 35)
    # Last checkpoint is just past the last window bar's completion
    # (crypto Wed 11:00 completes 12:00).
    assert checkpoints[-1] == datetime(2026, 11, 11, 12, 5)
    # The first call's warm-up must land on the first window bar.
    verify_first_checkpoint(frames, window, checkpoints[0])


def test_backtest_100_pot_entry_exit_and_fractional_sizing(tmp_path):
    result = _run(tmp_path)
    assert result["status"] == "ok"
    assert result["starting_cash_usd"] == 100.0
    # TEST enters on the Tue 14:30 drop and exits at its 9% target
    # on the Wed 9:30 bounce; HIGH enters on its drop and stays open.
    assert result["trades_opened"] == 2
    assert result["trades_closed"] == 1
    assert result["wins"] == 1
    assert result["losses"] == 0
    # TEST: 0.1176 shares @ 85, exit 92.65 -> +$0.90.
    assert result["total_pnl_usd"] == pytest.approx(0.90, abs=0.01)
    # Cash: 100 - 9.996 (TEST) - 8.00 (HIGH) + 10.896 (TEST exit).
    assert result["cash_usd"] == pytest.approx(92.90, abs=0.01)
    assert result["holdings_value_usd"] == pytest.approx(8.00, abs=0.01)
    assert result["portfolio_value_usd"] == pytest.approx(100.90, abs=0.01)
    closed = result["closed_trades"]
    assert len(closed) == 1
    assert closed[0]["symbol"] == "TEST"
    assert closed[0]["entry_bar"] == "2026-11-10T14:30:00"
    assert closed[0]["exit_bar"] == "2026-11-11T09:30:00"
    assert closed[0]["exit_reason"] == "take-profit"
    assert closed[0]["pnl_usd"] == pytest.approx(0.90, abs=0.01)
    # HIGH is still open at 0.0001 shares — fractional sizing works.
    open_positions = result["open_positions"]
    assert len(open_positions) == 1
    assert open_positions[0]["symbol"] == "HIGH"
    assert open_positions[0]["quantity"] == pytest.approx(0.0001, abs=1e-9)
    assert open_positions[0]["unrealised_pnl_usd"] == pytest.approx(0.0, abs=0.01)
    assert result["per_symbol"]["TEST"]["trades"] == 1
    assert result["per_symbol"]["TEST"]["wins"] == 1
    assert "CRYP" not in result["per_symbol"]


def test_no_lookahead_future_bars_never_processed(tmp_path):
    result = _run(tmp_path)
    for symbol, last in result["window"].items():
        assert result["processed_ok"][symbol] is True
    # Every symbol's last processed bar is its last window bar —
    # the still-forming Wed 11:30 bar (close 50) and the future
    # Wed 12:30 bar (close 200) were never touched.
    from vaulttec.intraday_paper_trading import load_state

    final = load_state(Path(result["scratch_dir"]))
    assert final["last_processed_bar"]["TEST"] == "2026-11-11T10:30:00"
    assert final["last_processed_bar"]["HIGH"] == "2026-11-11T10:30:00"
    assert final["last_processed_bar"]["CRYP"] == "2026-11-11T11:00:00"
    for trade in final["closed_trades"]:
        assert trade["entry_bar"] <= "2026-11-11T10:30:00"
