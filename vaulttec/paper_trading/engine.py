"""Paper trading engine — simulated fills against virtual cash.

No broker is contacted. No real money moves. Every order is first
checked by the Risk Engine; a blocked order is recorded, not executed.

Phase 3 wiring (previously the risk checks for concentration and the
daily loss limit could never fire, because ``place_order`` never
passed a holding value or a daily P&L to the Risk Engine):
- the current holding value for the symbol is passed, so the
  concentration limit is enforced for real;
- realised P&L from closed paper trades is tracked, so the daily
  loss limit pauses trading for the day once it is hit;
- a buy that the virtual cash cannot cover is blocked (with a reason)
  instead of raising an error;
- ``close_position`` sells a holding, realises its P&L, and marks the
  matching open paper trade closed — this is what the Phase 3
  validation run uses to exit trades at their stop, target, or
  time-based close.
"""
from __future__ import annotations

from ..db.models import PaperTrade
from ..portfolio.manager import Portfolio
from ..risk.engine import RiskEngine


class PaperTradingEngine:
    def __init__(self, portfolio: Portfolio, risk: RiskEngine):
        self.portfolio = portfolio
        self.risk = risk
        self.trades: list[PaperTrade] = []
        self.blocked: list[dict] = []
        # Starting value anchors the daily-loss percentage. Realised P&L
        # is tracked per session (one "day" in the app's paper-trading
        # view); a fresh engine starts a fresh day at zero.
        self.starting_value = portfolio.value({})
        self.realised_pnl = 0.0

    @property
    def daily_pnl_pct(self) -> float:
        """Realised paper P&L so far, as a share of starting value."""
        if self.starting_value <= 0:
            return 0.0
        return self.realised_pnl / self.starting_value

    def _holding_value(self, symbol: str, price: float) -> float:
        holding = self.portfolio.holdings.get(symbol)
        return holding.quantity * price if holding else 0.0

    def place_order(self, symbol: str, side: str, quantity: float, price: float,
                    stop_loss: float | None, take_profit: float | None,
                    reason: str, source: str = "manual") -> PaperTrade | None:
        prices = {symbol: price}
        portfolio_value = self.portfolio.value(prices)
        check = self.risk.check_order(
            symbol=symbol, price=price, quantity=quantity,
            stop_loss=stop_loss, take_profit=take_profit,
            portfolio_value=portfolio_value,
            current_exposure=self.portfolio.exposure(prices),
            holding_value=self._holding_value(symbol, price),
            daily_pnl_pct=self.daily_pnl_pct,
            side=side,
        )
        if not check.allowed:
            self.blocked.append({"symbol": symbol, "reasons": check.reasons, "source": source})
            return None
        if side == "buy":
            cost = quantity * price
            if cost > self.portfolio.cash:
                self.blocked.append({
                    "symbol": symbol,
                    "reasons": [f"Not enough virtual cash for this paper trade (${cost:,.2f} needed)."],
                    "source": source})
                return None
            self.portfolio.buy(symbol, quantity, price)
        elif side == "sell":
            holding = self.portfolio.holdings.get(symbol)
            if holding is None or holding.quantity < quantity:
                self.blocked.append({
                    "symbol": symbol,
                    "reasons": ["Not enough shares to sell."],
                    "source": source})
                return None
            pnl = self.portfolio.sell(symbol, quantity, price)
            self.realised_pnl += pnl
        else:
            raise ValueError("side must be 'buy' or 'sell'")
        trade = PaperTrade(symbol=symbol, side=side, quantity=quantity, price=price,
                           stop_loss=stop_loss or 0.0, take_profit=take_profit or 0.0,
                           reason=reason, source=source)
        self.trades.append(trade)
        return trade

    def close_position(self, symbol: str, price: float, exit_reason: str = "exit") -> float | None:
        """Sell the whole holding for a symbol at ``price`` (paper only).

        Realises the P&L, updates the daily-loss tracker, and marks the
        most recent open buy trade for the symbol closed. Returns the
        realised P&L, or None when there is no open position to close.
        """
        holding = self.portfolio.holdings.get(symbol)
        if holding is None or holding.quantity <= 0:
            return None
        pnl = self.portfolio.sell(symbol, holding.quantity, price)
        self.realised_pnl += pnl
        for trade in reversed(self.trades):
            if trade.symbol == symbol and trade.side == "buy" and trade.status == "open":
                trade.status = "closed"
                trade.pnl = round(pnl, 2)
                break
        return pnl

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def open_trade_count(self) -> int:
        return sum(1 for t in self.trades if t.status == "open")
