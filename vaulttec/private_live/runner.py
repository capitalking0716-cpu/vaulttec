"""Private-live runner — Neko only. Paper first, live locked off.

Commands (run from the ``vaulttec/`` folder, in the venv)::

    python -m vaulttec.private_live.runner scan
        Fetch the latest completed bar per symbol, check the
        wide-6 triggers, and write PROPOSALS — nothing is placed.
        This is the default, approval-first mode.
    python -m vaulttec.private_live.runner scan --auto
        Same scan, but proposals are placed immediately — ONLY if
        supervised automation has been explicitly opted into
        (``private_live/automation-enabled.json`` exists, see
        RUNBOOK.md). Without that file, --auto behaves like scan.
    python -m vaulttec.private_live.runner approve --id PROP-20261109-001
        Place one pending proposal as a bracket order at the broker.
    python -m vaulttec.private_live.runner approve-all
        Place every pending proposal (each still risk-checked).
    python -m vaulttec.private_live.runner status
        Account, open positions, pending proposals, P&L so far.
    python -m vaulttec.private_live.runner kill
        Create the STOP file: scan/approve refuse until it is deleted.

Modes, in order of safety:
- DRY-RUN (no Alpaca keys): signals and proposals only, orders
  are recorded as "dry-run — NOT placed". The logic can be tested
  with no broker account at all.
- PAPER (keys set, ALPACA_PAPER=true): real Alpaca paper account,
  fake money, real broker mechanics (fills, bracket legs).
- LIVE (all three live locks open): real money. ``require_live``
  is called before any live order is placed; a missing lock
  raises and nothing is placed.

Every run is logged to ``private_live/trades.jsonl`` (append-only)
and the report ``private_live/report.md`` is regenerated. Keys
are never written to any log or report.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ..config.settings import RISK_PROFILES
from ..live_paper_trading import LiveYFinanceProvider, _completed_bars
from ..market.data import SCAN_UNIVERSE
from ..risk import RiskEngine
from . import HORIZON_BARS, PRIVATE_ONLY_BANNER, RISK_REWARD, STOP_PCT, TAKE_PCT
from .broker import AlpacaBroker, BrokerError, DryRunBroker
from .config import (LiveTradingRefused, PrivateConfig, default_private_dir,
                     load_config, require_live)
from .strategy import (MIN_NOTIONAL_USD, Proposal, build_proposal,
                       check_proposal_with_risk, scan_history)

NY_TZ = ZoneInfo("America/New_York")
STATE_FILE = "state.json"
PROPOSALS_FILE = "proposals.json"
LOG_FILE = "trades.jsonl"
REPORT_FILE = "report.md"
STOP_FILE = "STOP"
AUTOMATION_FILE = "automation-enabled.json"
RISK_PROFILE = "balanced"


def _is_stopped(private_dir: Path) -> bool:
    return (private_dir / STOP_FILE).exists()


def _automation_opted_in(private_dir: Path) -> bool:
    path = private_dir / AUTOMATION_FILE
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return bool(data.get("enabled")) and data.get("confirmed_by") == "Neko"
    except (OSError, ValueError):
        return False


def fresh_state() -> dict:
    return {
        "version": 1,
        "private_only": True,
        "strategy": "wide-6-private",
        "stop_pct": STOP_PCT,
        "take_pct": TAKE_PCT,
        "horizon_bars": HORIZON_BARS,
        "risk_profile": RISK_PROFILE,
        "mode": "dry-run",
        "account_value_usd": 0.0,
        "open_positions": [],
        "closed_trades": [],
        "proposals": [],
        "blocked_count": 0,
        "fetch_failures": {},
        "runs": 0,
        "last_run_date": None,
    }


def load_state(private_dir: Path) -> dict:
    path = private_dir / STATE_FILE
    if not path.exists():
        return fresh_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    base = fresh_state()
    base.update(state)
    return base


def save_state(private_dir: Path, state: dict) -> None:
    path = private_dir / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def append_log(private_dir: Path, event: dict) -> None:
    path = private_dir / LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


def save_proposals(private_dir: Path, proposals: list[dict]) -> None:
    path = private_dir / PROPOSALS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposals, indent=2), encoding="utf-8")


def load_proposals(private_dir: Path) -> list[dict]:
    path = private_dir / PROPOSALS_FILE
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return []


def make_broker(config: PrivateConfig):
    """Alpaca broker when keys exist, DryRunBroker otherwise."""
    if config.has_keys:
        return AlpacaBroker(config.api_key, config.secret_key, paper=config.paper)
    return DryRunBroker()


def make_risk_engine() -> RiskEngine:
    limits = RISK_PROFILES[RISK_PROFILE]
    return RiskEngine(
        max_position_pct=limits["max_position_pct"],
        max_concentration_pct=limits["max_concentration_pct"],
        max_exposure_pct=limits["max_exposure_pct"],
        daily_loss_limit_pct=limits["daily_loss_limit_pct"],
        min_risk_reward=limits["min_risk_reward"],
    )


def _account_value(broker, state: dict) -> float:
    """Account value in dollars. Dry-run has no account, so the
    runner uses the state value (set by --account-value, default
    $50) purely to size proposals — it is labelled as an
    assumption in the report, never presented as a real balance."""
    try:
        account = broker.get_account()
        value = float(account.get("portfolio_value") or 0.0)
        if value > 0:
            return value
    except (BrokerError, ValueError, TypeError):
        pass
    return float(state.get("account_value_usd") or 0.0)


def scan(run_date: date | None = None, private_dir: Path | None = None,
         symbols: list[str] | None = None, auto: bool = False,
         account_value: float | None = None, provider=None) -> dict:
    """One daily scan: proposals only, unless automation is opted in.

    Only the latest completed bar per symbol is scanned (a run
    after the close, or the next morning before the open). Time
    exits are checked first: any tracked position held 10+ bars is
    listed as an exit proposal — in approval mode it waits for
    Neko, in automation mode it is sold at the broker.
    """
    run_date = run_date or datetime.now(NY_TZ).date()
    run_id = run_date.isoformat()
    pdir = Path(private_dir) if private_dir else default_private_dir()
    pdir.mkdir(parents=True, exist_ok=True)
    if _is_stopped(pdir):
        return {"run_date": run_date.isoformat(), "status": "stopped",
                "reason": "kill-switch active (private_live/STOP exists)",
                "proposals": [], "placed": []}
    config = load_config(pdir)
    state = load_state(pdir)
    state["last_run_date"] = run_id
    if account_value is not None:
        state["account_value_usd"] = float(account_value)
    broker = make_broker(config)
    risk = make_risk_engine()
    if provider is None:
        provider = LiveYFinanceProvider(run_date)
    symbols = symbols or list(SCAN_UNIVERSE)
    mode = config.mode_label
    if config.is_live:
        mode = "LIVE — real money"
    state["mode"] = mode

    account_usd = _account_value(broker, state)
    # Dry-run with no account value set: assume $50 so proposals
    # can be sized and shown — labelled as an assumption.
    if account_usd <= 0:
        account_usd = 50.0
        state["account_value_usd"] = account_usd
        account_assumed = True
    else:
        account_assumed = False
        state["account_value_usd"] = account_usd

    auto_enabled = auto and _automation_opted_in(pdir)
    proposals: list[dict] = []
    placed: list[dict] = []
    failed: dict[str, str] = {}

    # 1) Time exits for tracked positions, oldest first.
    for pos in list(state["open_positions"]):
        pos["bars_held"] = int(pos.get("bars_held", 0)) + 1
        if pos["bars_held"] >= HORIZON_BARS:
            exit_prop = {
                "proposal_id": f"EXIT-{run_id}-{pos['symbol']}",
                "kind": "exit", "symbol": pos["symbol"],
                "entry_date": pos.get("entry_date"),
                "bars_held": pos["bars_held"],
                "reason": f"10-day time exit ({HORIZON_BARS} bars held)",
                "status": "pending",
            }
            proposals.append(exit_prop)
            if auto_enabled:
                placed.append(_place_exit(broker, config, pdir, state, exit_prop))
            else:
                append_log(pdir, {"date": run_id, "event": "exit_proposed",
                                  "private_only": True, **exit_prop})

    # 2) Entry scan, one symbol at a time.
    for symbol in symbols:
        if any(p["symbol"] == symbol for p in state["open_positions"]):
            continue  # already holding this symbol — no second position
        try:
            history = provider.get_history(symbol)
        except Exception as exc:  # noqa: BLE001 — record, never invent data
            failed[symbol] = f"{type(exc).__name__}: {exc}"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            continue
        if history is None or history.empty or "close" not in history.columns:
            failed[symbol] = "empty history returned"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            continue
        completed = _completed_bars(history, run_date)
        if completed.empty:
            continue
        history_to_bar = completed  # completed bars only — no look-ahead
        strategy = scan_history(history_to_bar)
        if strategy is None:
            continue
        entry = float(completed["close"].iloc[-1])
        proposal_id = f"PROP-{run_id}-{symbol}"
        proposal = build_proposal(symbol, strategy, entry, account_usd,
                                  proposal_id, risk)
        if proposal is None:
            append_log(pdir, {"date": run_id, "event": "trade_skipped",
                              "symbol": symbol, "strategy": strategy,
                              "reason": f"sized position below the "
                                        f"${MIN_NOTIONAL_USD:.2f} minimum notional",
                              "private_only": True})
            continue
        allowed, reasons = check_proposal_with_risk(
            proposal, risk, portfolio_value_usd=account_usd,
            current_exposure_usd=sum(
                p.get("notional_usd", 0.0) for p in state["open_positions"]))
        record = {
            "proposal_id": proposal.proposal_id, "kind": "entry",
            "symbol": proposal.symbol, "strategy": proposal.strategy,
            "entry_price": proposal.entry_price,
            "stop_loss": proposal.stop_loss,
            "take_profit": proposal.take_profit,
            "notional_usd": proposal.notional_usd,
            "quantity": proposal.quantity,
            "risk_usd": proposal.risk_usd, "target_usd": proposal.target_usd,
            "risk_reward": proposal.risk_reward,
            "reason": proposal.reason, "status": "pending",
        }
        if not allowed:
            record["status"] = "blocked"
            record["blocked_reasons"] = reasons
            state["blocked_count"] = state.get("blocked_count", 0) + 1
            append_log(pdir, {"date": run_id, "event": "trade_blocked",
                              "private_only": True, **record})
        else:
            proposals.append(record)
            append_log(pdir, {"date": run_id, "event": "trade_proposed",
                              "private_only": True, **record})
            if auto_enabled:
                placed.append(_place_entry(broker, config, pdir, state, record))

    state["proposals"] = [p for p in state.get("proposals", [])
                          if p.get("status") == "pending"] + proposals
    state["runs"] = int(state.get("runs", 0)) + 1
    state["last_run_date"] = run_id
    save_state(pdir, state)
    save_proposals(pdir, state["proposals"])
    save_report(pdir, state)
    summary = {
        "run_date": run_id, "status": "ok", "mode": mode,
        "account_value_usd": account_usd,
        "account_value_assumed": account_assumed,
        "proposals": [p["proposal_id"] for p in proposals],
        "placed": [p.get("proposal_id") for p in placed],
        "auto_enabled": auto_enabled,
        "failed_symbols": failed,
    }
    append_log(pdir, {"date": run_id, "event": "run_summary",
                      "private_only": True, **summary})
    return summary


def _place_entry(broker, config: PrivateConfig, pdir: Path, state: dict,
                 record: dict) -> dict:
    """Place one approved entry proposal as a bracket order."""
    if not config.paper:
        require_live(config)  # live gate — raises, nothing is placed
    try:
        order = broker.submit_bracket_buy(
            symbol=record["symbol"], notional_usd=record["notional_usd"],
            take_profit_usd=record["take_profit"],
            stop_loss_usd=record["stop_loss"])
    except (BrokerError, LiveTradingRefused) as exc:
        # LiveTradingRefused is the safety gate working: nothing was
        # placed, and the refusal is logged with the reason.
        record["status"] = "failed"
        record["error"] = str(exc)
        append_log(pdir, {"date": state.get("last_run_date"), "event": "order_failed",
                          "private_only": True, **record})
        return record
    record["status"] = "placed"
    record["broker_order_id"] = order.get("id")
    record["broker_status"] = order.get("status")
    state["open_positions"].append({
        "symbol": record["symbol"], "strategy": record["strategy"],
        "entry_date": state.get("last_run_date"),
        "entry_price": record["entry_price"],
        "quantity": record["quantity"],
        "notional_usd": record["notional_usd"],
        "stop_loss": record["stop_loss"],
        "take_profit": record["take_profit"],
        "broker_order_id": order.get("id"),
        "bars_held": 0,
    })
    append_log(pdir, {"date": state.get("last_run_date"), "event": "trade_placed",
                      "private_only": True, **record})
    return record


def _place_exit(broker, config: PrivateConfig, pdir: Path, state: dict,
                record: dict) -> dict:
    """Sell a tracked position at market (10-day time exit)."""
    if not config.paper:
        require_live(config)
    pos = next((p for p in state["open_positions"]
                if p["symbol"] == record["symbol"]), None)
    if pos is None:
        record["status"] = "failed"
        record["error"] = "no tracked position to exit"
        return record
    try:
        order = broker.submit_sell(symbol=record["symbol"],
                                   quantity=float(pos["quantity"]))
    except (BrokerError, LiveTradingRefused) as exc:
        record["status"] = "failed"
        record["error"] = str(exc)
        return record
    record["status"] = "placed"
    record["broker_order_id"] = order.get("id")
    state["open_positions"] = [p for p in state["open_positions"]
                               if p["symbol"] != record["symbol"]]
    state["closed_trades"].append({
        "symbol": record["symbol"], "entry_date": pos.get("entry_date"),
        "exit_date": state.get("last_run_date"),
        "exit_reason": record["reason"], "quantity": pos["quantity"],
        "entry_price": pos.get("entry_price"),
    })
    append_log(pdir, {"date": state.get("last_run_date"), "event": "exit_placed",
                      "private_only": True, **record})
    return record


def approve(proposal_id: str | None = None, approve_all: bool = False,
            private_dir: Path | None = None) -> dict:
    """Place pending proposal(s) after Neko's explicit approval."""
    pdir = Path(private_dir) if private_dir else default_private_dir()
    if _is_stopped(pdir):
        return {"status": "stopped",
                "reason": "kill-switch active (private_live/STOP exists)",
                "placed": []}
    config = load_config(pdir)
    state = load_state(pdir)
    broker = make_broker(config)
    pending = [p for p in state.get("proposals", []) if p.get("status") == "pending"]
    if proposal_id:
        pending = [p for p in pending if p["proposal_id"] == proposal_id]
    if not pending:
        return {"status": "nothing_pending", "placed": []}
    if not approve_all and len(pending) > 1 and proposal_id is None:
        return {"status": "needs_choice",
                "reason": "more than one proposal is pending — approve one by id, or use approve-all",
                "pending": [p["proposal_id"] for p in pending]}
    placed = []
    for record in pending:
        if record.get("kind") == "exit":
            placed.append(_place_exit(broker, config, pdir, state, record))
        else:
            placed.append(_place_entry(broker, config, pdir, state, record))
    state["proposals"] = [p for p in state.get("proposals", [])
                          if p.get("status") == "pending"]
    save_state(pdir, state)
    save_proposals(pdir, state["proposals"])
    save_report(pdir, state)
    return {"status": "ok", "mode": config.mode_label,
            "placed": [p.get("proposal_id") for p in placed
                       if p.get("status") == "placed"],
            "failed": [p for p in placed if p.get("status") != "placed"]}


