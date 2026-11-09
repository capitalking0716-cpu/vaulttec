"""VaultTec settings — single source of truth for limits and tiers.

Safety note: these defaults are deliberately conservative. The Risk Engine
enforces them; the UI never overrides them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "vaulttec.db"

# Paper-trading starting capital (virtual money only).
# Real-money guidance from the brief: start small, $25-$50, then $50-$100.
PAPER_STARTING_CASH = 10_000.00
MIN_PAPER_TRADES_BEFORE_LIVE_CONSIDERATION = 30
TARGET_PAPER_TRADES_BEFORE_LIVE_CONSIDERATION = 50
COACHED_TRADES_BEFORE_GRADUATION = 5

# Risk profiles: max position size, max concentration, daily loss limit.
RISK_PROFILES = {
    "conservative": {
        "label": "Conservative",
        "max_position_pct": 0.05,
        "max_concentration_pct": 0.15,
        "max_exposure_pct": 0.50,
        "daily_loss_limit_pct": 0.01,
        "min_risk_reward": 1.5,
    },
    "balanced": {
        "label": "Balanced",
        "max_position_pct": 0.10,
        "max_concentration_pct": 0.25,
        "max_exposure_pct": 0.75,
        "daily_loss_limit_pct": 0.02,
        "min_risk_reward": 1.5,
    },
    "growth": {
        "label": "Growth",
        "max_position_pct": 0.15,
        "max_concentration_pct": 0.35,
        "max_exposure_pct": 0.90,
        "daily_loss_limit_pct": 0.03,
        "min_risk_reward": 1.5,
    },
}

# Membership tiers (structure only in Phase 1 — no billing, no paywall).
# Pricing and limits need research and finalising before launch.
MEMBERSHIP_TIERS = {
    "free": {"label": "Free", "signals_per_day": 3, "watchlist_max": 5, "automation": False},
    "standard": {"label": "Standard", "signals_per_day": 10, "watchlist_max": 20, "automation": False},
    "premium": {"label": "Premium", "signals_per_day": 50, "watchlist_max": 100, "automation": False},
    "elite": {"label": "Elite", "signals_per_day": 999, "watchlist_max": 999, "automation": True},
}

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "NVDA", "SPY", "BTC-USD"]


@dataclass
class Settings:
    """Runtime settings. Values come from the environment / .env where set."""

    app_name: str = "VaultTec"
    environment: str = os.getenv("VAULTTEC_ENV", "development")
    # Phase 1 is paper trading ONLY. This flag must never be flipped
    # without the Phase 4 brokerage integration, safeguards, and legal review.
    live_trading_enabled: bool = False
    paper_trading_only: bool = True
    db_path: Path = DB_PATH
    paper_starting_cash: float = PAPER_STARTING_CASH
    data_provider: str = os.getenv("VAULTTEC_DATA_PROVIDER", "sample")  # sample | yfinance
    watchlist: list = field(default_factory=lambda: list(DEFAULT_WATCHLIST))

    def __post_init__(self) -> None:
        if self.live_trading_enabled:
            raise ValueError(
                "Live trading is not available in Phase 1. "
                "Paper trading only — see vaulttec-architecture.md."
            )


def get_settings() -> Settings:
    return Settings()
