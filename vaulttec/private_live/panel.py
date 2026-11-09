"""Phone panel logic for Neko's PRIVATE trading — no Streamlit here.

This module is the testable logic behind the "My Private Trading"
section in ``app.py``. It never imports Streamlit, never touches
the network itself (the runner's provider does the fetching, and
tests pass a stub provider), and never places an order without
Neko tapping Approve on a specific proposal.

Security rules enforced here:
- The panel is only shown in the app when a login password is set
  (``VAULTTEC_LOGIN_PASSWORD``). See ``login_password_set``.
- Live trading is never enabled from the UI: ``missing_live_locks``
  names every closed lock, and ``approve`` goes through the
  runner, which calls ``require_live`` before any live order.
- No API key is ever returned by any function in this module.
"""
from __future__ import annotations

from pathlib import Path

from . import PRIVATE_ONLY_BANNER
from .config import load_config
from .runner import (
    _is_stopped,
    append_log,
    approve as _runner_approve,
    compute_summary,
    load_state,
    save_proposals,
    save_state,
    scan as _runner_scan,
)


def login_password_set(login_password: str | None) -> bool:
    """True only when a VaultTec login password is configured.

    The app's login gate is off until ``VAULTTEC_LOGIN_PASSWORD``
    is set in Streamlit Secrets or the environment. The private
    panel stays hidden until it is set — a password-less app must
    never show Neko's private proposals or allow approvals.
    """
    return bool(login_password)


def missing_live_locks(private_dir: Path | None = None) -> list[str]:
    """Every live-gate lock that is still closed, in plain words.

    Empty list means all three locks are open (live is possible).
    A non-empty list is the exact reason live is refused.
    """
    config = load_config(private_dir)
    missing: list[str] = []
    if not config.live_enabled_flag:
        missing.append("VAULTTEC_LIVE_TRADING_ENABLED=true is not set")
    if config.paper:
        missing.append("ALPACA_PAPER is not false (paper is the default)")
    if not config.confirmation_present:
        missing.append(
            "private_live/LIVE_CONFIRMATION.txt is missing or does "
            "not contain the exact confirmation text"
        )
    return missing


def get_private_status(private_dir: Path | None = None) -> dict:
    """Everything the phone panel needs to draw its status card.

    No broker call, no network, no keys returned. Realised P&L is
    not tracked in the runner's closed-trade records, so it is
    reported as unknown rather than invented.
    """
    config = load_config(private_dir)
    pdir = state_dir_path(private_dir)
    state = load_state(pdir)
    summary = compute_summary(state)
    return {
        "private_only_banner": PRIVATE_ONLY_BANNER,
        "mode": config.mode_label,
        "is_live": config.is_live,
        "has_keys": config.has_keys,
        "live_locked": not config.is_live,
        "missing_live_locks": missing_live_locks(private_dir),
        "kill_switch_on": _is_stopped(state_dir_path(private_dir)),
        "account_value_usd": summary["account_value_usd"],
        "open_positions": state.get("open_positions", []),
        "open_positions_count": summary["open_positions"],
        "closed_trades": summary["closed_trades"],
        "pending_proposals": [
            p for p in state.get("proposals", []) if p.get("status") == "pending"
        ],
        "pending_count": summary["pending_proposals"],
        "blocked_count": summary["blocked_count"],
        "fetch_failures": summary["fetch_failures"],
        "runs": summary["runs"],
        "last_run_date": summary["last_run_date"],
        "realised_pnl_usd": None,  # not tracked in closed-trade records
    }


def state_dir_path(private_dir: Path | None = None) -> Path:
    from .config import default_private_dir

    return Path(private_dir) if private_dir else default_private_dir()


def run_private_scan(account_value: float | None = None,
                     private_dir: Path | None = None,
                     provider=None) -> dict:
    """Run one private scan: proposals only, nothing placed.

    Approval-first: even in automation mode the runner only places
    when the automation opt-in file exists. ``provider`` is only
    used by tests (a stub); in the app it defaults to the real
    delayed-price provider.
    """
    kwargs: dict = {"account_value": account_value}
    if private_dir is not None:
        kwargs["private_dir"] = private_dir
    if provider is not None:
        kwargs["provider"] = provider
    return _runner_scan(**kwargs)


def approve_proposal(proposal_id: str,
                     private_dir: Path | None = None) -> dict:
    """Place one pending proposal after Neko tapped Approve.

    Goes through the runner, which risk-checks the trade and calls
    ``require_live`` before any live order. In dry-run / paper
    mode no real money moves.
    """
    return _runner_approve(proposal_id=proposal_id, private_dir=private_dir)


def reject_proposal(proposal_id: str,
                    private_dir: Path | None = None) -> bool:
    """Reject (skip) one pending proposal. No order is placed.

    Returns True when a pending proposal with that id was removed.
    """
    pdir = state_dir_path(private_dir)
    state = load_state(pdir)
    pending = [p for p in state.get("proposals", []) if p.get("status") == "pending"]
    target = next((p for p in pending if p.get("proposal_id") == proposal_id), None)
    if target is None:
        return False
    state["proposals"] = [p for p in state.get("proposals", [])
                          if p.get("proposal_id") != proposal_id]
    save_state(pdir, state)
    save_proposals(pdir, state["proposals"])
    append_log(pdir, {"event": "proposal_rejected", "private_only": True,
                      "proposal_id": proposal_id, "symbol": target.get("symbol")})
    return True


def activate_kill_switch(private_dir: Path | None = None) -> Path:
    """Create private_live/STOP — scan and approve refuse until
    the file is deleted. Returns the STOP file path."""
    pdir = state_dir_path(private_dir)
    pdir.mkdir(parents=True, exist_ok=True)
    stop = pdir / "STOP"
    stop.write_text(
        "STOPPED by Neko — delete this file to resume private trading.\n",
        encoding="utf-8",
    )
    return stop


def clear_kill_switch(private_dir: Path | None = None) -> bool:
    """Delete private_live/STOP, resuming private trading.

    Returns True when a STOP file was removed.
    """
    pdir = state_dir_path(private_dir)
    stop = pdir / "STOP"
    if stop.exists():
        stop.unlink()
        return True
    return False


def check_live_gate(private_dir: Path | None = None) -> dict:
    """Plain-language live-gate check for the UI.

    Never enables live — it only reports whether the gate is open
    and, if not, exactly which locks are still closed.
    """
    missing = missing_live_locks(private_dir)
    return {"live_open": not missing, "missing_locks": missing}