def compute_summary(state: dict) -> dict:
    closed = state.get("closed_trades", [])
    return {
        "mode": state.get("mode", "dry-run"),
        "strategy": state.get("strategy"),
        "runs": state.get("runs", 0),
        "last_run_date": state.get("last_run_date"),
        "account_value_usd": state.get("account_value_usd", 0.0),
        "open_positions": len(state.get("open_positions", [])),
        "closed_trades": len(closed),
        "pending_proposals": len([p for p in state.get("proposals", [])
                                  if p.get("status") == "pending"]),
        "blocked_count": state.get("blocked_count", 0),
        "fetch_failures": state.get("fetch_failures", {}),
    }


def render_report(state: dict) -> str:
    s = compute_summary(state)
    lines = [
        "# VaultTec PRIVATE — Neko only (paper first, live locked off)",
        "",
        f"> **{PRIVATE_ONLY_BANNER}**",
        "",
        f"- Mode: **{s['mode']}**",
        "- Strategy: wide-6 — 6% stop / 9% target (1.5:1), 10-bar time "
        "exit, RSI + Bollinger mean-reversion, long-only.",
        f"- Runs: {s['runs']} — last run: {s['last_run_date'] or 'never'}",
        f"- Account value: ${s['account_value_usd']:,.2f} "
        "(assumed $50 in dry-run mode unless --account-value is given)",
        f"- Open positions: {s['open_positions']} — closed trades: "
        f"{s['closed_trades']} — pending proposals: {s['pending_proposals']} "
        f"— blocked by risk: {s['blocked_count']}",
        f"- Fetch failures: {s['fetch_failures'] or 'none'}",
        "",
    ]
    if state.get("open_positions"):
        lines += ["## Open positions", "",
                  "| Symbol | Strategy | Entry | Qty | Stop | Target | Bars held |",
                  "|---|---|---:|---:|---:|---:|---:|"]
        for p in state["open_positions"]:
            lines.append(f"| {p['symbol']} | {p['strategy']} | "
                         f"${p['entry_price']:,.2f} ({p.get('entry_date')}) | "
                         f"{p['quantity']} | ${p['stop_loss']:,.2f} | "
                         f"${p['take_profit']:,.2f} | {p['bars_held']} |")
        lines.append("")
    pending = [p for p in state.get("proposals", []) if p.get("status") == "pending"]
    if pending:
        lines += ["## Pending proposals (approve before anything is placed)", ""]
        for p in pending:
            if p.get("kind") == "exit":
                lines.append(f"- **{p['proposal_id']}** — EXIT {p['symbol']}: {p['reason']}")
            else:
                lines.append(
                    f"- **{p['proposal_id']}** — BUY {p['symbol']} "
                    f"({p['strategy']}) @ ${p['entry_price']:,.2f} — "
                    f"${p['notional_usd']:,.2f} notional, stop "
                    f"${p['stop_loss']:,.2f}, target ${p['take_profit']:,.2f}, "
                    f"risk ${p['risk_usd']:,.2f} / target ${p['target_usd']:,.2f}. "
                    f"{p.get('reason', '')}")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        "This module trades Neko's own money only, paper first. The "
        "wide-6 rules held up on fresh past windows (RSI +$1,226.24 "
        "and Bollinger +$1,043.47 pooled fresh, Phase 4d) and the live "
        "paper run is only on Day 1 — 3 trades open, 0 closed, $0.00 "
        "realised. That is promising, not proven. A $20–$50 account "
        "risks about $0.12–$0.30 per trade and targets about "
        "$0.18–$0.45 — it will not fund attorney fees quickly. Do "
        "not scale up on the basis of backtests alone.",
        "",
    ]
    return "\n".join(lines)


