"""Phone-panel tests — logic only, no Streamlit, no network.

The panel module (vaulttec/private_live/panel.py) is the testable
logic behind the "My Private Trading" section in app.py. Tests
use the same stub provider / dry-run broker as test_private_live.py:
no real Alpaca call, no real market fetch, no keys.
"""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_private_live import RUN_DATE, StubProvider, _clean_env, _dip_history

from vaulttec.private_live.panel import (
    activate_kill_switch,
    approve_proposal,
    check_live_gate,
    clear_kill_switch,
    get_private_status,
    login_password_set,
    missing_live_locks,
    reject_proposal,
    run_private_scan,
)


# Proposal IDs are stamped with the real current date, so the expected ID
# is built from today — a hardcoded date goes stale overnight.
PROP_AAPL = f"PROP-{date.today().isoformat()}-AAPL"


def test_login_password_gate():
    assert login_password_set("a-password") is True
    assert login_password_set("") is False
    assert login_password_set(None) is False


def test_status_is_dry_run_and_live_locked_by_default(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    status = get_private_status(tmp_path)
    assert status["mode"].startswith("DRY-RUN")
    assert status["is_live"] is False
    assert status["live_locked"] is True
    assert status["has_keys"] is False
    assert status["kill_switch_on"] is False
    assert status["pending_count"] == 0
    assert status["open_positions_count"] == 0
    assert status["realised_pnl_usd"] is None  # never invented
    assert "ALPACA_API_KEY" not in str(status)
    assert "ALPACA_SECRET_KEY" not in str(status)


def test_missing_live_locks_names_all_three(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    missing = missing_live_locks(tmp_path)
    assert len(missing) == 3
    assert any("VAULTTEC_LIVE_TRADING_ENABLED" in m for m in missing)
    assert any("ALPACA_PAPER" in m for m in missing)
    assert any("LIVE_CONFIRMATION" in m for m in missing)
    gate = check_live_gate(tmp_path)
    assert gate["live_open"] is False
    assert gate["missing_locks"] == missing


def test_scan_via_panel_proposes_but_places_nothing(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_private_scan(account_value=50.0, private_dir=tmp_path,
                               provider=provider)
    assert summary["status"] == "ok"
    assert summary["proposals"] == [PROP_AAPL]
    assert summary["placed"] == []
    status = get_private_status(tmp_path)
    assert status["pending_count"] == 1
    prop = status["pending_proposals"][0]
    assert prop["symbol"] == "AAPL"
    assert prop["entry_price"] > 0
    assert prop["stop_loss"] < prop["entry_price"] < prop["take_profit"]
    assert prop["risk_usd"] == 0.30
    assert prop["target_usd"] == 0.45


def test_approve_via_panel_places_dry_run_only(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    run_private_scan(account_value=50.0, private_dir=tmp_path, provider=provider)
    result = approve_proposal(PROP_AAPL, tmp_path)
    assert result["status"] == "ok"
    assert result["placed"] == [PROP_AAPL]
    assert "DRY-RUN" in result["mode"]
    status = get_private_status(tmp_path)
    assert status["pending_count"] == 0
    assert status["open_positions_count"] == 1


def test_reject_via_panel_places_nothing(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    provider = StubProvider({"AAPL": _dip_history()})
    run_private_scan(account_value=50.0, private_dir=tmp_path, provider=provider)
    assert reject_proposal(PROP_AAPL, tmp_path) is True
    assert reject_proposal(PROP_AAPL, tmp_path) is False
    status = get_private_status(tmp_path)
    assert status["pending_count"] == 0
    assert status["open_positions_count"] == 0


def test_kill_switch_via_panel_blocks_scan_and_approve(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    activate_kill_switch(tmp_path)
    assert get_private_status(tmp_path)["kill_switch_on"] is True
    provider = StubProvider({"AAPL": _dip_history()})
    summary = run_private_scan(account_value=50.0, private_dir=tmp_path,
                               provider=provider)
    assert summary["status"] == "stopped"
    result = approve_proposal(PROP_AAPL, tmp_path)
    assert result["status"] == "stopped"
    assert clear_kill_switch(tmp_path) is True
    assert clear_kill_switch(tmp_path) is False
    assert get_private_status(tmp_path)["kill_switch_on"] is False
    # After clearing, a scan works again.
    summary = run_private_scan(account_value=50.0, private_dir=tmp_path,
                               provider=provider)
    assert summary["status"] == "ok"
    assert summary["proposals"] == [PROP_AAPL]
