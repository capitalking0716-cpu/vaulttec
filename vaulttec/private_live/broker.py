"""Alpaca broker connector — plain REST, no extra dependency.

Uses only the Python standard library (``urllib``), so no Alpaca
SDK needs installing. Talks to the Alpaca Trading API v2:

- paper: https://paper-api.alpaca.markets
- live:  https://api.alpaca.markets  (only when the live gate in
  ``config.py`` is fully open — this module never decides that
  itself; the caller must call ``require_live`` first)

Orders are submitted as **bracket orders** (market buy with a
take-profit limit and a stop-loss attached at the broker), so the
stop and target live at Alpaca — not just in VaultTec's local
state. If VaultTec's computer is off, the broker still has the
stop. A bracket order is one order: if the stop or the target
fills, the other leg is cancelled by the broker.

Fractional shares: orders are placed by **notional** (dollar
amount), not share count, so a $5 position in a $600 stock is a
fractional holding. Alpaca supports fractional trading for
eligible US stocks and crypto; a symbol that does not support it
is rejected by the broker and the runner logs it and skips it.

Keys are passed in as strings and are NEVER written to any log,
report, or exception message. The transport (``request`` callable)
is injectable so tests can use a fake broker without touching the
network — no test in this repo ever calls the real Alpaca API.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import LIVE_BASE_URL, PAPER_BASE_URL, alpaca_symbol


class BrokerError(Exception):
    """An Alpaca API call failed (network or broker error)."""


@dataclass
class AlpacaBroker:
    api_key: str
    secret_key: str
    paper: bool = True

    def __post_init__(self) -> None:
        if not self.api_key or not self.secret_key:
            raise BrokerError(
                "Alpaca API keys are missing — set ALPACA_API_KEY and "
                "ALPACA_SECRET_KEY in .env (see private_live/RUNBOOK.md). "
                "No keys were invented."
            )

    @property
    def base_url(self) -> str:
        return PAPER_BASE_URL if self.paper else LIVE_BASE_URL

    # -- low-level transport (injectable for tests) -------------------

    def _request(self, method: str, path: str,
                 payload: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("APCA-API-KEY-ID", self.api_key)
        req.add_header("APCA-API-SECRET-KEY", self.secret_key)
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise BrokerError(
                f"Alpaca {method} {path} failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise BrokerError(
                f"Alpaca {method} {path} failed (network): {exc}"
            ) from exc

    # -- account / positions ------------------------------------------

    def get_account(self) -> dict:
        """Buying power, cash, portfolio value. No keys in the result."""
        return self._request("GET", "/v2/account")

    def get_positions(self) -> list[dict]:
        return self._request("GET", "/v2/positions")

    def get_position(self, symbol: str) -> dict | None:
        try:
            return self._request("GET", f"/v2/positions/{alpaca_symbol(symbol)}")
        except BrokerError as exc:
            if "404" in str(exc):
                return None
            raise

    def get_clock(self) -> dict:
        return self._request("GET", "/v2/clock")

    def list_orders(self, status: str = "open") -> list[dict]:
        return self._request("GET", f"/v2/orders?status={status}&limit=100")

    # -- orders ---------------------------------------------------------

    def submit_bracket_buy(self, *, symbol: str, notional_usd: float,
                           take_profit_usd: float, stop_loss_usd: float,
                           ) -> dict:
        """Market buy by dollar amount, with broker-side take-profit
        and stop-loss (a bracket order).

        ``notional_usd`` is the dollars to spend. The Risk Engine
        must already have approved the trade — this method does not
        re-check risk, it only talks to the broker. Prices are
        rounded to cents; the stop must be below and the target
        above the entry price (checked by the caller, since the
        entry price is the market price at fill time).
        """
        if notional_usd <= 0:
            raise ValueError("notional_usd must be positive")
        if stop_loss_usd <= 0 or take_profit_usd <= 0:
            raise ValueError("stop-loss and take-profit must be positive")
        payload = {
            "symbol": alpaca_symbol(symbol),
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "notional": f"{notional_usd:.2f}",
            "order_class": "bracket",
            "take_profit": {"limit_price": f"{take_profit_usd:.2f}"},
            "stop_loss": {"stop_price": f"{stop_loss_usd:.2f}"},
        }
        return self._request("POST", "/v2/orders", payload)

    def submit_sell(self, *, symbol: str, quantity: float) -> dict:
        """Market sell of a whole position (used for the 10-day time
        exit — bracket legs do not cover a time exit)."""
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        payload = {
            "symbol": alpaca_symbol(symbol),
            "side": "sell",
            "type": "market",
            "time_in_force": "day",
            "qty": f"{quantity:.9f}".rstrip("0").rstrip("."),
        }
        return self._request("POST", "/v2/orders", payload)

    def cancel_order(self, order_id: str) -> dict:
        return self._request("DELETE", f"/v2/orders/{order_id}")

    def close_position(self, symbol: str) -> dict:
        """Close a position at the broker (market). Used by the
        kill-switch path and the time exit."""
        return self._request("DELETE", f"/v2/positions/{alpaca_symbol(symbol)}")


@dataclass
class DryRunBroker:
    """Stand-in broker used when no Alpaca keys exist: it records
    what WOULD have been sent, and returns fake fills, so the
    runner logic can be tested end to end without a broker account.
    Every order it records is labelled dry-run."""
    orders: list[dict] = field(default_factory=list)
    paper: bool = True

    def get_account(self) -> dict:
        return {"cash": "0.00", "portfolio_value": "0.00",
                "buying_power": "0.00", "status": "ACTIVE",
                "dry_run": True}

    def get_positions(self) -> list[dict]:
        return []

    def get_position(self, symbol: str) -> dict | None:
        return None

    def get_clock(self) -> dict:
        return {"is_open": False, "dry_run": True}

    def list_orders(self, status: str = "open") -> list[dict]:
        return list(self.orders)

    def submit_bracket_buy(self, *, symbol: str, notional_usd: float,
                           take_profit_usd: float, stop_loss_usd: float) -> dict:
        order = {
            "id": f"dry-run-{len(self.orders) + 1}",
            "symbol": alpaca_symbol(symbol), "side": "buy",
            "notional": f"{notional_usd:.2f}",
            "take_profit": {"limit_price": f"{take_profit_usd:.2f}"},
            "stop_loss": {"stop_price": f"{stop_loss_usd:.2f}"},
            "status": "dry-run — NOT placed",
        }
        self.orders.append(order)
        return order

    def submit_sell(self, *, symbol: str, quantity: float) -> dict:
        order = {"id": f"dry-run-sell-{len(self.orders) + 1}",
                 "symbol": alpaca_symbol(symbol), "side": "sell",
                 "qty": quantity, "status": "dry-run — NOT placed"}
        self.orders.append(order)
        return order

    def cancel_order(self, order_id: str) -> dict:
        return {"id": order_id, "status": "dry-run — NOT cancelled"}

    def close_position(self, symbol: str) -> dict:
        return {"symbol": alpaca_symbol(symbol),
                "status": "dry-run — NOT closed"}
