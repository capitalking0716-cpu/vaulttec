"""E*TRADE broker tests — stubs and fakes only, no network.

The real E*TRADE API is never called here. The broker is faked
by subclassing ``ETradeBroker`` and overriding ``_request`` with
canned sandbox-shaped JSON, and the OAuth signer is checked
against the worked example in RFC 5849 section 3.4.1.3.2.

Tests check the guarantees that matter: the signer is correct,
live is locked off by default, crypto is refused, orders are
whole shares (so $5 cannot buy 0 shares of a $610 stock),
every order is previewed before it is placed, the stop-loss
rides as its own order (E*TRADE has no bracket orders) and is
cancelled before any sell, and an entry whose stop fails is
reported as UNPROTECTED — never silently left that way.
"""
import json
import re
import stat
from urllib.parse import unquote
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.private_live.broker import BrokerError
from vaulttec.private_live.config import (
    LIVE_CONFIRMATION_TEXT,
    LiveTradingRefused,
)
from vaulttec.private_live.etrade_broker import (
    ETradeBroker,
    ETradeConfig,
    ETradeDryRunBroker,
    load_etrade_config,
    require_etrade_live,
)
from vaulttec.private_live.etrade_oauth import (
    authorization_header,
    build_signature_base_string,
    oauth_params,
    percent_encode,
    sign,
    sign_request,
)

ACCOUNT_KEY = "vsnhtF7d9jXxBy6HyaAC4vQ"


# --- OAuth 1.0a signing (RFC 5849 section 3.4.1.3.2) --------------------------

def test_percent_encode_uses_percent_20_not_plus():
    assert percent_encode("a b") == "a%20b"
    assert percent_encode("~") == "~"          # unreserved, untouched
    assert percent_encode("vacation.jpg") == "vacation.jpg"
    assert percent_encode("a+b&c=d") == "a%2Bb%26c%3Dd"


def test_rfc5849_signature_base_string():
    params = {
        "file": "vacation.jpg",
        "size": "original",
        "oauth_consumer_key": "dpf43f3p2l4k3l03",
        "oauth_token": "nnch734d00sl2jdk",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": "1191242096",
        "oauth_nonce": "kllo9940pd9333jh",
        "oauth_version": "1.0",
    }
    expected = (
        "GET&http%3A%2F%2Fphotos.example.net%2Fphotos&"
        "file%3Dvacation.jpg%26oauth_consumer_key%3Ddpf43f3p2l4k3l03"
        "%26oauth_nonce%3Dkllo9940pd9333jh"
        "%26oauth_signature_method%3DHMAC-SHA1"
        "%26oauth_timestamp%3D1191242096"
        "%26oauth_token%3Dnnch734d00sl2jdk"
        "%26oauth_version%3D1.0%26size%3Doriginal")
    assert build_signature_base_string(
        "GET", "http://photos.example.net/photos", params) == expected


def test_rfc5849_signature():
    params = {
        "file": "vacation.jpg",
        "size": "original",
        "oauth_consumer_key": "dpf43f3p2l4k3l03",
        "oauth_token": "nnch734d00sl2jdk",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": "1191242096",
        "oauth_nonce": "kllo9940pd9333jh",
        "oauth_version": "1.0",
    }
    assert sign("GET", "http://photos.example.net/photos", params,
                "kd94hf93k423kf44", "pfkkdhi9sl3r4s00") == \
        "tR3+Ty81lMeYAr/Fid0kMTYa/WM="


def test_sign_request_header_signature_verifies():
    header = sign_request(
        "GET", "https://apisb.etrade.com/v1/accounts/list", {},
        "CONSUMER", "CONSUMER-SECRET",
        token="TOKEN", token_secret="TOKEN-SECRET")
    assert header.startswith("OAuth ")
    fields = dict(re.findall(r'(\w+)="([^"]*)"', header))
    assert fields["oauth_consumer_key"] == "CONSUMER"
    assert fields["oauth_token"] == "TOKEN"
    assert fields["oauth_signature_method"] == "HMAC-SHA1"
    assert fields["oauth_version"] == "1.0"
    # Recompute the signature from the header's own nonce/timestamp
    # and check it matches what the header carries (the header value
    # is percent-encoded, so unquote it first).
    oauth = oauth_params("CONSUMER", token="TOKEN")
    oauth["oauth_nonce"] = fields["oauth_nonce"]
    oauth["oauth_timestamp"] = fields["oauth_timestamp"]
    expected = sign("GET", "https://apisb.etrade.com/v1/accounts/list",
                    oauth, "CONSUMER-SECRET", "TOKEN-SECRET")
    assert unquote(fields["oauth_signature"]) == expected