def save_report(private_dir: Path, state: dict) -> Path:
    path = Path(private_dir) / REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(state), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VaultTec PRIVATE live trading — Neko only. "
                    "Paper first; live is locked off by default.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_scan = sub.add_parser("scan", help="scan for proposals (nothing placed)")
    p_scan.add_argument("--date", default=None, help="run date YYYY-MM-DD")
    p_scan.add_argument("--auto", action="store_true",
                        help="place proposals immediately — only works with automation opt-in")
    p_scan.add_argument("--account-value", type=float, default=None,
                        help="account value in USD for sizing (dry-run default $50)")
    p_scan.add_argument("--state-dir", default=None)
    p_approve = sub.add_parser("approve", help="approve and place one proposal")
    p_approve.add_argument("--id", required=True, help="proposal id, e.g. PROP-2026-11-09-AAPL")
    p_approve.add_argument("--state-dir", default=None)
    p_all = sub.add_parser("approve-all", help="approve and place all pending proposals")
    p_all.add_argument("--state-dir", default=None)
    p_status = sub.add_parser("status", help="show account, positions, proposals")
    p_status.add_argument("--state-dir", default=None)
    p_kill = sub.add_parser("kill", help="create the STOP file — nothing trades until it is deleted")
    p_kill.add_argument("--state-dir", default=None)
    args = parser.parse_args(argv)
    pdir = Path(getattr(args, "state_dir", None)) if getattr(args, "state_dir", None) else default_private_dir()

    if args.command == "kill":
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / STOP_FILE).write_text(
            "STOPPED by Neko — delete this file to resume private trading.\n",
            encoding="utf-8")
        print("PRIVATE kill-switch ON — scan/approve will refuse until "
              "private_live/STOP is deleted.")
        return 0
    if args.command == "status":
        state = load_state(pdir)
        print(render_report(state))
        return 0
    if args.command == "approve":
        result = approve(proposal_id=args.id, private_dir=pdir)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ok" else 2
    if args.command == "approve-all":
        result = approve(approve_all=True, private_dir=pdir)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "ok" else 2
    # scan
    run_date = date.fromisoformat(args.date) if args.date else None
    summary = scan(run_date=run_date, private_dir=pdir, auto=args.auto,
                   account_value=args.account_value)
    print(f"PRIVATE — {summary['status']} — mode: {summary.get('mode', '')}")
    print(f"Proposals: {summary.get('proposals') or 'none'}")
    print(f"Placed: {summary.get('placed') or 'none'}")
    if summary.get("failed_symbols"):
        print(f"Fetch failures: {summary['failed_symbols']}")
    print(f"Report: {pdir / REPORT_FILE}")
    return 0 if summary["status"] in ("ok", "stopped") else 2


if __name__ == "__main__":
    sys.exit(main())
