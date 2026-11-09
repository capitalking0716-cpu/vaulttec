"""The VaultTec Coach — coaching-to-automation, Stage 1.

The Coach walks the user through their first few trades in plain
language until they get the hang of trading. It never places a trade
itself; the user approves every coached trade. Graduation is an explicit
opt-in after the checklist and a review — never automatic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COACHING_CHECKLIST = [
    {"id": "profile", "label": "Set your profile — goals, capital, risk tolerance"},
    {"id": "risk_basics", "label": "Learn the basics — stop-loss, position size, risk/reward"},
    {"id": "trade_1", "label": "Coached paper trade 1 — with a full walkthrough"},
    {"id": "trade_2", "label": "Coached paper trade 2 — you explain the 'why' back"},
    {"id": "trade_3", "label": "Coached paper trade 3 — you set the stop-loss yourself"},
    {"id": "trade_4", "label": "Coached paper trade 4 — you size the position yourself"},
    {"id": "trade_5", "label": "Coached paper trade 5 — full trade, Coach only reviews"},
    {"id": "review", "label": "Graduation review — what you got right, what to watch"},
]

GRADUATION_QUESTIONS = [
    "What is a stop-loss, and why does every trade need one?",
    "If a trade risks $10, how much should it stand to make (at 1.5:1)?",
    "What happens when your daily loss limit is hit?",
    "How do you stop automation instantly?",
]


def walkthrough(symbol: str, direction: str, price: float, stop_loss: float,
                take_profit: float, quantity: float, evidence: str) -> str:
    """Plain-language walkthrough for one coached trade."""
    risk = abs(price - stop_loss) * quantity
    reward = abs(take_profit - price) * quantity
    return (
        f"Let's walk through this {direction} trade on {symbol}, step by step.\n\n"
        f"1. THE IDEA — {evidence}\n"
        f"2. THE PRICE — entry ${price:,.2f} for {quantity} shares.\n"
        f"3. THE RISK — if it goes wrong, your stop-loss at ${stop_loss:,.2f} "
        f"limits the loss to about ${risk:,.2f}. That is the most this trade should cost you.\n"
        f"4. THE REWARD — your take-profit at ${take_profit:,.2f} targets about "
        f"${reward:,.2f} if it goes right.\n"
        f"5. THE RULES — this is paper trading, virtual money only. "
        f"If the stop-loss is hit, the trade closes. No chasing, no doubling down.\n\n"
        f"Do you understand why this trade, and what could go wrong? "
        f"Approve it only if the answer is yes."
    )


@dataclass
class Coach:
    completed: set = field(default_factory=set)
    coached_trades_done: int = 0
    graduated: bool = False

    def complete(self, item_id: str) -> None:
        self.completed.add(item_id)

    def record_coached_trade(self) -> None:
        self.coached_trades_done += 1
        trade_no = min(self.coached_trades_done, 5)
        self.complete(f"trade_{trade_no}")

    @property
    def progress_pct(self) -> int:
        return round(len(self.completed) / len(COACHING_CHECKLIST) * 100)

    @property
    def next_step(self) -> str:
        for item in COACHING_CHECKLIST:
            if item["id"] not in self.completed:
                return item["label"]
        return "All coaching steps complete — take the graduation review."

    def can_graduate(self) -> bool:
        """Graduation needs 5 coached trades + the full checklist."""
        return self.coached_trades_done >= 5 and len(self.completed) >= len(COACHING_CHECKLIST)

    def graduate(self, user_confirmed: bool) -> bool:
        """Graduation only happens when the user explicitly confirms."""
        if self.can_graduate() and user_confirmed:
            self.graduated = True
            return True
        return False