def test_oauth_header_is_sorted_and_quoted():
    header = authorization_header({"b": "2", "a": "1"})
    assert header == 'OAuth a="1", b="2"'


# --- config / live gate -------------------------------------------------------

def _clean_env(monkeypatch):
    for key in ("ETRADE_CONSUMER_KEY", "ETRADE_CONSUMER_SECRET",
                "ETRADE_ACCOUNT_ID_KEY", "ETRADE_SANDBOX",
                "ETRADE_LIVE_TRADING_ENABLED"):
        monkeypatch.delenv(key, raising=False)


def test_etrade_live_off_by_default(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    cfg = load_etrade_config(tmp_path)
    assert cfg.sandbox is True
    assert cfg.is_live is False
    assert cfg.has_keys is False
    assert cfg.mode_label.startswith("DRY-RUN")


def test_etrade_gate_opens_only_with_all_three_locks(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("ETRADE_CONSUMER_KEY", "k")
    monkeypatch.setenv("ETRADE_CONSUMER_SECRET", "s")
    monkeypatch.setenv("ETRADE_ACCOUNT_ID_KEY", ACCOUNT_KEY)
    monkeypatch.setenv("ETRADE_SANDBOX", "false")
    monkeypatch.setenv("ETRADE_LIVE_TRADING_ENABLED", "true")
    (tmp_path / "LIVE_CONFIRMATION.txt").write_text(
        LIVE_CONFIRMATION_TEXT, encoding="utf-8")
    cfg = load_etrade_config(tmp_path)
    assert cfg.is_live is True
    assert cfg.mode_label == "LIVE"
    require_etrade_live(cfg)  # does not raise


def test_require_etrade_live_names_etrade_locks(tmp_path):
    cfg = ETradeConfig(sandbox=True, live_enabled_flag=False,
                       confirmation_present=False, private_dir=tmp_path)
    with pytest.raises(LiveTradingRefused) as exc:
        require_etrade_live(cfg)
    assert "ETRADE_LIVE_TRADING_ENABLED" in str(exc.value)
    assert "ETRADE_SANDBOX" in str(exc.value)
    assert "LIVE_CONFIRMATION" in str(exc.value)


# --- fake broker --------------------------------------------------------------

class FakeETradeBroker(ETradeBroker):
    """Records every request instead of calling E*TRADE."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("token_path", Path("/tmp/etrade-test-tokens.json"))
        super().__init__(*args, **kwargs)
        self.calls: list[dict] = []
        self.preview_count = 0
        self.place_count = 0
        self.fail_preview_number: int | None = None
        self.balance_variant = "realtime"

    def _request(self, method, path, params=None, payload=None):
        self.calls.append({"method": method, "path": path,
                           "params": params, "payload": payload})
        if path == "/oauth/request_token":
            return ("oauth_token=REQTOK&oauth_token_secret=REQSEC"
                    "&oauth_callback_confirmed=true")
        if path == "/oauth/access_token":
            return "oauth_token=ACCTOK&oauth_token_secret=ACCSEC"
        if path == "/oauth/renew_access_token":
            return "oauth_token=ACCTOK&oauth_token_secret=ACCSEC"
        if path.startswith("/v1/market/quote/"):
            symbol = path.split("/")[4].removesuffix(".json")
            price = {"AAPL": 100.00, "META": 610.15}.get(symbol, 50.00)
            return {"QuoteResponse": {"QuoteData": [{
                "symbol": symbol,
                "All": {"lastTrade": price}}]}}
        if path == "/v1/accounts/list":
            return {"AccountListResponse": {"Account": [{
                "accountIdKey": ACCOUNT_KEY, "accountDesc": "INDIVIDUAL",
                "netAccountValue": 5000.00}]}}
        if path.endswith("/balance"):
            if self.balance_variant == "realtime":
                return {"BalanceResponse": {
                    "accountId": "83353535",
                    "computedBalance": {"cashAvailableForInvestment": 250.00},
                    "RealTimeValues": {"totalAccountValue": 5000.00}}}
            return {"BalanceResponse": {
                "accountBalance": {"netAccountValue": 4200.00,
                                   "cashAvailableForWithdrawal": 180.00}}}
        if path.endswith("/portfolio"):
            return {"PortfolioResponse": {"Position": [{
                "symbol": "AAPL", "quantity": 10,
                "pricePaid": 95.00, "marketValue": 1000.00}]}}
        if path.endswith("/orders") and method == "GET":
            return {"OrdersResponse": {"Order": [
                {"orderId": 777, "orderType": "EQ",
                 "Instrument": [{"Product": {"symbol": "AAPL"}}]},
                {"orderId": 888, "orderType": "EQ",
                 "Instrument": [{"Product": {"symbol": "MSFT"}}]},
            ]}}
        if path.endswith("/orders/preview"):
            self.preview_count += 1
            if self.fail_preview_number == self.preview_count:
                raise BrokerError("broker says: stop price invalid")
            return {"PreviewOrderResponse": {
                "PreviewIds": {"previewId": f"PREVIEW-{self.preview_count}"}}}
        if path.endswith("/orders/place"):
            self.place_count += 1
            return {"PlaceOrderResponse": {
                "OrderIds": {"orderId": 1000 + self.place_count}}}
        if path.endswith("/orders/cancel"):
            return {"CancelOrderResponse": {"orderId": 777}}
        return {}


def _broker(tmp_path, **kwargs):
    return FakeETradeBroker(
        consumer_key="CONSUMER", consumer_secret="SECRET",
        account_id_key=ACCOUNT_KEY, sandbox=True,
        access_token="ACCTOK", access_token_secret="ACCSEC",
        token_path=tmp_path / ".etrade-tokens.json", **kwargs)


# --- broker basics ------------------------------------------------------------

def test_broker_refuses_without_keys(tmp_path):
    with pytest.raises(BrokerError, match="keys are missing"):
        ETradeBroker(consumer_key="", consumer_secret="",
                     account_id_key="", token_path=tmp_path / "t.json")
    with pytest.raises(BrokerError, match="keys are missing"):
        ETradeBroker(consumer_key="k", consumer_secret="s",
                     account_id_key="", token_path=tmp_path / "t.json")


def test_sandbox_is_default_host(tmp_path):
    assert _broker(tmp_path).host == "https://apisb.etrade.com"
    prod = FakeETradeBroker(
        consumer_key="k", consumer_secret="s", account_id_key=ACCOUNT_KEY,
        sandbox=False, access_token="t", access_token_secret="s",
        token_path=tmp_path / "t.json")
    assert prod.host == "https://api.etrade.com"


def test_broker_refuses_without_token(tmp_path):
    broker = FakeETradeBroker(
        consumer_key="k", consumer_secret="s", account_id_key=ACCOUNT_KEY,
        token_path=tmp_path / "no-token.json")
    with pytest.raises(BrokerError, match="No E\\*TRADE access token"):
        broker.get_account()


def test_crypto_is_refused(tmp_path):
    broker = _broker(tmp_path)
    with pytest.raises(BrokerError, match="does not trade crypto"):
        broker.submit_bracket_buy(symbol="BTC-USD", notional_usd=5.00,
                                  take_profit_usd=109.00, stop_loss_usd=94.00)
    with pytest.raises(BrokerError, match="does not trade crypto"):
        broker.submit_bracket_buy(symbol="ETH-USD", notional_usd=5.00,
                                  take_profit_usd=109.00, stop_loss_usd=94.00)


def test_list_accounts(tmp_path):
    broker = _broker(tmp_path)
    accounts = broker.list_accounts()
    assert len(accounts) == 1
    assert accounts[0]["account_id_key"] == ACCOUNT_KEY
    assert accounts[0]["description"] == "INDIVIDUAL"
    assert accounts[0]["net_account_value"] == 5000.00


def test_get_account_prefers_realtime_value(tmp_path):
    broker = _broker(tmp_path)
    account = broker.get_account()
    assert account["portfolio_value"] == 5000.00
    assert account["cash"] == 250.00
    assert account["status"] == "ACTIVE"


def test_get_account_falls_back_without_realtime(tmp_path):
    broker = _broker(tmp_path)
    broker.balance_variant = "plain"
    account = broker.get_account()
    assert account["portfolio_value"] == 4200.00
    assert account["cash"] == 180.00


def test_get_positions_and_quote(tmp_path):
    broker = _broker(tmp_path)
    positions = broker.get_positions()
    assert positions == [{"symbol": "AAPL", "qty": 10.0,
                          "market_value": 1000.00, "price_paid": 95.00}]
    assert broker.get_position("AAPL")["qty"] == 10.0
    assert broker.get_position("MSFT") is None
    assert broker.get_quote("AAPL") == 100.00
    assert broker.get_quote("META") == 610.15


def test_get_clock_is_an_estimate(tmp_path):
    broker = _broker(tmp_path)
    clock = broker.get_clock()
    assert isinstance(clock["is_open"], bool)
    assert "no clock endpoint" in clock["source"]


# --- orders: entry + standalone stop -------------------------------------------

def test_bracket_buy_is_entry_plus_standalone_stop(tmp_path):
    broker = _broker(tmp_path)
    order = broker.submit_bracket_buy(
        symbol="AAPL", notional_usd=100.00,
        take_profit_usd=109.00, stop_loss_usd=94.00)
    assert order["status"] == "accepted"
    assert order["qty"] == 1  # $100 at $100/share = 1 whole share
    assert order["notional_usd"] == 100.00
    assert order["stop_order_id"]  # a stop order exists at the broker
    assert "VaultTec-managed" in order["take_profit_note"]
    # Call order: quote, preview, place, preview (stop), place (stop)
    kinds = [(c["method"], c["path"].split("/")[-1]) for c in broker.calls]
    assert kinds == [("GET", "AAPL.json"),
                     ("POST", "preview"), ("POST", "place"),
                     ("POST", "preview"), ("POST", "place")]
    entry_preview = broker.calls[1]["payload"]["PreviewOrderRequest"]
    entry = entry_preview["Order"][0]
    assert entry["priceType"] == "MARKET"
    assert entry["orderTerm"] == "GOOD_FOR_DAY"
    assert entry["Instrument"][0]["quantityType"] == "QUANTITY"
    assert entry["Instrument"][0]["quantity"] == 1
    assert entry["Instrument"][0]["orderAction"] == "BUY"
    stop_preview = broker.calls[3]["payload"]["PreviewOrderRequest"]
    stop = stop_preview["Order"][0]
    assert stop["priceType"] == "STOP"
    assert stop["orderTerm"] == "GOOD_UNTIL_CANCEL"
    assert stop["stopPrice"] == 94.00
    assert stop["Instrument"][0]["orderAction"] == "SELL"
    assert stop["Instrument"][0]["quantity"] == 1
    # Place calls carry the preview id and a <=20-char client order id
    for call in (broker.calls[2], broker.calls[4]):
        place = call["payload"]["PlaceOrderRequest"]
        assert place["PreviewIds"][0]["previewId"].startswith("PREVIEW-")
        assert len(place["clientOrderId"]) <= 20
        assert place["clientOrderId"].isalnum()


def test_bracket_buy_refuses_zero_whole_shares(tmp_path):
    broker = _broker(tmp_path)
    # $5 cannot buy 1 share of META at $610.15 — and the broker must
    # say so, not silently buy nothing or round up.
    with pytest.raises(BrokerError, match="buys 0 shares"):
        broker.submit_bracket_buy(symbol="META", notional_usd=5.00,
                                  take_profit_usd=665.07, stop_loss_usd=573.54)


def test_entry_placed_but_stop_failed_is_unprotected(tmp_path):
    broker = _broker(tmp_path)
    broker.fail_preview_number = 2  # the stop preview fails
    with pytest.raises(BrokerError) as exc:
        broker.submit_bracket_buy(symbol="AAPL", notional_usd=100.00,
                                  take_profit_usd=109.00, stop_loss_usd=94.00)
    assert "UNPROTECTED" in str(exc.value)
    assert "ENTRY PLACED" in str(exc.value)
    assert "1001" in str(exc.value)  # the entry order id, for hand fixing


def test_submit_sell_cancels_stop_first_and_sells_whole_position(tmp_path):
    broker = _broker(tmp_path)
    broker.submit_bracket_buy(symbol="AAPL", notional_usd=100.00,
                              take_profit_usd=109.00, stop_loss_usd=94.00)
    stop_id = broker._stop_orders["AAPL"]
    calls_before_sell = len(broker.calls)
    # The runner's record can hold a fractional quantity (Alpaca-style);
    # E*TRADE sells the whole position instead.
    order = broker.submit_sell(symbol="AAPL", quantity=0.0167)
    assert order["status"] == "accepted"
    assert order["qty"] == 10  # the whole position, not 0.0167 shares
    assert "AAPL" not in broker._stop_orders
    sell_calls = broker.calls[calls_before_sell:]
    assert sell_calls[0]["method"] == "PUT"
    assert sell_calls[0]["path"].endswith("/orders/cancel")
    assert sell_calls[0]["payload"] == {
        "CancelOrderRequest": {"orderId": int(stop_id)}}
    assert sell_calls[2]["payload"]["PreviewOrderRequest"]["Order"][0][
        "Instrument"][0]["quantity"] == 10


def test_submit_sell_with_no_position_refuses(tmp_path):
    broker = _broker(tmp_path)
    with pytest.raises(BrokerError, match="No E\\*TRADE position"):
        broker.submit_sell(symbol="MSFT", quantity=1.0)


def test_close_position_cancels_open_orders_then_sells(tmp_path):
    broker = _broker(tmp_path)
    result = broker.close_position("AAPL")
    assert result["status"] == "accepted"
    cancel_calls = [c for c in broker.calls
                    if c["path"].endswith("/orders/cancel")]
    # Only the AAPL order (777) is cancelled, not the MSFT one (888).
    assert len(cancel_calls) == 1
    assert cancel_calls[0]["payload"] == {
        "CancelOrderRequest": {"orderId": 777}}


# --- OAuth lifecycle -------------------------------------------------------------

def test_authorization_flow_saves_token(tmp_path):
    broker = _broker(tmp_path)
    broker.access_token = None
    broker.access_token_secret = None
    url = broker.begin_authorization()
    assert url.startswith("https://us.etrade.com/e/t/etws/authorize")
    assert "key=CONSUMER" in url
    assert "token=REQTOK" in url
    assert broker.complete_authorization("12345") is True
    assert broker.access_token == "ACCTOK"
    token_file = tmp_path / ".etrade-tokens.json"
    assert token_file.exists()
    saved = json.loads(token_file.read_text(encoding="utf-8"))
    assert saved["oauth_token"] == "ACCTOK"
    assert saved["oauth_token_secret"] == "ACCSEC"
    assert stat.S_IMODE(token_file.stat().st_mode) == 0o600


def test_token_file_is_reloaded_by_a_new_broker(tmp_path):
    broker = _broker(tmp_path)
    broker.access_token = None
    broker.access_token_secret = None
    broker.begin_authorization()
    broker.complete_authorization("12345")
    reloaded = FakeETradeBroker(
        consumer_key="CONSUMER", consumer_secret="SECRET",
        account_id_key=ACCOUNT_KEY, sandbox=True,
        token_path=tmp_path / ".etrade-tokens.json")
    assert reloaded.token_status()["has_token"] is True
    assert reloaded.access_token == "ACCTOK"


def test_complete_without_begin_refuses(tmp_path):
    broker = _broker(tmp_path)
    broker._request_token = None
    broker._request_token_secret = None
    with pytest.raises(BrokerError, match="begin_authorization"):
        broker.complete_authorization("12345")


def test_renew_access_token(tmp_path):
    broker = _broker(tmp_path)
    assert broker.renew_access_token() is True


# --- dry-run broker ---------------------------------------------------------------

def test_dry_run_records_entry_plus_stop(tmp_path):
    broker = ETradeDryRunBroker(prices={"AAPL": 100.00})
    order = broker.submit_bracket_buy(
        symbol="AAPL", notional_usd=500.00,
        take_profit_usd=109.00, stop_loss_usd=94.00)
    assert "NOT placed" in order["status"]
    assert order["qty"] == 5
    assert order["notional"] == "500.00"
    assert order["stop_order_id"].startswith("dry-run-stop-")
    assert "VaultTec-managed" in order["take_profit"]["note"]
    assert len(broker.orders) == 1


def test_dry_run_refuses_zero_shares_and_crypto():
    broker = ETradeDryRunBroker(prices={"META": 610.15})
    with pytest.raises(BrokerError, match="buys 0 shares"):
        broker.submit_bracket_buy(symbol="META", notional_usd=5.00,
                                  take_profit_usd=665.07, stop_loss_usd=573.54)
    with pytest.raises(BrokerError, match="does not trade crypto"):
        broker.submit_bracket_buy(symbol="BTC-USD", notional_usd=5.00,
                                  take_profit_usd=109.00, stop_loss_usd=94.00)


def test_dry_run_assumed_price_is_labelled():
    broker = ETradeDryRunBroker()
    order = broker.submit_bracket_buy(
        symbol="AAPL", notional_usd=500.00,
        take_profit_usd=109.00, stop_loss_usd=94.00)
    assert order["qty"] == 5  # $500 / assumed $100
    assert "assumed $100.00" in order["price_assumed"]


def test_dry_run_sell_and_account_shape():
    broker = ETradeDryRunBroker()
    account = broker.get_account()
    assert account["dry_run"] is True
    assert broker.get_positions() == []
    assert broker.get_position("AAPL") is None
    order = broker.submit_sell(symbol="AAPL", quantity=1.0)
    assert "NOT placed" in order["status"]
    assert broker.cancel_order("x")["status"] == "dry-run — NOT cancelled"
    assert broker.close_position("AAPL")["status"] == "dry-run — NOT closed"
