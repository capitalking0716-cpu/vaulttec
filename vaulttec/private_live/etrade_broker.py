"""E*TRADE broker for VaultTec's PRIVATE version — Neko only.

This mirrors ``vaulttec/private_live/broker.py`` (the Alpaca
broker) so the strategy and runner can use it unchanged: same
method names, same return shapes. What is different is everything
underneath, because E*TRADE's API is a different animal:

1. **Auth is OAuth 1.0a, not API-key headers.** Every request is
   signed (see ``etrade_oauth.py``). Getting an access token needs
   a human step: Neko opens an E*TRADE page in his browser, logs
   in, approves the app, and pastes back a short verifier code.
   Access tokens **die at midnight US Eastern every night** and
   go idle after ~2 hours without a call; there is no refresh
   token. After midnight, only a fresh browser approval mints a
   new one. VaultTec stores the token in a local file
   (``private_live/.etrade-tokens.json``, gitignored, never
   pushed) — never in code, never in chat.

2. **There is a sandbox** (``https://apisb.etrade.com``) with
   canned test data — it proves the request/response shapes work,
   NOT real fills or real account data. Production is
   ``https://api.etrade.com``. Sandbox and production keys and
   tokens cannot cross.

3. **No bracket / OCO orders through the API.** The E*TRADE
   website has them; the REST API does not. So
   ``submit_bracket_buy`` keeps the same name and signature as
   Alpaca's (the runner calls it that way), but on E*TRADE it
   places TWO separate orders: a market buy, then a standalone
   STOP sell (good-until-cancelled) as the stop-loss. The
   take-profit target is **NOT resting at the broker** — VaultTec
   itself watches the price and sells when the target hits (and
   cancels the stop first). If the stop order fails after the
   entry filled, the error says so loudly: the position is
   unprotected and must be dealt with by hand.

4. **Orders are by whole shares, not dollars.** E*TRADE's
   ``quantityType`` is QUANTITY only — there is no dollar
   (notional) order type through the API. VaultTec converts the
   dollar position into whole shares (rounded DOWN) from a fresh
   quote. If the dollars buy 0 whole shares, the broker REFUSES
   the trade and says so plainly. Fractional shares exist on
   E*TRADE's website for some names, but whether the REST API
   accepts a decimal quantity is **unverified** — the sandbox
   preview call is the test, and until it passes, the broker
   runs whole shares only (``allow_fractional=False``).

5. **Every order must be previewed before it is placed.**
   Preview returns a ``previewId``; the place call needs it.
   That is a safety win: the preview is a free check that
   catches bad symbols, bad quantities and insufficient funds
   before any money moves.

6. **No crypto.** E*TRADE is stocks (and options) only. BTC /
   ETH stay Alpaca-only. This broker refuses crypto symbols
   outright instead of sending them and hoping.

7. **No market-clock endpoint.** ``get_clock`` is an estimate
   from local New York time (Mon–Fri 9:30–16:00); US holidays
   are NOT excluded, and it says so in the answer.

8. **One account at a time.** Every call needs an
   ``accountIdKey`` (the encrypted account key from
   ``/v1/accounts/list``). It comes from the environment
   (``ETRADE_ACCOUNT_ID_KEY``) — never guessed, never logged.

LIVE GATE — same three locks as Alpaca, E*TRADE names:
  1. environment ``ETRADE_LIVE_TRADING_ENABLED=true``
  2. environment ``ETRADE_SANDBOX=false`` (sandbox is default)
  3. ``private_live/LIVE_CONFIRMATION.txt`` exists with the
     exact confirmation text (shared with the Alpaca gate)

Sandbox is the default and the only mode the tests exercise.
No live order is placed anywhere in this file unless the gate
is open AND the caller asked for it — and the runner still
requires Neko's explicit approval first.

No profit is promised. Past paper results do not guarantee
future results. This is Neko's own money at risk.
"""
from __future__ import annotations

import json
import math
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest
from zoneinfo import ZoneInfo

from .broker import BrokerError
from .config import LIVE_CONFIRMATION_TEXT, LiveTradingRefused
from .etrade_oauth import parse_token_response, sign_request

SANDBOX_HOST = "https://apisb.etrade.com"
PRODUCTION_HOST = "https://api.etrade.com"
AUTHORIZE_URL = "https://us.etrade.com/e/t/etws/authorize"
DEFAULT_TOKEN_PATH = Path(__file__).resolve().parent / ".etrade-tokens.json"

