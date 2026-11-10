"""Ava's context snapshot — the shape her brief, chat and trade check read.

The builder moved here from the deleted Shadow bridge module; the
shape is unchanged, so Ava's brief, ask and check_move keep working.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ava.context import build_context_snapshot
from vaulttec.db.models import PaperTrade, Signal


def _profile():
    return SimpleNamespace(
        name="Neko", goal="Build wealth", risk_tolerance="balanced",
        virtual_capital=100000.0, max_position_pct=10.0,
        daily_loss_limit_pct=2.0, allowed_markets=["stocks"],
        automation_enabled=False,
    )


def _portfolio():
    return SimpleNamespace(
        cash=7000.0,
        holdings={"GOOGL": SimpleNamespace(symbol="GOOGL", quantity=10, avg_cost=280.0)},
    )


def _engine():
    open_trade = PaperTrade(symbol="GOOGL", side="buy", quantity=10, price=284.78,
                            stop_loss=267.69, take_profit=310.0, reason="wide-6")
    closed_trade = PaperTrade(symbol="META", side="buy", quantity=5, price=600.0,
                              stop_loss=564.0, take_profit=654.0, reason="wide-6",
                              status="closed")
    return SimpleNamespace(trades=[open_trade, closed_trade])


def test_snapshot_shape_matches_what_ava_reads():
    ctx = build_context_snapshot(
        _profile(), _portfolio(), _engine(),
        [Signal(symbol="NVDA", direction="long", confidence=0.7, evidence="RSI 28")],
        {"GOOGL": 290.0}, 7000.0, 10000.0, 0.0,
    )
    assert ctx["user"]["name"] == "Neko"
    assert ctx["user"]["risk_tolerance"] == "balanced"
    assert ctx["portfolio"] == {"cash": 7000.0, "value": 10000.0, "pnl": 0.0}
    assert ctx["holdings"] == [
        {"symbol": "GOOGL", "quantity": 10.0, "avg_cost": 280.0, "current_price": 290.0}
    ]
    assert len(ctx["open_trades"]) == 1  # closed trade stays out
    trade = ctx["open_trades"][0]
    assert trade["symbol"] == "GOOGL"
    assert trade["price"] == 284.78
    assert trade["stop_loss"] == 267.69
    assert trade["take_profit"] == 310.0
    assert ctx["signals"] == [
        {"symbol": "NVDA", "direction": "long", "confidence": 0.7, "evidence": "RSI 28"}
    ]
    assert ctx["generated_at"]


def test_snapshot_never_crashes_on_odd_input():
    ctx = build_context_snapshot(None, None, None, None, None, 0, 0, 0)
    assert ctx["user"]["name"] == ""
    assert ctx["portfolio"] == {"cash": 0.0, "value": 0.0, "pnl": 0.0}
    assert ctx["holdings"] == []
    assert ctx["open_trades"] == []
    assert ctx["signals"] == []
