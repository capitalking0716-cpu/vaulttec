"""Private live-trading tests — stubs and fakes only, no network.

The real Alpaca API is never called here. The broker is faked by
subclassing ``AlpacaBroker`` and overriding ``_request``, and the
market-data provider is a stub returning fixed bars. Tests check
the guarantees that matter: live is locked off by default, keys
never come from code, bracket orders carry the stop and target,
small-capital sizing is honest, approval is required before
anything is placed, and the kill-switch stops everything.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.private_live import MAX_POSITION_PCT, STOP_PCT, TAKE_PCT
from vaulttec.private_live.broker import AlpacaBroker, DryRunBroker
from vaulttec.private_live.config import (
    LIVE_CONFIRMATION_TEXT,
    LiveTradingRefused,
    PrivateConfig,
    alpaca_symbol,
    load_config,
    require_live,
    vaulttec_symbol,
)
from vaulttec.private_live.runner import (
    _automation_opted_in,
    approve,
    load_state,
    scan,
)
from vaulttec.private_live.strategy import (
    build_proposal,
    size_position,
    wide6_stop_target,
)

RUN_DATE = date(2026, 11, 9)  # Monday; last completed stock bar Fri 2026-11-06


def _bars(dates, closes):
    rows = []
    prev = closes[0]
    for d, close in zip(dates, closes):
        rows.append({"date": pd.Timestamp(d), "open": prev,
                     "high": round(max(prev, close) * 1.002, 2),
                     "low": round(min(prev, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
        prev = close
    return pd.DataFrame(rows)


def _dip_history(end="2026-11-06", days=100):
    """Flat at 100, then a steady 1%/day fall for the last 15 bars:
    RSI collapses below 30 on the final bar, so the trigger fires."""
    dates = pd.bdate_range(end=end, periods=days)
    closes = []
    price = 100.0
    for i in range(days):
        if i >= days - 15:
            price *= 0.99
        closes.append(price)
    return _bars([str(d)[:10] for d in dates], closes)


class StubProvider:
    def __init__(self, frames):
        self.frames = frames

    def get_history(self, symbol, days=None):
        return self.frames[symbol].copy()


class FakeBroker(AlpacaBroker):
    """Records every request instead of calling Alpaca."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = []

    def _request(self, method, path, payload=None):
        self.calls.append({"method": method, "path": path, "payload": payload})
        if path == "/v2/account":
            return {"cash": "50.00", "portfolio_value": "50.00",
                    "buying_power": "50.00", "status": "ACTIVE"}
        if path == "/v2/positions":
            return []
        return {"id": f"fake-{len(self.calls)}", "status": "accepted"}


# --- live gate ------------------------------------------------------------

def test_live_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ALPACA_PAPER", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.paper is True
    assert cfg.is_live is False
    assert cfg.has_keys is False
    assert cfg.mode_label.startswith("DRY-RUN")


def test_require_live_refuses_and_names_missing_locks(tmp_path):
    cfg = PrivateConfig(paper=True, live_enabled_flag=False,
                        confirmation_present=False, private_dir=tmp_path)
    with pytest.raises(LiveTradingRefused) as exc:
        require_live(cfg)
    assert "VAULTTEC_LIVE_TRADING_ENABLED" in str(exc.value)
    assert "ALPACA_PAPER" in str(exc.value)
    assert "LIVE_CONFIRMATION" in str(exc.value)


def test_live_gate_opens_only_when_all_three_locks_open(tmp_path):
    (tmp_path / "LIVE_CONFIRMATION.txt").write_text(
        LIVE_CONFIRMATION_TEXT, encoding="utf-8")
    cfg = load_config(tmp_path)
    # env flags are off in this test process, so still closed
    assert cfg.is_live is False
    cfg2 = PrivateConfig(api_key="k", secret_key="s", paper=False,
                         live_enabled_flag=True, confirmation_present=True,
                         private_dir=tmp_path)
    assert cfg2.is_live is True
    require_live(cfg2)  # does not raise


def test_confirmation_file_with_wrong_text_does_not_open_gate(tmp_path):
    (tmp_path / "LIVE_CONFIRMATION.txt").write_text(
        "yes, go live", encoding="utf-8")
    cfg = load_config(tmp_path)
    assert cfg.confirmation_present is False


def test_symbol_mapping():
    assert alpaca_symbol("BTC-USD") == "BTC/USD"
    assert alpaca_symbol("ETH-USD") == "ETH/USD"
    assert alpaca_symbol("AAPL") == "AAPL"
    assert vaulttec_symbol("BTC/USD") == "BTC-USD"
    assert vaulttec_symbol("AAPL") == "AAPL"


# --- broker ----------------------------------------------------------------

def test_broker_refuses_without_keys():
    with pytest.raises(Exception, match="API keys are missing"):
        AlpacaBroker(api_key="", secret_key="")


def test_bracket_order_carries_stop_and_target_at_broker():
    broker = FakeBroker(api_key="key-id", secret_key="secret", paper=True)
    order = broker.submit_bracket_buy(symbol="AAPL", notional_usd=5.00,
                                      take_profit_usd=109.00, stop_loss_usd=94.00)
    assert order["status"] == "accepted"
    payload = broker.calls[-1]["payload"]
    assert payload["order_class"] == "bracket"
    assert payload["notional"] == "5.00"  # dollar amount, fractional
    assert payload["take_profit"]["limit_price"] == "109.00"
    assert payload["stop_loss"]["stop_price"] == "94.00"
    assert payload["type"] == "market"


