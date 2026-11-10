"""Small-wins watch tests — Ava flags the wins to bank, the wins
that are slipping away, the positions past their stop, the losers
drifting toward it, and the names carrying too much of the pot.
All from real numbers in the state; no current price, no flag.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ava.small_wins import summarize_watch, watch_positions


def _position(entry: float = 100.0, quantity: float = 10, stop: float = 94.0,
              target: float = 109.0, symbol: str = "AAPL",
              entry_date: str = "2026-11-06") -> dict:
    return {"symbol": symbol, "entry_price": entry, "quantity": quantity,
            "stop_loss": stop, "take_profit": target,
            "entry_date": entry_date, "bars_held": 2}


def test_bank_it_halfway_to_target():
    flags = watch_positions([_position()], {"AAPL": 106.0})
    kinds = [f["kind"] for f in flags]
    assert "bank_it" in kinds
    flag = next(f for f in flags if f["kind"] == "bank_it")
    assert "Bank the small win" in flag["headline"]
    assert "$60.00" in flag["detail"]


def test_bank_it_at_target():
    flags = watch_positions([_position()], {"AAPL": 110.0})
    flag = next(f for f in flags if f["kind"] == "bank_it")
    assert "Target hit" in flag["headline"]


def test_cut_it_past_the_stop():
    flags = watch_positions([_position()], {"AAPL": 93.0})
    assert [f["kind"] for f in flags] == ["cut_it"]
    assert "past your stop" in flags[0]["headline"]


def test_drifting_toward_the_stop():
    flags = watch_positions([_position()], {"AAPL": 96.5})
    assert [f["kind"] for f in flags] == ["drifting"]
    assert "drifting toward the stop" in flags[0]["headline"]


def test_slipping_win_is_flagged():
    history = pd.DataFrame({
        "date": pd.date_range("2026-11-06", periods=6),
        "close": [100.0, 102.0, 104.0, 106.0, 105.0, 103.0]})
    flags = watch_positions([_position()], {"AAPL": 103.0},
                            history_by_symbol={"AAPL": history})
    kinds = [f["kind"] for f in flags]
    assert "slipping" in kinds
    flag = next(f for f in flags if f["kind"] == "slipping")
    assert "slipping away" in flag["headline"]
    assert "$60.00" in flag["detail"]  # was up $60, now up $30


def test_small_win_holding_steady_is_not_slipping():
    history = pd.DataFrame({
        "date": pd.date_range("2026-11-06", periods=4),
        "close": [100.0, 103.0, 105.0, 105.5]})
    flags = watch_positions([_position()], {"AAPL": 105.5},
                            history_by_symbol={"AAPL": history})
    kinds = [f["kind"] for f in flags]
    assert "slipping" not in kinds
    assert "bank_it" in kinds


def test_over_concentration_is_flagged():
    position = _position(entry=100.0, quantity=10)
    flags = watch_positions([position], {"AAPL": 101.0},
                            portfolio_value=3000.0)
    kinds = [f["kind"] for f in flags]
    assert "concentrated" in kinds
    flag = next(f for f in flags if f["kind"] == "concentrated")
    assert "34%" in flag["headline"] or "33%" in flag["headline"]


def test_no_current_price_means_no_flag():
    assert watch_positions([_position()], {}) == []
    assert watch_positions([_position()], {"MSFT": 200.0}) == []


def test_summarize_watch():
    flags = watch_positions([_position()], {"AAPL": 106.0})
    text = summarize_watch(flags)
    assert "Bank the small wins" in text
    assert "AAPL" in text
    assert summarize_watch([]) == (
        "Small wins watch: nothing to bank or cut right now — no small "
        "win is slipping, nothing is past its stop, and no name is "
        "carrying too much of the pot.")
