"""Phase 3 risk-engine validation — every rule in the brief, tested
directly, including the two wiring gaps Phase 3 closed (concentration
and daily-loss limits could never fire before, because the paper
engine never passed a holding value or a daily P&L to the engine)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.paper_trading import PaperTradingEngine
from vaulttec.portfolio import Portfolio
from vaulttec.risk import RiskEngine


def _engine(**kw):
    return RiskEngine(**kw)


def test_stop_loss_direction_is_side_aware():
    e = _engine()
    # Buy: stop must be below entry.
    assert not e.check_order(symbol="A", price=100, quantity=1, stop_loss=101,
                             take_profit=110, portfolio_value=10_000,
                             current_exposure=0, side="buy").allowed
    # Sell: stop must be above entry.
    assert not e.check_order(symbol="A", price=100, quantity=1, stop_loss=99,
                             take_profit=90, portfolio_value=10_000,
                             current_exposure=0, side="sell").allowed
    ok = e.check_order(symbol="A", price=100, quantity=1, stop_loss=103,
                       take_profit=95, portfolio_value=10_000,
                       current_exposure=0, side="sell")
    assert ok.allowed, ok.reasons


def test_take_profit_must_be_on_the_right_side():
    e = _engine()
    bad = e.check_order(symbol="A", price=100, quantity=1, stop_loss=97,
                        take_profit=99, portfolio_value=10_000,
                        current_exposure=0, side="buy")
    assert not bad.allowed
    assert any("Take-profit" in r for r in bad.reasons)


def test_exactly_minimum_risk_reward_passes():
    e = _engine(min_risk_reward=1.5)
    # 3% risk, 4.5% reward = exactly 1.5:1 — must pass, not be blocked
    # by floating-point rounding of the prices.
    ok = e.check_order(symbol="A", price=100, quantity=5, stop_loss=97,
                       take_profit=104.5, portfolio_value=10_000,
                       current_exposure=0)
    assert ok.allowed, ok.reasons
    just_under = e.check_order(symbol="A", price=100, quantity=5, stop_loss=97,
                               take_profit=104.4, portfolio_value=10_000,
                               current_exposure=0)
    assert not just_under.allowed


def test_position_cap_boundary():
    e = _engine(max_position_pct=0.10)
    at_cap = e.check_order(symbol="A", price=100, quantity=10, stop_loss=97,
                           take_profit=105, portfolio_value=10_000,
                           current_exposure=0)
    assert at_cap.allowed, at_cap.reasons
    over_cap = e.check_order(symbol="A", price=100, quantity=10.1, stop_loss=97,
                             take_profit=105, portfolio_value=10_000,
                             current_exposure=0)
    assert not over_cap.allowed


def test_concentration_limit_enforced():
    e = _engine(max_concentration_pct=0.25)
    # Holding $1,500 + new $1,000 = $2,500 = exactly 25% of $10,000: allowed.
    at_cap = e.check_order(symbol="A", price=100, quantity=10, stop_loss=97,
                           take_profit=105, portfolio_value=10_000,
                           current_exposure=0, holding_value=1500)
    assert at_cap.allowed, at_cap.reasons
    # Holding $2,000 + $1,000 = $3,000 > 25%: blocked.
    over = e.check_order(symbol="A", price=100, quantity=10, stop_loss=97,
                         take_profit=105, portfolio_value=10_000,
                         current_exposure=0, holding_value=2000)
    assert not over.allowed
    assert any("concentration" in r for r in over.reasons)


def test_exposure_limit_enforced():
    e = _engine(max_exposure_pct=0.75)
    over = e.check_order(symbol="A", price=100, quantity=10, stop_loss=97,
                         take_profit=105, portfolio_value=10_000,
                         current_exposure=7000)
    assert not over.allowed
    assert any("exposure" in r for r in over.reasons)


def test_suggested_stop_and_target_always_meet_minimum():
    e = _engine(min_risk_reward=1.5)
    for price in (100.0, 167.05, 131.20, 97450.0, 23.47):
        check = e.check_order(symbol="A", price=price, quantity=1,
                              stop_loss=price * 0.97, take_profit=price * 1.045,
                              portfolio_value=10_000_000, current_exposure=0)
        ratio = (check.suggested_take_profit - price) / (price - check.suggested_stop_loss)
        assert ratio >= 1.5, (price, ratio, check.suggested_stop_loss, check.suggested_take_profit)


def test_daily_loss_limit_blocks_via_paper_engine():
    risk = RiskEngine(max_position_pct=1.0, max_concentration_pct=1.0,
                      max_exposure_pct=1.0, daily_loss_limit_pct=0.02)
    engine = PaperTradingEngine(Portfolio(cash=10_000), risk)
    trade = engine.place_order("AAPL", "buy", 50, 100, 97, 105,
                               reason="test", source="manual")
    assert trade is not None
    pnl = engine.close_position("AAPL", 95)  # -$250 = -2.5% of $10,000
    assert pnl == -250
    assert engine.daily_pnl_pct == -0.025
    blocked = engine.place_order("MSFT", "buy", 1, 100, 97, 105,
                                 reason="test", source="manual")
    assert blocked is None
    assert any("Daily loss limit" in r for r in engine.blocked[-1]["reasons"])


def test_close_position_marks_trade_closed_and_realises_pnl():
    engine = PaperTradingEngine(Portfolio(cash=10_000), RiskEngine())
    engine.place_order("AAPL", "buy", 5, 100, 97, 105, reason="test")
    assert engine.open_trade_count == 1
    pnl = engine.close_position("AAPL", 110)
    assert pnl == 50
    assert engine.open_trade_count == 0
    assert engine.trades[0].status == "closed"
    assert engine.trades[0].pnl == 50
    assert engine.close_position("AAPL", 110) is None  # nothing left to close


def test_buy_without_enough_cash_is_blocked_not_an_error():
    # $100 cash but $9,000 already invested (portfolio value $9,100):
    # a $500 buy passes the risk caps, but the virtual cash cannot
    # cover it — it must be blocked with a reason, not raise an error.
    from vaulttec.portfolio.manager import Holding

    portfolio = Portfolio(cash=100, holdings={"MSFT": Holding("MSFT", 100, 90)})
    wide = PaperTradingEngine(portfolio, RiskEngine(
        max_position_pct=1.0, max_concentration_pct=2.0, max_exposure_pct=2.0))
    assert wide.place_order("AAPL", "buy", 5, 100, 97, 105, reason="test") is None
    assert any("cash" in r for r in wide.blocked[-1]["reasons"])
