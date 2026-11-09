"""Risk Engine unit tests — run with: pytest tests/"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.risk import RiskEngine


def test_no_stop_loss_blocks_trade():
    engine = RiskEngine()
    check = engine.check_order(symbol="AAPL", price=100, quantity=1, stop_loss=None,
                               take_profit=110, portfolio_value=10_000,
                               current_exposure=0)
    assert not check.allowed
    assert any("stop-loss" in r for r in check.reasons)


def test_leverage_and_options_rejected():
    engine = RiskEngine()
    for kwargs in ({"leveraged": True}, {"is_option": True}):
        check = engine.check_order(symbol="AAPL", price=100, quantity=1, stop_loss=97,
                                   take_profit=105, portfolio_value=10_000,
                                   current_exposure=0, **kwargs)
        assert not check.allowed


def test_oversized_position_blocked():
    engine = RiskEngine(max_position_pct=0.10)
    check = engine.check_order(symbol="AAPL", price=100, quantity=50, stop_loss=97,
                               take_profit=105, portfolio_value=10_000,
                               current_exposure=0)
    assert not check.allowed


def test_good_trade_allowed():
    engine = RiskEngine()
    check = engine.check_order(symbol="AAPL", price=100, quantity=5, stop_loss=97,
                               take_profit=105, portfolio_value=10_000,
                               current_exposure=0)
    assert check.allowed, check.reasons


def test_daily_loss_limit_pauses_trading():
    engine = RiskEngine(daily_loss_limit_pct=0.02)
    check = engine.check_order(symbol="AAPL", price=100, quantity=5, stop_loss=97,
                               take_profit=105, portfolio_value=10_000,
                               current_exposure=0, daily_pnl_pct=-0.03)
    assert not check.allowed
