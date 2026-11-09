"""Private-live configuration and the live-trading gate.

Keys come ONLY from the environment / ``.env`` — never from code,
never invented, never written to any report or log. If the keys
are missing, the module runs in dry-run mode (signals only, no
broker calls) so Neko can test the logic before he has an Alpaca
account.

The live gate is deliberately three locks, not one:
  1. ``VAULTTEC_LIVE_TRADING_ENABLED=true`` in the environment
  2. ``ALPACA_PAPER=false`` (paper is the default — ``true`` or
     unset both mean paper)
  3. ``private_live/LIVE_CONFIRMATION.txt`` exists and contains
     the exact confirmation line (see ``LIVE_CONFIRMATION_TEXT``)

If any lock is missing, ``is_live_enabled()`` is False and any
attempt to place a live order raises ``LiveTradingRefused``.
Paper mode needs no confirmation file.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import MAX_POSITION_PCT, MAX_RISK_PER_TRADE_PCT

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"

LIVE_CONFIRMATION_TEXT = (
    "I, Neko Robinson, confirm I want VaultTec PRIVATE to trade "
    "live with my own real money. I understand I can lose money."
)

# Alpaca crypto symbols use a slash (BTC/USD); the rest of VaultTec
# uses the yfinance form (BTC-USD). Stocks trade as-is.
CRYPTO_MAP = {"BTC-USD": "BTC/USD", "ETH-USD": "ETH/USD"}
# Alpaca paper trading supports crypto; if a symbol is ever
# rejected by the broker, the runner logs it and skips it — it
# never falls back to a different symbol.
STOCK_SYMBOLS = ["AAPL", "MSFT", "NVDA", "SPY", "AMZN", "GOOGL",
                 "META", "TSLA", "JPM", "JNJ"]
CRYPTO_SYMBOLS = ["BTC-USD", "ETH-USD"]
PRIVATE_UNIVERSE = STOCK_SYMBOLS + CRYPTO_SYMBOLS


class LiveTradingRefused(Exception):
    """Raised when live trading is requested but the gate is not open."""


def default_private_dir() -> Path:
    """private_live/ next to this package's project root."""
    return Path(__file__).resolve().parents[1] / "private_live"


def load_dotenv_if_present(project_root: Path | None = None) -> None:
    """Load ``.env`` from the project root if python-dotenv is
    available. Keys already in the environment win. Never raises
    if the file or the library is missing."""
    root = project_root or Path(__file__).resolve().parents[2]
    env_file = root / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=False)
    except Exception:  # noqa: BLE001 — .env is optional
        pass


@dataclass
class PrivateConfig:
    api_key: str = ""
    secret_key: str = ""
    paper: bool = True
    live_enabled_flag: bool = False
    confirmation_present: bool = False
    private_dir: Path = default_private_dir()
    max_position_pct: float = MAX_POSITION_PCT
    max_risk_per_trade_pct: float = MAX_RISK_PER_TRADE_PCT

    @property
    def has_keys(self) -> bool:
        return bool(self.api_key and self.secret_key)

    @property
    def base_url(self) -> str:
        return PAPER_BASE_URL if self.paper else LIVE_BASE_URL

    @property
    def is_live(self) -> bool:
        """True only when all three live locks are open."""
        return (
            self.live_enabled_flag
            and not self.paper
            and self.confirmation_present
        )

    @property
    def mode_label(self) -> str:
        if self.is_live:
            return "LIVE — real money"
        if self.has_keys:
            return "PAPER — Alpaca paper account"
        return "DRY-RUN — no broker keys, signals only"


def load_config(private_dir: Path | None = None) -> PrivateConfig:
    """Read the private-live config from the environment.

    ``ALPACA_PAPER`` defaults to ``true``. ``VAULTTEC_LIVE_TRADING_ENABLED``
    defaults to ``false``. Anything else in the environment is ignored.
    """
    load_dotenv_if_present()
    pdir = Path(private_dir) if private_dir else default_private_dir()
    confirmation_file = pdir / "LIVE_CONFIRMATION.txt"
    confirmation_present = False
    if confirmation_file.exists():
        try:
            confirmation_present = (
                confirmation_file.read_text(encoding="utf-8").strip()
                == LIVE_CONFIRMATION_TEXT
            )
        except OSError:
            confirmation_present = False
    return PrivateConfig(
        api_key=os.getenv("ALPACA_API_KEY", "").strip(),
        secret_key=os.getenv("ALPACA_SECRET_KEY", "").strip(),
        paper=os.getenv("ALPACA_PAPER", "true").strip().lower() != "false",
        live_enabled_flag=os.getenv(
            "VAULTTEC_LIVE_TRADING_ENABLED", "false").strip().lower() == "true",
        confirmation_present=confirmation_present,
        private_dir=pdir,
    )


def require_live(config: PrivateConfig) -> None:
    """Raise unless the live gate is fully open. Tells the user
    exactly which lock is still closed — never silently proceeds."""
    missing: list[str] = []
    if not config.live_enabled_flag:
        missing.append("VAULTTEC_LIVE_TRADING_ENABLED=true is not set")
    if config.paper:
        missing.append("ALPACA_PAPER is not false (paper is the default)")
    if not config.confirmation_present:
        missing.append(
            "private_live/LIVE_CONFIRMATION.txt is missing or does "
            "not contain the exact confirmation text")
    if missing:
        raise LiveTradingRefused(
            "Live trading refused — the live gate is not fully open: "
            + "; ".join(missing)
            + ". Paper mode is still available."
        )


def alpaca_symbol(symbol: str) -> str:
    """Map a VaultTec symbol to the form Alpaca expects."""
    return CRYPTO_MAP.get(symbol, symbol)


def vaulttec_symbol(alpaca_symbol_str: str) -> str:
    """Map an Alpaca symbol back to VaultTec form."""
    reverse = {v: k for k, v in CRYPTO_MAP.items()}
    return reverse.get(alpaca_symbol_str, alpaca_symbol_str)