# E*TRADE does not trade crypto. Refuse these outright instead of
# sending a symbol the broker cannot fill.
CRYPTO_SYMBOLS = {"BTC-USD", "ETH-USD", "SOL-USD",
                  "BTC/USD", "ETH/USD", "SOL/USD"}

MAX_CLIENT_ORDER_ID_LEN = 20  # E*TRADE limit, per account, unique


# --- config / live gate ---------------------------------------------------

@dataclass
class ETradeConfig:
    """E*TRADE connection settings. Keys come only from the
    environment — never from code, never from a file in the repo."""
    consumer_key: str = ""
    consumer_secret: str = ""
    account_id_key: str = ""
    sandbox: bool = True
    live_enabled_flag: bool = False
    confirmation_present: bool = False
    private_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)

    @property
    def has_keys(self) -> bool:
        return bool(self.consumer_key and self.consumer_secret
                    and self.account_id_key)

    @property
    def is_live(self) -> bool:
        """Live only when ALL three locks are open AND keys exist."""
        return (self.has_keys and not self.sandbox
                and self.live_enabled_flag and self.confirmation_present)

    @property
    def mode_label(self) -> str:
        if not self.has_keys:
            return "DRY-RUN — no E*TRADE keys (nothing is placed)"
        return "LIVE" if self.is_live else "SANDBOX — paper only"


def load_etrade_config(private_dir: Path | None = None) -> ETradeConfig:
    """Read E*TRADE settings from the environment."""
    pdir = Path(private_dir) if private_dir else Path(__file__).resolve().parent
    confirmation_file = pdir / "LIVE_CONFIRMATION.txt"
    confirmation = False
    if confirmation_file.exists():
        confirmation = (confirmation_file.read_text(
            encoding="utf-8", errors="ignore").strip()
            == LIVE_CONFIRMATION_TEXT)
    return ETradeConfig(
        consumer_key=os.environ.get("ETRADE_CONSUMER_KEY", ""),
        consumer_secret=os.environ.get("ETRADE_CONSUMER_SECRET", ""),
        account_id_key=os.environ.get("ETRADE_ACCOUNT_ID_KEY", ""),
        sandbox=os.environ.get("ETRADE_SANDBOX", "true").lower() != "false",
        live_enabled_flag=os.environ.get(
            "ETRADE_LIVE_TRADING_ENABLED", "false").lower() == "true",
        confirmation_present=confirmation,
        private_dir=pdir,
    )


def require_etrade_live(config: ETradeConfig) -> None:
    """Refuse live E*TRADE trading unless all three locks are open.
    Raises LiveTradingRefused naming exactly which locks are shut."""
    missing = []
    if not config.has_keys:
        missing.append("ETRADE_CONSUMER_KEY / ETRADE_CONSUMER_SECRET / "
                       "ETRADE_ACCOUNT_ID_KEY (set in the environment)")
    if config.sandbox:
        missing.append("ETRADE_SANDBOX=false (sandbox is the default)")
    if not config.live_enabled_flag:
        missing.append("ETRADE_LIVE_TRADING_ENABLED=true")
    if not config.confirmation_present:
        missing.append("LIVE_CONFIRMATION.txt with the exact confirmation text")
    if missing:
        raise LiveTradingRefused(
            "E*TRADE live trading is LOCKED. Missing: " + "; ".join(missing))


# --- access-token storage ---------------------------------------------------

def _save_tokens(token_path: Path, token: str, token_secret: str) -> None:
    """Save an access token to disk with owner-only permissions.
    This file is gitignored (see .gitignore) and must never be
    pushed, emailed, or pasted into chat."""
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(json.dumps({
        "oauth_token": token,
        "oauth_token_secret": token_secret,
        "obtained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "note": "E*TRADE OAuth access token. Expires midnight US Eastern. "
                "Do not share. Do not commit.",
    }), encoding="utf-8")
    try:
        os.chmod(token_path, 0o600)
    except (OSError, NotImplementedError):
        pass  # Windows has no POSIX perms; the file stays local only


