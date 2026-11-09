"""Risk Engine — every order passes through here before it can be placed.

Rules (from the brief + architecture):
- No trade without a stop-loss.
- Position size capped by the user's profile.
- Risk/reward must meet the profile minimum (default 1:1.5).
- Total exposure and single-holding concentration capped.
- Daily loss limit stops trading for the day.
- No leverage, no options — rejected outright.
A failed check BLOCKS the trade and logs the reason. It is never
silently adjusted to fit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class RiskCheck:
    allowed: bool
    reasons: list = field(default_factory=list)
    max_quantity: float = 0.0
    suggested_stop_loss: float = 0.0
    suggested_take_profit: float = 0.0


@dataclass
class RiskEngine:
    max_position_pct: float = 0.10
    max_concentration_pct: float = 0.25
    max_exposure_pct: float = 0.75
    daily_loss_limit_pct: float = 0.02
    min_risk_reward: float = 1.5

    def position_size(self, portfolio_value: float, price: float) -> float:
        """Max shares for one trade, from the profile's position cap."""
        if price <= 0:
            return 0.0
        return (portfolio_value * self.max_position_pct) / price

    def check_order(
        self,
        *,
        symbol: str,
        price: float,
        quantity: float,
        stop_loss: float | None,
        take_profit: float | None,
        portfolio_value: float,
        current_exposure: float,
        holding_value: float = 0.0,
        daily_pnl_pct: float = 0.0,
        leveraged: bool = False,
        is_option: bool = False,
        side: str = "buy",
    ) -> RiskCheck:
        """Validate an order. Phase 3: stop-loss / take-profit direction
        is checked for the trade side — a buy needs its stop below the
        entry price and its target above it; a sell (short exit) needs
        the reverse. ``side`` defaults to "buy" so existing callers
        keep working unchanged."""
        reasons: list[str] = []

        if leveraged:
            reasons.append("Leverage is not allowed.")
        if is_option:
            reasons.append("Options trading is not allowed in the initial strategy.")
        if price <= 0 or quantity <= 0:
            reasons.append("Price and quantity must be positive.")
        if side not in ("buy", "sell"):
            reasons.append("Side must be 'buy' or 'sell'.")
        if stop_loss is None:
            reasons.append("No stop-loss set — every trade needs a stop-loss.")
        elif side == "buy" and stop_loss >= price:
            reasons.append("Stop-loss must be below the entry price for a buy.")
        elif side == "sell" and stop_loss <= price:
            reasons.append("Stop-loss must be above the entry price for a sell.")
        if take_profit is not None:
            if side == "buy" and take_profit <= price:
                reasons.append("Take-profit must be above the entry price for a buy.")
            elif side == "sell" and take_profit >= price:
                reasons.append("Take-profit must be below the entry price for a sell.")
        if take_profit is not None and stop_loss is not None:
            if side == "buy":
                risk, reward = price - stop_loss, take_profit - price
            else:
                risk, reward = stop_loss - price, price - take_profit
            # EPS tolerance: a trade at exactly the minimum (1.50:1) must
            # pass — floating-point rounding of the stop/target prices
            # (e.g. 1.4999999:1) must not block it. The tolerance is
            # 1e-9, far too small to let a genuinely under-minimum
            # trade through.
            if risk > 0 and reward / risk < self.min_risk_reward - 1e-9:
                reasons.append(
                    f"Risk/reward is {reward / risk:.2f}:1, below the minimum "
                    f"{self.min_risk_reward}:1."
                )
            elif risk <= 0:
                reasons.append("Stop-loss gives no room for risk — it is on the wrong side of the entry price.")
        cost = price * quantity
        # Same EPS tolerance on the money caps: a position sized to
        # exactly the cap must not be blocked because rounding the
        # quantity to 4 decimals pushed its cost a few cents over.
        if cost > portfolio_value * self.max_position_pct * (1 + 1e-9):
            reasons.append(
                f"Position ${cost:,.2f} exceeds the max position size "
                f"({self.max_position_pct:.0%} of portfolio)."
            )
        if current_exposure + cost > portfolio_value * self.max_exposure_pct * (1 + 1e-9):
            reasons.append("Trade would exceed maximum total exposure.")
        if holding_value + cost > portfolio_value * self.max_concentration_pct * (1 + 1e-9):
            reasons.append("Trade would exceed the single-holding concentration limit.")
        if daily_pnl_pct <= -self.daily_loss_limit_pct:
            reasons.append("Daily loss limit reached — trading is paused for today.")

        max_qty = self.position_size(portfolio_value, price)
        # Suggested stop/target are built the same way the validation
        # run builds them: the target is derived from the rounded stop
        # and rounded UP to the cent, so the suggestion is always at
        # least the 1.5:1 minimum and never gets blocked by its own
        # cent-rounding.
        sl = round(price * 0.97, 2) if price > 0 else 0.0
        tp = math.ceil((price + self.min_risk_reward * (price - sl)) * 100) / 100 if price > 0 else 0.0
        return RiskCheck(allowed=not reasons, reasons=reasons, max_quantity=max_qty,
                         suggested_stop_loss=sl, suggested_take_profit=tp)


def check_order(engine: RiskEngine, **kwargs) -> RiskCheck:
    return engine.check_order(**kwargs)
