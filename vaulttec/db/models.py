"""Data models — plain dataclasses, no ORM in Phase 1."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UserProfile:
    """The user's trading profile. Automation may never exceed these limits."""

    name: str = "Trader"
    goal: str = "Grow steadily"
    risk_tolerance: str = "balanced"  # conservative | balanced | growth
    virtual_capital: float = 10_000.00
    max_position_pct: float = 0.10
    daily_loss_limit_pct: float = 0.02
    allowed_markets: list = field(default_factory=lambda: ["stocks"])
    automation_enabled: bool = False  # OFF by default; user opts in


@dataclass
class PaperTrade:
    symbol: str
    side: str  # buy | sell
    quantity: float
    price: float
    stop_loss: float
    take_profit: float
    reason: str
    source: str = "manual"  # manual | automated
    status: str = "open"  # open | closed | blocked
    pnl: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class Signal:
    symbol: str
    direction: str  # long | short | neutral
    confidence: float  # 0-1, with evidence — never a guarantee
    evidence: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
