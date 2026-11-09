"""The VaultTec Challenge Trial — trading platform, not a school.

Approved by Neko 2026-11-09, revised 2026-11-09: Academy / course
is REMOVED. There is no course and no course gate — VaultTec is a
trading platform, not a school.

- The user puts in $20. That $20 is the user's OWN starting money /
  trading capital — it is NOT a fee to VaultTec. VaultTec takes
  nothing from it and does not get paid from it.
- The user completes 30 paper trades in 1 month (win or lose —
  finishing is the pass, not being profitable). Pass = 30 trades only.
- Human-in-the-loop: the AI proposes a trade, the user decides YES
  or NO on each one. AI can't win every time; the better the user
  understands the data, the better their chances.
- After passing, the user trades live with that $20 — but live
  trading is NOT built here. It needs a compliance/legal check first.
  After the challenge the user joins the membership separately and
  pays for it themselves ($29 / $59 / $99); the subscription is NOT
  taken automatically from profits. No payment code, no Stripe, no
  broker, no live trading in this module. Paper trading only.

This module has no Streamlit and no network in it — only ``app.py``
touches the UI. All logic is pure and unit-testable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

# --- The Challenge Trial rules (approved 2026-11-09) ----------------------
CHALLENGE_REQUIRED_TRADES = 30
CHALLENGE_STARTING_CAPITAL = 20.0
CHALLENGE_STARTING_CAPITAL_LABEL = (
    "Your $20 — your starting capital. VaultTec takes nothing from it."
)
# Wide-6 risk rules, exactly as validated in Phase 4c/4d: 6% stop,
# 9% target, 1.5:1 risk/reward. Every challenge trade keeps a stop-loss.
CHALLENGE_STOP_PCT = 0.06
CHALLENGE_TARGET_PCT = 0.09
CHALLENGE_MIN_RISK_REWARD = 1.5

# Membership prices from vaulttec-pricing-research.md (approved
# 2026-11-09). Data only — no billing, no paywall, no payment code.
# After the challenge the user joins the membership separately and
# pays for it themselves; it is NOT taken automatically from profits,
# and never from the $20 starting capital.
CHALLENGE_SUBSCRIPTIONS = {
    "starter": {"label": "Vault Starter", "monthly_usd": 29, "annual_monthly_usd": 24},
    "pro": {"label": "Vault Pro", "monthly_usd": 59, "annual_monthly_usd": 49},
    "elite": {"label": "Vault Elite", "monthly_usd": 99, "annual_monthly_usd": 79},
}

LIVE_NOT_AVAILABLE = (
    "Live trading is NOT yet available. It needs a compliance/legal "
    "check first. No payment has been taken, and no live trade has "
    "been placed."
)

NO_REASONS = [
    "I don't agree with the AI's reasoning",
    "Too risky for me",
    "Waiting for a better price",
    "I don't understand it yet",
    "Other",
]

def wide6_stop_target(price: float) -> tuple[float, float]:
    """Wide-6 stop/target for an entry price: 6% stop, 9% target.

    The target is derived from the rounded stop and rounded UP to the
    cent, so the suggestion always meets the 1.5:1 minimum (the same
    pattern the Risk Engine uses for its own suggestions).
    """
    if price <= 0:
        raise ValueError("Price must be positive.")
    stop = round(price * (1 - CHALLENGE_STOP_PCT), 2)
    target = math.ceil((price + CHALLENGE_MIN_RISK_REWARD * (price - stop)) * 100) / 100
    return stop, target


def build_proposal(symbol: str, direction: str, confidence: float, evidence: str,
                   price: float, quantity: float = 1.0) -> dict:
    """Build the YES/NO proposal card for one AI signal.

    Returns everything the user needs to decide: the evidence in plain
    language, the confidence (never a promise), the wide-6 stop/target,
    and what the trade risks vs what it targets.
    """
    if price <= 0:
        raise ValueError("Price must be positive.")
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("Confidence must be between 0 and 1.")
    stop, target = wide6_stop_target(price)
    risk = round(abs(price - stop) * quantity, 2)
    reward = round(abs(target - price) * quantity, 2)
    return {
        "symbol": symbol,
        "direction": direction,
        "confidence": confidence,
        "evidence": evidence,
        "price": price,
        "quantity": quantity,
        "stop_loss": stop,
        "take_profit": target,
        "risk_usd": risk,
        "reward_usd": reward,
        "risk_reward": round(reward / risk, 2) if risk > 0 else 0.0,
        "paper_only": True,
    }


def explain_proposal_plain(proposal: dict) -> str:
    """Plain-language explanation of a proposal, for the YES/NO card."""
    return (
        f"{proposal['symbol']}: the AI suggests a {proposal['direction']} trade "
        f"at ${proposal['price']:,.2f}, with {proposal['confidence']:.0%} confidence. "
        f"Why: {proposal['evidence']} "
        f"If it goes wrong, the stop-loss at ${proposal['stop_loss']:,.2f} limits "
        f"the loss to about ${proposal['risk_usd']:,.2f}. If it goes right, the "
        f"take-profit at ${proposal['take_profit']:,.2f} targets about "
        f"${proposal['reward_usd']:,.2f}. That is {proposal['risk_reward']:.1f}:1 "
        f"risk/reward. Confidence is not a promise — the AI can't win every "
        f"time. This is a PAPER trade with virtual money. Say YES only if "
        f"you understand why, and NO if you don't — a NO is a good decision "
        f"too, and it is logged just like a YES."
    )


@dataclass
class ChallengeDecision:
    symbol: str
    direction: str
    confidence: float
    evidence: str
    price: float
    stop_loss: float
    take_profit: float
    quantity: float
    decision: str  # "yes" | "no"
    reason: str
    outcome: str = "pending"  # pending | win | loss (set when the trade resolves)
    pnl: float = 0.0
    date: str = field(default_factory=lambda: date.today().isoformat())


@dataclass
class ChallengeTrade:
    symbol: str
    date: str
    decision: str = "yes"  # challenge trades are only ever placed by a YES
    outcome: str = "open"  # open | win | loss
    pnl: float = 0.0
    price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    quantity: float = 0.0
    decision_index: int | None = None


@dataclass
class ChallengeTrial:
    """One user's Challenge Trial state. Session state in the app.

    ``starting_capital`` is the user's own $20 — VaultTec takes
    nothing from it (``vaulttec_takes_from_starting_capital_usd`` is
    always 0.0; there is no payment logic anywhere in this module).
    """
    starting_capital: float = CHALLENGE_STARTING_CAPITAL
    decisions: list = field(default_factory=list)
    trades: list = field(default_factory=list)

    @property
    def vaulttec_takes_from_starting_capital_usd(self) -> float:
        return 0.0

    def record_decision(self, symbol: str, direction: str, confidence: float,
                        evidence: str, price: float, stop_loss: float,
                        take_profit: float, quantity: float, decision: str,
                        reason: str = "") -> ChallengeDecision:
        """Log a YES/NO decision on an AI proposal. A NO places no trade."""
        if decision not in ("yes", "no"):
            raise ValueError("decision must be 'yes' or 'no'")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0 and 1.")
        if price <= 0:
            raise ValueError("Price must be positive.")
        record = ChallengeDecision(
            symbol=symbol, direction=direction, confidence=confidence,
            evidence=evidence, price=price, stop_loss=stop_loss,
            take_profit=take_profit, quantity=quantity, decision=decision,
            reason=reason or ("No reason given" if decision == "no" else "Agreed with the AI's reasoning"),
        )
        self.decisions.append(record)
        return record

    def record_trade(self, symbol: str, outcome: str = "open", pnl: float = 0.0,
                     price: float = 0.0, stop_loss: float = 0.0,
                     take_profit: float = 0.0, quantity: float = 0.0,
                     date_str: str | None = None,
                     decision: str = "yes", decision_index: int | None = None) -> ChallengeTrade:
        """Count one paper trade toward the 30. Losses count — the pass
        is finishing, not being profitable. ``outcome`` may be "open"
        (just placed), "win", or "loss"."""
        if outcome not in ("open", "win", "loss"):
            raise ValueError("outcome must be 'open', 'win' or 'loss'")
        trade = ChallengeTrade(
            symbol=symbol, date=date_str or date.today().isoformat(),
            decision=decision, outcome=outcome, pnl=pnl, price=price,
            stop_loss=stop_loss, take_profit=take_profit, quantity=quantity,
            decision_index=decision_index,
        )
        self.trades.append(trade)
        return trade

    def close_trade(self, index: int, outcome: str, pnl: float) -> ChallengeTrade:
        """Resolve a trade that was recorded as open."""
        if outcome not in ("win", "loss"):
            raise ValueError("outcome must be 'win' or 'loss' when closing a trade")
        trade = self.trades[index]
        trade.outcome = outcome
        trade.pnl = round(pnl, 2)
        if trade.decision_index is not None:
            decision = self.decisions[trade.decision_index]
            decision.outcome = outcome
            decision.pnl = round(pnl, 2)
        return trade

    # --- Progress ---------------------------------------------------------
    @property
    def trades_done(self) -> int:
        return len(self.trades)

    @property
    def trades_remaining(self) -> int:
        return max(0, CHALLENGE_REQUIRED_TRADES - len(self.trades))

    @property
    def is_complete(self) -> bool:
        """The Challenge is passed when 30 paper trades are done.
        No course — VaultTec is a trading platform, not a school.
        Profitability is never part of the gate — losses count."""
        return self.trades_done >= CHALLENGE_REQUIRED_TRADES

    @property
    def progress_pct(self) -> int:
        """Progress is trades only: trades done / 30."""
        return round(min(self.trades_done, CHALLENGE_REQUIRED_TRADES) / CHALLENGE_REQUIRED_TRADES * 100)

    @property
    def whats_left(self) -> list[str]:
        if self.trades_remaining:
            return [f"{self.trades_remaining} more paper trade(s) to reach 30"]
        return []

    def yes_no_accuracy(self) -> dict:
        """How the user's own YES decisions turned out — resolved
        challenge trades only. Returns None for accuracy until at
        least one trade has resolved, so no number is shown before
        there is anything to measure."""
        resolved = [t for t in self.trades if t.outcome in ("win", "loss")]
        wins = sum(1 for t in resolved if t.outcome == "win")
        losses = len(resolved) - wins
        yes_count = sum(1 for d in self.decisions if d.decision == "yes")
        no_count = sum(1 for d in self.decisions if d.decision == "no")
        return {
            "yes_decisions": yes_count,
            "no_decisions": no_count,
            "resolved_trades": len(resolved),
            "wins": wins,
            "losses": losses,
            "accuracy_pct": round(wins / len(resolved) * 100, 1) if resolved else None,
        }

    def graduation_message(self) -> str:
        if not self.is_complete:
            return "Challenge not complete yet — " + "; ".join(self.whats_left) + "."
        return (
            "Challenge complete — ready for live trading. "
            "You finished 30 paper trades. "
            + LIVE_NOT_AVAILABLE
        )

    def summary(self) -> dict:
        acc = self.yes_no_accuracy()
        return {
            "paper_only": True,
            "starting_capital_usd": self.starting_capital,
            "starting_capital_label": CHALLENGE_STARTING_CAPITAL_LABEL,
            "vaulttec_takes_from_starting_capital_usd": self.vaulttec_takes_from_starting_capital_usd,
            "trades_done": self.trades_done,
            "trades_required": CHALLENGE_REQUIRED_TRADES,
            "trades_remaining": self.trades_remaining,
            "progress_pct": self.progress_pct,
            "is_complete": self.is_complete,
            "yes_decisions": acc["yes_decisions"],
            "no_decisions": acc["no_decisions"],
            "resolved_trades": acc["resolved_trades"],
            "wins": acc["wins"],
            "losses": acc["losses"],
            "accuracy_pct": acc["accuracy_pct"],
            "whats_left": self.whats_left,
            "live_trading_available": False,
            "live_trading_note": LIVE_NOT_AVAILABLE,
        }
