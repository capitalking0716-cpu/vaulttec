"""Private-live strategy: wide-6 mean-reversion, sized for small capital.

Same validated rules as the public live-paper run (Phase 4c/4d):
RSI < 30 or price at/below the Bollinger lower band, long-only,
6% stop / 9% target (1.5:1), 10-bar time exit. The signal logic is
reused from ``analytics.mean_reversion.mean_reversion_trigger`` —
there is no second copy of the trigger.

What is different here is the SIZING, because this module is for
$20–$50 of real money, not $10,000 of virtual cash:

- Position size is a DOLLAR amount (notional), because Alpaca
  fractional orders are placed in dollars. The Risk Engine still
  checks the trade in share terms (notional / price = quantity),
  so the same caps apply: max 10% of the account in one position
  (balanced), max 25% in one holding, max 75% invested overall.
- Risk per trade is capped at 2% of the account: the dollars at
  risk if the 6% stop fires. On $50 that is $1.00 of risk, which
  at a 6% stop means a $16.67 position — bigger than the 10%
  position cap ($5.00), so the position cap wins and the real
  risk per trade on $50 is $0.30 (6% of $5.00). The honest maths
  is in README.md: $20–$50 will not fund an attorney quickly.
  It is a test amount, and it must be treated as one.
- A trade is skipped when the dollar position would be below
  Alpaca's minimum notional (about $1 — verify the current
  figure in Alpaca's docs at the time; the runner uses
  ``MIN_NOTIONAL_USD = 1.00`` and logs the skip).

Every proposal carries its full evidence (strategy, confidence
is NOT invented — the trigger is binary, so the proposal says
exactly that), the entry price, the stop, the target, the dollars
at risk, and the dollars the trade targets. A proposal is not an
order: in approval mode (the default) nothing is placed until
Neko approves it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from ..analytics.mean_reversion import STRATEGIES, mean_reversion_trigger, strategy_label
from ..risk import RiskEngine
from . import HORIZON_BARS, RISK_REWARD, STOP_PCT, TAKE_PCT
from .config import MAX_POSITION_PCT, MAX_RISK_PER_TRADE_PCT

MIN_NOTIONAL_USD = 1.00  # Alpaca fractional minimum, approx. — verify in docs


@dataclass
class Proposal:
    proposal_id: str
    symbol: str
    strategy: str
    entry_price: float
    stop_loss: float
    take_profit: float
    notional_usd: float
    quantity: float
    risk_usd: float  # dollars lost if the stop fires
    target_usd: float  # dollars gained if the target fills
    risk_reward: float = RISK_REWARD
    status: str = "pending"  # pending | approved | rejected | placed | blocked | skipped
    reason: str = ""


def wide6_stop_target(entry_price: float) -> tuple[float, float]:
    """6% stop, 9% target — target derived from the rounded stop
    and rounded UP to the cent, so it always meets the 1.5:1
    minimum (same construction as the Challenge Trial)."""
    stop = round(entry_price * (1 - STOP_PCT), 2)
    take = math.ceil((entry_price + RISK_REWARD * (entry_price - stop)) * 100) / 100
    return stop, take


def size_position(account_value_usd: float, entry_price: float,
                  risk_engine: RiskEngine | None = None) -> dict:
    """Dollar position for one trade on a small account.

    Returns ``{"notional_usd", "quantity", "risk_usd", "target_usd",
    "capped_by"}``. The position cap (10% of account) and the
    risk cap (2% of account at the 6% stop) are both computed and
    the smaller one wins. On $20–$50 the position cap always wins,
    so ``capped_by`` is ``"position cap (10% of account)"`` — the
    risk cap only binds on larger accounts.
    """
    if account_value_usd <= 0 or entry_price <= 0:
        return {"notional_usd": 0.0, "quantity": 0.0, "risk_usd": 0.0,
                "target_usd": 0.0, "capped_by": "no capital / no price"}
    by_position = account_value_usd * MAX_POSITION_PCT
    by_risk = (account_value_usd * MAX_RISK_PER_TRADE_PCT) / STOP_PCT
    if by_position <= by_risk:
        notional = by_position
        capped_by = "position cap (10% of account)"
    else:
        notional = by_risk
        capped_by = "risk cap (2% of account)"
    notional = round(notional, 2)
    quantity = notional / entry_price
    return {
        "notional_usd": notional,
        "quantity": quantity,
        "risk_usd": round(notional * STOP_PCT, 2),
        "target_usd": round(notional * TAKE_PCT, 2),
        "capped_by": capped_by,
    }


def build_proposal(symbol: str, strategy: str, entry_price: float,
                   account_value_usd: float, proposal_id: str,
                   risk_engine: RiskEngine | None = None) -> Proposal | None:
    """Build a proposal for a triggered symbol, or None when the
    trade cannot be sized (too little capital for the $1 minimum).
    The Risk Engine check happens in the runner, against the live
    account value — this function only sizes and prices the trade.
    """
    sizing = size_position(account_value_usd, entry_price, risk_engine)
    if sizing["notional_usd"] < MIN_NOTIONAL_USD:
        return None
    stop, take = wide6_stop_target(entry_price)
    # Floor (never round up) the quantity: rounding up can push the
    # cost a fraction of a cent over the Risk Engine's 10% position
    # cap and get the trade blocked for $0.00 of real difference.
    quantity = math.floor(sizing["quantity"] * 1_000_000_000) / 1_000_000_000
    return Proposal(
        proposal_id=proposal_id,
        symbol=symbol,
        strategy=strategy,
        entry_price=round(entry_price, 2),
        stop_loss=stop,
        take_profit=take,
        notional_usd=sizing["notional_usd"],
        quantity=quantity,
        risk_usd=sizing["risk_usd"],
        target_usd=sizing["target_usd"],
        reason=(f"{strategy_label(strategy)} trigger on the last completed "
                f"bar. Wide-6: 6% stop / 9% target. Sized by "
                f"{sizing['capped_by']}. This is a binary trigger, not a "
                f"confidence score — no win probability is claimed."),
    )


def check_proposal_with_risk(proposal: Proposal, risk_engine: RiskEngine,
                             portfolio_value_usd: float,
                             current_exposure_usd: float,
                             holding_value_usd: float = 0.0,
                             daily_pnl_pct: float = 0.0) -> tuple[bool, list[str]]:
    """Run a proposal through the shared Risk Engine. Returns
    (allowed, reasons). A blocked proposal is logged, never placed
    and never silently shrunk to fit."""
    check = risk_engine.check_order(
        symbol=proposal.symbol, price=proposal.entry_price,
        quantity=proposal.quantity, stop_loss=proposal.stop_loss,
        take_profit=proposal.take_profit,
        portfolio_value=portfolio_value_usd,
        current_exposure=current_exposure_usd,
        holding_value=holding_value_usd,
        daily_pnl_pct=daily_pnl_pct, side="buy",
    )
    return check.allowed, list(check.reasons)


def scan_history(history: pd.DataFrame) -> str | None:
    """First firing strategy on the last bar of ``history``, or None.
    RSI is checked first (same order as the live-paper runner). A
    Bollinger trigger on a flat line (zero-width band) is not a
    bounce — same guard as the live-paper runner."""
    from ..market.indicators import bollinger_bands

    for strategy in STRATEGIES:
        if strategy == "bollinger":
            closes = history["close"].reset_index(drop=True)
            bands = bollinger_bands(closes)
            bandwidth = bands["bandwidth"].iloc[-1]
            if pd.isna(bandwidth) or float(bandwidth) <= 0:
                continue
        if mean_reversion_trigger(strategy, history):
            return strategy
    return None