def test_bracket_order_maps_crypto_symbol():
    broker = FakeBroker(api_key="key-id", secret_key="secret", paper=True)
    broker.submit_bracket_buy(symbol="BTC-USD", notional_usd=5.00,
                              take_profit_usd=70000.00, stop_loss_usd=60000.00)
    assert broker.calls[-1]["payload"]["symbol"] == "BTC/USD"


def test_dry_run_broker_records_but_places_nothing():
    broker = DryRunBroker()
    order = broker.submit_bracket_buy(symbol="AAPL", notional_usd=5.00,
                                      take_profit_usd=109.00, stop_loss_usd=94.00)
    assert "NOT placed" in order["status"]
    assert len(broker.orders) == 1


# --- sizing -----------------------------------------------------------------

def test_wide6_stop_target_is_exactly_1_5_to_1():
    stop, take = wide6_stop_target(100.00)
    assert stop == 94.00
    assert take == 109.00
    assert (take - 100.00) / (100.00 - stop) == pytest.approx(1.5)


def test_sizing_on_50_dollars():
    sizing = size_position(50.0, 100.0)
    assert sizing["notional_usd"] == 5.00  # 10% position cap
    assert sizing["risk_usd"] == 0.30  # 6% stop on $5
    assert sizing["target_usd"] == 0.45
    assert "position cap" in sizing["capped_by"]


def test_sizing_on_20_dollars():
    sizing = size_position(20.0, 100.0)
    assert sizing["notional_usd"] == 2.00
    assert sizing["risk_usd"] == 0.12
    assert sizing["target_usd"] == 0.18


def test_proposal_below_minimum_notional_is_none():
    # $5 account -> $0.50 position, below Alpaca's ~$1 minimum
    assert build_proposal("AAPL", "rsi", 100.0, 5.0, "PROP-1") is None


def test_proposal_carries_risk_and_target_in_dollars():
    proposal = build_proposal("AAPL", "rsi", 100.0, 50.0, "PROP-1")
    assert proposal is not None
    assert proposal.notional_usd == 5.00
    assert proposal.risk_usd == 0.30
    assert proposal.take_profit == 109.00
    assert proposal.stop_loss == 94.00


# --- runner: approval first, kill-switch, automation opt-in ----------------

def _clean_env(monkeypatch):
    for key in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY",
                "VAULTTEC_LIVE_TRADING_ENABLED", "ALPACA_PAPER"):
        monkeypatch.delenv(key, raising=False)


def test_scan_proposes_but_places_nothing_without_approval(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    summary = scan(run_date=RUN_DATE, private_dir=tmp_path,
                   symbols=["AAPL"], provider=provider, account_value=50.0)
    assert summary["status"] == "ok"
    assert summary["proposals"] == ["PROP-2026-11-09-AAPL"]
    assert summary["placed"] == []
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 0
    assert state["proposals"][0]["status"] == "pending"
    assert state["proposals"][0]["notional_usd"] == 5.00


def test_approve_places_the_proposal_via_dry_run_broker(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
         provider=provider, account_value=50.0)
    result = approve(proposal_id="PROP-2026-11-09-AAPL", private_dir=tmp_path)
    assert result["status"] == "ok"
    assert result["placed"] == ["PROP-2026-11-09-AAPL"]
    state = load_state(tmp_path)
    assert len(state["open_positions"]) == 1
    assert state["open_positions"][0]["symbol"] == "AAPL"
    assert state["proposals"] == []


def test_scan_with_auto_but_no_optin_places_nothing(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    summary = scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
                   provider=provider, account_value=50.0, auto=True)
    assert summary["auto_enabled"] is False
    assert summary["placed"] == []
    assert summary["proposals"] == ["PROP-2026-11-09-AAPL"]


def test_scan_with_auto_and_optin_places(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    (tmp_path / "automation-enabled.json").write_text(
        '{"enabled": true, "confirmed_by": "Neko"}', encoding="utf-8")
    assert _automation_opted_in(tmp_path) is True
    provider = StubProvider({"AAPL": _dip_history()})
    summary = scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
                   provider=provider, account_value=50.0, auto=True)
    assert summary["auto_enabled"] is True
    assert summary["placed"] == ["PROP-2026-11-09-AAPL"]


def test_kill_switch_stops_scan_and_approve(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    (tmp_path / "STOP").write_text("stopped", encoding="utf-8")
    provider = StubProvider({"AAPL": _dip_history()})
    summary = scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
                   provider=provider, account_value=50.0)
    assert summary["status"] == "stopped"
    assert summary["proposals"] == []
    result = approve(proposal_id="PROP-2026-11-09-AAPL", private_dir=tmp_path)
    assert result["status"] == "stopped"


def test_scan_skips_symbol_already_held(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
         provider=provider, account_value=50.0)
    approve(proposal_id="PROP-2026-11-09-AAPL", private_dir=tmp_path)
    # Second scan: already holding AAPL, so no new proposal.
    summary = scan(run_date=RUN_DATE, private_dir=tmp_path, symbols=["AAPL"],
                   provider=provider, account_value=50.0)
    assert summary["proposals"] == []