def _load_tokens(token_path: Path) -> dict[str, str]:
    """Load a saved access token. Missing/corrupt file -> {} (the
    caller then has to run the browser authorization flow)."""
    try:
        data = json.loads(token_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    token = data.get("oauth_token", "")
    secret = data.get("oauth_token_secret", "")
    if not token or not secret:
        return {}
    return {"oauth_token": token, "oauth_token_secret": secret}


# --- broker -----------------------------------------------------------------

class ETradeBroker:
    """E*TRADE REST API broker (v1), OAuth 1.0a signed.

    Same method names as ``AlpacaBroker`` so the runner works
    unchanged: ``get_account``, ``get_positions``,
    ``get_position``, ``get_clock``, ``list_orders``,
    ``submit_bracket_buy``, ``submit_sell``, ``cancel_order``,
    ``close_position``. Plus the OAuth lifecycle:
    ``begin_authorization``, ``complete_authorization``,
    ``renew_access_token``.
    """

    def __init__(self, consumer_key: str, consumer_secret: str,
                 account_id_key: str, sandbox: bool = True,
                 access_token: str | None = None,
                 access_token_secret: str | None = None,
                 token_path: Path | None = None,
                 allow_fractional: bool = False):
        if not consumer_key or not consumer_secret or not account_id_key:
            raise BrokerError(
                "E*TRADE API keys are missing — set ETRADE_CONSUMER_KEY, "
                "ETRADE_CONSUMER_SECRET and ETRADE_ACCOUNT_ID_KEY in the "
                "environment (or Streamlit Secrets). Keys are never typed "
                "into code or chat.")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.account_id_key = account_id_key
        self.sandbox = sandbox
        self.host = SANDBOX_HOST if sandbox else PRODUCTION_HOST
        self.allow_fractional = allow_fractional
        self.token_path = Path(token_path) if token_path else DEFAULT_TOKEN_PATH
        saved = _load_tokens(self.token_path)
        self.access_token = access_token or saved.get("oauth_token")
        self.access_token_secret = (access_token_secret
                                    or saved.get("oauth_token_secret"))
        # symbol -> resting stop-order id, so a sell can cancel the
        # stop first and never leave a live stop with no position.
        self._stop_orders: dict[str, str] = {}
        self._request_token: str | None = None
        self._request_token_secret: str | None = None

    # -- transport (the seam tests override) --------------------------------

    def _request(self, method: str, path: str,
                 params: dict[str, str] | None = None,
                 payload: dict | None = None):
        """One signed API call. Returns parsed JSON, or raw text
        for the OAuth token endpoints (they answer in query
        strings, not JSON). Raises BrokerError on any failure."""
        url = f"{self.host}{path}"
        query = dict(params or {})
        header = sign_request(
            method, url, query, self.consumer_key, self.consumer_secret,
            token=self.access_token, token_secret=self.access_token_secret or "")
        if query:
            url = f"{url}?{urlparse.urlencode(query)}"
        data = None
        headers = {"Authorization": header, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urlrequest.Request(url, data=data, headers=headers, method=method)
        try:
            with urlrequest.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urlerror.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
            except OSError:
                pass
            raise BrokerError(
                f"E*TRADE request failed ({method} {path}): HTTP "
                f"{exc.code} {detail}") from exc
        except urlerror.URLError as exc:
            raise BrokerError(
                f"E*TRADE request failed ({method} {path}): network "
                f"error {exc.reason}") from exc
        if path.startswith("/oauth/"):
            return body
        try:
            return json.loads(body) if body.strip() else {}
        except ValueError:
            return {"_raw": body}

    # -- OAuth lifecycle ------------------------------------------------------

    def begin_authorization(self) -> str:
        """Step 1 of 3: fetch a request token and return the E*TRADE
        authorize URL. Neko opens that URL in his browser, logs in
        to E*TRADE, approves the app, and gets a short verifier
        code to paste back (see ``complete_authorization``).
        Request tokens live about 5 minutes — do not dawdle."""
        body = self._request("GET", "/oauth/request_token",
                             params={"oauth_callback": "oob"})
        data = parse_token_response(body if isinstance(body, str) else "")
        token = data.get("oauth_token", "")
        secret = data.get("oauth_token_secret", "")
        if not token or not secret:
            raise BrokerError(
                "E*TRADE did not return a request token — check the "
                "consumer key/secret and that the sandbox key is active.")
        self._request_token = token
        self._request_token_secret = secret
        return (f"{AUTHORIZE_URL}?key={urlparse.quote(self.consumer_key)}"
                f"&token={urlparse.quote(token)}")

    def complete_authorization(self, verifier: str) -> bool:
        """Step 3 of 3: trade the verifier code (typed by Neko, never
        stored in chat) for an access token, and save that token to
        the local token file. Returns True on success."""
        if not self._request_token or not self._request_token_secret:
            raise BrokerError(
                "No request token — call begin_authorization() first and "
                "open the authorize URL.")
        # The access-token call is signed with the REQUEST token.
        saved_token, saved_secret = self.access_token, self.access_token_secret
        self.access_token, self.access_token_secret = (
            self._request_token, self._request_token_secret)
        try:
            body = self._request(
                "GET", "/oauth/access_token",
                params={"oauth_verifier": verifier.strip()})
        finally:
            self.access_token, self.access_token_secret = saved_token, saved_secret
        data = parse_token_response(body if isinstance(body, str) else "")
        token = data.get("oauth_token", "")
        secret = data.get("oauth_token_secret", "")
        if not token or not secret:
            raise BrokerError(
                "E*TRADE did not return an access token — the verifier "
                "may have expired (request tokens live ~5 minutes). "
                "Start again with begin_authorization().")
        self.access_token, self.access_token_secret = token, secret
        _save_tokens(self.token_path, token, secret)
        return True

    def renew_access_token(self) -> bool:
        """Revive an access token that went idle (no calls for ~2
        hours) — only works within the same day. After midnight US
        Eastern the token is dead and only a fresh browser
        authorization (``begin_authorization``) mints a new one."""
        if not self.access_token:
            return False
        body = self._request("GET", "/oauth/renew_access_token")
        data = parse_token_response(body if isinstance(body, str) else "")
        return bool(data.get("oauth_token"))

    def token_status(self) -> dict:
        """What the panel needs to know: is there a token at all?
        (It never reveals the token itself.)"""
        return {
            "has_token": bool(self.access_token),
            "sandbox": self.sandbox,
            "note": "E*TRADE access tokens expire at midnight US Eastern "
                    "and go idle after ~2 hours without a call. After "
                    "midnight, re-authorize in the browser.",
        }

    # -- helpers ---------------------------------------------------------------

    def _require_token(self) -> None:
        if not self.access_token:
            raise BrokerError(
                "No E*TRADE access token — run the browser authorization "
                "first (begin_authorization, open the URL, approve, then "
                "complete_authorization with the verifier code). Tokens "
                "are saved locally and expire at midnight US Eastern.")

    @staticmethod
    def _client_order_id() -> str:
        """Unique per account, max 20 alphanumeric characters."""
        return f"VT{int(time.time())}{secrets.token_hex(2)}"[:20]

    @staticmethod
    def _as_float(value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _account_path(self, suffix: str) -> str:
        return f"/v1/accounts/{self.account_id_key}{suffix}"

    # -- account / positions / quotes (read-only) -------------------------------

    def list_accounts(self) -> list[dict]:
        """All accounts on this login — used to find the right
        ``accountIdKey``. Returns description + value only; the key
        itself is carried in the dict because the caller needs it
        to configure the broker, and is never logged by this code."""
        self._require_token()
        data = self._request("GET", "/v1/accounts/list")
        accounts = (data.get("AccountListResponse", {}).get("Account", [])
                    if isinstance(data, dict) else [])
        if isinstance(accounts, dict):
            accounts = [accounts]
        return [{
            "account_id_key": a.get("accountIdKey", ""),
            "description": a.get("accountDesc", ""),
            "net_account_value": self._as_float(a.get("netAccountValue")),
        } for a in accounts if isinstance(a, dict)]

    def get_account(self) -> dict:
        """Cash, portfolio value and buying power for the configured
        account. Field names come from E*TRADE's BalanceResponse
        docs; several fallbacks are tried because the sandbox
        answers with stored sample data whose shape can differ
        from the live shape. Values are numbers, matching the
        Alpaca broker's return shape."""
        self._require_token()
        data = self._request(
            "GET", self._account_path("/balance"),
            params={"instType": "BROKERAGE", "realTimeNAV": "true"})
        resp = data.get("BalanceResponse", {}) if isinstance(data, dict) else {}
        computed = resp.get("computedBalance", {}) or {}
        account_bal = resp.get("accountBalance", {}) or {}
        real_time = resp.get("RealTimeValues", {}) or {}
        portfolio_value = (
            self._as_float(real_time.get("totalAccountValue"), 0.0)
            or self._as_float(computed.get("accountBalance"), 0.0)
            or self._as_float(account_bal.get("netAccountValue"), 0.0))
        cash = (
            self._as_float(computed.get("cashAvailableForInvestment"), 0.0)
            or self._as_float(account_bal.get("cashAvailableForWithdrawal"), 0.0)
            or self._as_float(computed.get("cashBalance"), 0.0))
        return {"cash": round(cash, 2),
                "portfolio_value": round(portfolio_value, 2),
                "buying_power": round(cash, 2),
                "status": "ACTIVE"}

    def get_positions(self) -> list[dict]:
        self._require_token()
        data = self._request("GET", self._account_path("/portfolio"))
        positions = (data.get("PortfolioResponse", {}).get("Position", [])
                     if isinstance(data, dict) else [])
        if isinstance(positions, dict):
            positions = [positions]
        out = []
        for p in positions:
            if not isinstance(p, dict):
                continue
            out.append({
                "symbol": str(p.get("symbol", "")),
                "qty": self._as_float(p.get("quantity")),
                "market_value": self._as_float(p.get("marketValue")),
                "price_paid": self._as_float(p.get("pricePaid")),
            })
        return out

    def get_position(self, symbol: str) -> dict | None:
        for pos in self.get_positions():
            if pos["symbol"].upper() == symbol.upper():
                return pos
        return None

    def get_quote(self, symbol: str) -> float:
        """Latest trade price for one symbol, from
        ``/v1/market/quote/{symbol}.json``."""
        self._require_token()
        data = self._request(
            "GET", f"/v1/market/quote/{urlparse.quote(symbol)}.json")
        quotes = (data.get("QuoteResponse", {}).get("QuoteData", [])
                  if isinstance(data, dict) else [])
        if isinstance(quotes, dict):
            quotes = [quotes]
        for q in quotes:
            if not isinstance(q, dict):
                continue
            all_data = q.get("All", {}) or {}
            price = (self._as_float(all_data.get("lastTrade"), 0.0)
                     or self._as_float(q.get("lastTrade"), 0.0)
                     or self._as_float(all_data.get("close"), 0.0))
            if price > 0:
                return price
        raise BrokerError(f"E*TRADE returned no price for {symbol}")

    def get_clock(self) -> dict:
        """E*TRADE's API has NO market-clock endpoint, so this is an
        estimate from local New York time (Mon–Fri 09:30–16:00).
        US market holidays are NOT excluded — the answer says so."""
        now = datetime.now(ZoneInfo("America/New_York"))
        is_open = (now.weekday() < 5
                   and (now.hour, now.minute) >= (9, 30)
                   and (now.hour, now.minute) < (16, 0))
        return {"is_open": is_open,
                "timestamp": now.isoformat(),
                "source": "estimate — E*TRADE API has no clock endpoint; "
                          "US holidays not excluded"}

    def list_orders(self, status: str = "OPEN") -> list[dict]:
        self._require_token()
        data = self._request(
            "GET", self._account_path("/orders"),
            params={"status": status.upper()})
        orders = (data.get("OrdersResponse", {}).get("Order", [])
                  if isinstance(data, dict) else [])
        if isinstance(orders, dict):
            orders = [orders]
        return [o for o in orders if isinstance(o, dict)]

    # -- orders (preview is mandatory before place) -----------------------------

    def _preview_order(self, *, symbol: str, order_action: str,
                       quantity, price_type: str, order_term: str,
                       stop_price: float | None = None,
                       limit_price: float | None = None) -> str:
        """Preview an equity order. Returns the previewId that the
        place call must carry. A failed preview raises BrokerError
        with E*TRADE's message — nothing is placed."""
        order: dict = {
            "orderType": "EQ",
            "clientOrderId": self._client_order_id(),
            "Order": [{
                "allOrNone": False,
                "priceType": price_type,
                "orderTerm": order_term,
                "marketSession": "REGULAR",
                "stopPrice": stop_price,
                "limitPrice": limit_price,
                "Instrument": [{
                    "Product": {"securityType": "EQ", "symbol": symbol},
                    "orderAction": order_action,
                    "quantityType": "QUANTITY",
                    "quantity": quantity,
                }],
            }],
        }
        data = self._request(
            "POST", self._account_path("/orders/preview"), payload={
                "PreviewOrderRequest": order})
        preview = (data.get("PreviewOrderResponse", {}) if isinstance(data, dict)
                   else {})
        ids = preview.get("PreviewIds") or {}
        preview_id = ids.get("previewId") if isinstance(ids, dict) else None
        if not preview_id:
            raise BrokerError(
                f"E*TRADE preview failed for {order_action} {quantity}x "
                f"{symbol} ({price_type}) — no previewId returned. "
                "Nothing was placed.")
        return str(preview_id)

    def _place_order(self, *, symbol: str, order_action: str,
                     quantity, price_type: str, order_term: str,
                     preview_id: str, stop_price: float | None = None,
                     limit_price: float | None = None) -> dict:
        """Place a previewed equity order. Returns the raw order
        summary (orderId lives under PlaceOrderResponse.OrderIds)."""
        order: dict = {
            "orderType": "EQ",
            "clientOrderId": self._client_order_id(),
            "PreviewIds": [{"previewId": preview_id}],
            "Order": [{
                "allOrNone": False,
                "priceType": price_type,
                "orderTerm": order_term,
                "marketSession": "REGULAR",
                "stopPrice": stop_price,
                "limitPrice": limit_price,
                "Instrument": [{
                    "Product": {"securityType": "EQ", "symbol": symbol},
                    "orderAction": order_action,
                    "quantityType": "QUANTITY",
                    "quantity": quantity,
                }],
            }],
        }
        data = self._request(
            "POST", self._account_path("/orders/place"), payload={
                "PlaceOrderRequest": order})
        placed = (data.get("PlaceOrderResponse", {}) if isinstance(data, dict)
                  else {})
        ids = placed.get("OrderIds") or {}
        order_id = ids.get("orderId") if isinstance(ids, dict) else None
        if not order_id:
            raise BrokerError(
                f"E*TRADE place failed for {order_action} {quantity}x "
                f"{symbol} — no orderId returned.")
        return {"id": str(order_id), "status": "accepted",
                "preview_id": preview_id}

    def cancel_order(self, order_id: str) -> dict:
        self._require_token()
        data = self._request(
            "PUT", self._account_path("/orders/cancel"), payload={
                "CancelOrderRequest": {"orderId": int(order_id)}})
        cancelled = (data.get("CancelOrderResponse", {}) if isinstance(data, dict)
                     else {})
        return {"id": str(order_id),
                "status": str(cancelled.get("orderId", order_id)),
                "cancelled": True}

    # -- wide-6 entry / exit (same signatures as the Alpaca broker) -------------

    def submit_bracket_buy(self, *, symbol: str, notional_usd: float,
                           take_profit_usd: float, stop_loss_usd: float) -> dict:
        """Buy with the wide-6 stop and target — E*TRADE style.

        There is NO bracket order at E*TRADE, so this places:
          1. a market buy for WHOLE shares (dollars converted from
             a fresh quote, rounded DOWN), then
          2. a standalone STOP sell (good-until-cancelled) for the
             same whole shares at ``stop_loss_usd``.
        The take-profit target is NOT placed at the broker — no
        OCO exists to link it — VaultTec watches the price and
        sells when the target hits, cancelling the stop first.

        Refuses crypto, and refuses when the dollars buy 0 whole
        shares. If the entry fills but the stop order fails, the
        error says the position is UNPROTECTED — do not ignore it.
        """
        if symbol.upper() in CRYPTO_SYMBOLS:
            raise BrokerError(
                f"E*TRADE does not trade crypto — {symbol} cannot be "
                "placed here. Crypto stays on Alpaca (paper).")
        self._require_token()
        price = self.get_quote(symbol)
        if self.allow_fractional:
            # UNVERIFIED: whether the REST API accepts a decimal
            # quantity. The sandbox preview call is the test — if it
            # rejects, the error below surfaces it and whole shares
            # stay the rule.
            qty: float = math.floor(notional_usd / price * 1000) / 1000
            if qty <= 0:
                raise BrokerError(
                    f"${notional_usd:.2f} buys 0 shares of {symbol} at "
                    f"${price:.2f} — even fractional. Position too small.")
        else:
            qty = int(notional_usd // price)
            if qty < 1:
                raise BrokerError(
                    f"E*TRADE trades whole shares: ${notional_usd:.2f} "
                    f"buys 0 shares of {symbol} at ${price:.2f}. On "
                    "Alpaca that same money buys a fraction; here it "
                    "buys nothing. Use a bigger position or a cheaper "
                    "symbol.")
        actual_notional = round(qty * price, 2)
        entry_preview = self._preview_order(
            symbol=symbol, order_action="BUY", quantity=qty,
            price_type="MARKET", order_term="GOOD_FOR_DAY")
        entry = self._place_order(
            symbol=symbol, order_action="BUY", quantity=qty,
            price_type="MARKET", order_term="GOOD_FOR_DAY",
            preview_id=entry_preview)
        # The stop is a separate, standalone order. If it fails,
        # the entry is already live and UNPROTECTED — say so loudly.
        try:
            stop_preview = self._preview_order(
                symbol=symbol, order_action="SELL", quantity=qty,
                price_type="STOP", order_term="GOOD_UNTIL_CANCEL",
                stop_price=round(stop_loss_usd, 2))
            stop = self._place_order(
                symbol=symbol, order_action="SELL", quantity=qty,
                price_type="STOP", order_term="GOOD_UNTIL_CANCEL",
                preview_id=stop_preview,
                stop_price=round(stop_loss_usd, 2))
        except BrokerError as exc:
            raise BrokerError(
                f"ENTRY PLACED (order {entry['id']}) but the stop-loss "
                f"order FAILED: {exc} — the position is UNPROTECTED. "
                "Place a stop by hand in E*TRADE, or sell the position.") from exc
        self._stop_orders[symbol.upper()] = str(stop["id"])
        return {
            "id": entry["id"], "symbol": symbol, "status": "accepted",
            "qty": qty, "entry_price": price,
            "notional_usd": actual_notional,
            "stop_order_id": stop["id"],
            "take_profit_usd": take_profit_usd,
            "take_profit_note": "VaultTec-managed — E*TRADE has no "
                                "bracket/OCO orders, so the target is NOT "
                                "resting at the broker.",
        }

    def submit_sell(self, *, symbol: str, quantity: float) -> dict:
        """Sell at market — cancelling any resting stop for the
        symbol FIRST, so a filled sale never leaves a live stop
        order behind (in a margin account that could open a short
        position). ``quantity`` is a hint from the runner's
        position record (which can be fractional for Alpaca);
        E*TRADE sells whole shares, never more than actually held,
        and sells the whole position when the hint is under 1."""
        self._require_token()
        stop_id = self._stop_orders.pop(symbol.upper(), None)
        if stop_id:
            try:
                self.cancel_order(stop_id)
            except BrokerError as exc:
                self._stop_orders[symbol.upper()] = stop_id
                raise BrokerError(
                    f"Could not cancel the resting stop order {stop_id} "
                    f"for {symbol}: {exc} — NOT selling, so the stop "
                    "cannot fire against a position that is gone.") from exc
        position = self.get_position(symbol)
        if position is None or position["qty"] <= 0:
            raise BrokerError(f"No E*TRADE position in {symbol} to sell.")
        held = int(position["qty"])
        if quantity >= 1:
            sell_qty = min(int(quantity), held)
        else:
            sell_qty = held  # fractional hint: sell the whole position
        if sell_qty < 1:
            raise BrokerError(
                f"Cannot sell {symbol}: {held} whole share(s) held, "
                "nothing whole to sell.")
        preview_id = self._preview_order(
            symbol=symbol, order_action="SELL", quantity=sell_qty,
            price_type="MARKET", order_term="GOOD_FOR_DAY")
        order = self._place_order(
            symbol=symbol, order_action="SELL", quantity=sell_qty,
            price_type="MARKET", order_term="GOOD_FOR_DAY",
            preview_id=preview_id)
        order["qty"] = sell_qty
        return order

    def close_position(self, symbol: str) -> dict:
        """Close a position at the broker (market). Used by the
        kill-switch path and the time exit. Cancels any open orders
        for the symbol first, then sells everything held."""
        self._require_token()
        for open_order in self.list_orders(status="OPEN"):
            instruments = open_order.get("Instrument", []) or []
            for inst in instruments:
                product = inst.get("Product", {}) or {}
                if str(product.get("symbol", "")).upper() == symbol.upper():
                    order_id = str(open_order.get("orderId", ""))
                    if order_id:
                        self.cancel_order(order_id)
        position = self.get_position(symbol)
        if position is None or position["qty"] <= 0:
            return {"symbol": symbol, "status": "no position to close"}
        return self.submit_sell(symbol=symbol, quantity=float(position["qty"]))


# --- dry-run broker (no network, no keys) --------------------------------------

@dataclass
class ETradeDryRunBroker:
    """Stand-in E*TRADE broker: records what WOULD have been sent
    (preview -> place, entry + standalone stop) and returns fake
    fills, so the runner logic can be tested end to end without
    keys, tokens, or a sandbox account. Every order it records is
    labelled dry-run. Whole-share sizing applies here too — the
    point is to catch $5-buys-0-shares cases before real money
    is anywhere near them.

    ``prices`` maps symbol -> assumed price for sizing (tests
    pass real ones). A symbol with no price assumes $100.00 and
    the record says so.
    """
    orders: list[dict] = field(default_factory=list)
    paper: bool = True
    prices: dict[str, float] = field(default_factory=dict)
    allow_fractional: bool = False

    def _price(self, symbol: str) -> tuple[float, bool]:
        if symbol in self.prices:
            return self.prices[symbol], False
        return 100.00, True

    def get_account(self) -> dict:
        return {"cash": "0.00", "portfolio_value": "0.00",
                "buying_power": "0.00", "status": "ACTIVE", "dry_run": True}

    def get_positions(self) -> list[dict]:
        return []

    def get_position(self, symbol: str) -> dict | None:
        return None

    def get_clock(self) -> dict:
        return {"is_open": False, "dry_run": True}

    def list_orders(self, status: str = "OPEN") -> list[dict]:
        return list(self.orders)

    def submit_bracket_buy(self, *, symbol: str, notional_usd: float,
                           take_profit_usd: float, stop_loss_usd: float) -> dict:
        if symbol.upper() in CRYPTO_SYMBOLS:
            raise BrokerError(
                f"E*TRADE does not trade crypto — {symbol} cannot be "
                "placed here. Crypto stays on Alpaca (paper).")
        price, assumed = self._price(symbol)
        if self.allow_fractional:
            qty: float = math.floor(notional_usd / price * 1000) / 1000
            if qty <= 0:
                raise BrokerError(
                    f"${notional_usd:.2f} buys 0 shares of {symbol} at "
                    f"${price:.2f} — even fractional. Position too small.")
        else:
            qty = int(notional_usd // price)
            if qty < 1:
                raise BrokerError(
                    f"E*TRADE trades whole shares: ${notional_usd:.2f} "
                    f"buys 0 shares of {symbol} at ${price:.2f}. On "
                    "Alpaca that same money buys a fraction; here it "
                    "buys nothing. Use a bigger position or a cheaper "
                    "symbol.")
        entry = {
            "id": f"dry-run-etrade-{len(self.orders) + 1}",
            "symbol": symbol, "side": "buy",
            "qty": qty, "entry_price": price,
            "notional": f"{qty * price:.2f}",
            "stop_order_id": f"dry-run-stop-{len(self.orders) + 1}",
            "stop_loss": {"stop_price": f"{stop_loss_usd:.2f}"},
            "take_profit": {"limit_price": f"{take_profit_usd:.2f}",
                            "note": "VaultTec-managed, not at the broker"},
            "status": "dry-run — NOT placed",
        }
        if assumed:
            entry["price_assumed"] = ("no price supplied for sizing; "
                                      "assumed $100.00")
        self.orders.append(entry)
        return entry

    def submit_sell(self, *, symbol: str, quantity: float) -> dict:
        order = {"id": f"dry-run-etrade-sell-{len(self.orders) + 1}",
                 "symbol": symbol, "side": "sell",
                 "qty": quantity, "status": "dry-run — NOT placed"}
        self.orders.append(order)
        return order

    def cancel_order(self, order_id: str) -> dict:
        return {"id": order_id, "status": "dry-run — NOT cancelled"}

    def close_position(self, symbol: str) -> dict:
        return {"symbol": symbol, "status": "dry-run — NOT closed"}
