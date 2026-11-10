"""Ava's DAILY paper trading — one real day at a time, paper only.

The night of Nov 9–10 Ava practiced OUR strategy on old price
windows (FRESH-1/2/3): 262 trades, 61.8% win, +$46.90 on a $100
pot. That was history replayed. This module is the next step:
trade the same wide-6 rules (6% stop / 9% target, 1.5:1, 10-bar
time exit, RSI + Bollinger mean-reversion as the lead, MACD
trend-following as the complement, one shared $100 pot, balanced
profile, long-only) one day at a time, on delayed real prices as
they arrive — the same live flow as
``vaulttec.live_paper_trading`` (run once a day, process every
*completed* daily bar not yet processed, in order, no look-ahead),
but on Ava's own pot, with her evidence and her lessons.

Where things live
-----------------
- Resume state (virtual cash, open positions, last processed bar
  per symbol, run history): ``data/ava-daily/state.json`` — the
  same shape as ``live_paper/state.json``, starting cash $100.
  Cash and open positions are also derivable from the evidence
  log, so a state file can be cross-checked against it.
- Evidence (one record per trade event — placed, blocked, closed):
  appended to the existing ``data/ava-evidence.jsonl``, marked
  ``"run": "daily"`` with the run date and a trade id
  (``AVA-YYYY-MM-DD-SYMBOL``). The 262 historical-window records
  already in that file have no ``"run"`` key, so daily records
  are never mixed up with the old simulations.
- Lessons (one per closed trade): the existing
  ``data/ava-lessons.jsonl``, via ``learn_from_trade``.
- Report: ``data/ava-daily/ava-daily-report.md``, regenerated
  each run.

Hard rules (same as every phase before this one)
------------------------------------------------
- PAPER ONLY. No broker is ever contacted, no real money moves,
  no leverage, no options. ``assert_paper_only`` refuses to run
  if either live lock is on (``VAULTTEC_LIVE_TRADING_ENABLED`` is
  true or ``ALPACA_PAPER`` is false).
- Every trade keeps its stop-loss. The stop is never removed.
- A fetch failure is recorded, never replaced with sample data
  and never invented. If every symbol fails to fetch, the run is
  recorded as "not run — no data": no state change, no trades.
- Kill-switch: create ``data/ava-daily/STOP`` (or set ``enabled``
  to false in the state file) and the next run does nothing at
  all except log that it was stopped.
- Past performance does not guarantee future results. A good
  daily paper week still needs a compliance/legal review before
  real money is ever considered.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from ..analytics.mean_reversion import STRATEGIES
from ..analytics.signals import generate_signal
from ..analytics.trend_and_stress import trend_trigger
from ..config.settings import RISK_PROFILES
from ..db.models import PaperTrade, UserProfile
from ..live_paper_trading import (
    HORIZON_BARS,
    RISK_PROFILE,
    RISK_REWARD,
    STOP_PCT,
    TAKE_PCT,
    LiveYFinanceProvider,
    _completed_bars,
    _live_trigger,
    _unprocessed_bars,
    check_exit,
)
from ..market.data import SCAN_UNIVERSE
from ..paper_trading import PaperTradingEngine
from ..portfolio.manager import Portfolio
from ..risk import RiskEngine
from .lessons import learn_from_trade
from .paper_trading import assert_paper_only, evidence_path

STRATEGY_ID = "wide-6"
STARTING_CASH = 100.0
AVA_DAILY_DIR_NAME = "ava-daily"
STATE_FILE = "state.json"
REPORT_FILE = "ava-daily-report.md"
STOP_FILE = "STOP"
DAILY_RUN = "daily"
NY_TZ = ZoneInfo("America/New_York")

PAPER_ONLY_BANNER = (
    "PAPER ONLY — Ava's virtual $100 pot, no live brokerage, no real "
    "money. Trading involves substantial risk of loss. This daily paper "
    "run does not promise profits. Past performance does not guarantee "
    "future results."
)


def default_ava_daily_dir() -> Path:
    """data/ava-daily/ next to this package's project root.

    This module lives at vaulttec/ava/daily_trading.py, so
    parents[2] is the project root (vaulttec/) and data/ sits
    beside the package.
    """
    return Path(__file__).resolve().parents[2] / "data" / AVA_DAILY_DIR_NAME


def trade_id(run_date: date, symbol: str) -> str:
    """One trade id per day per symbol: AVA-2026-11-10-AAPL."""
    return f"AVA-{run_date.isoformat()}-{symbol}"


# --- State -----------------------------------------------------------------

def fresh_state(started_on: str) -> dict:
    """A brand-new Ava daily state: $100 virtual cash, no
    positions, nothing processed yet."""
    return {
        "version": 1,
        "paper_only": True,
        "strategy": STRATEGY_ID,
        "stop_pct": STOP_PCT,
        "take_pct": TAKE_PCT,
        "horizon_bars": HORIZON_BARS,
        "risk_profile": RISK_PROFILE,
        "starting_cash_usd": STARTING_CASH,
        "cash_usd": STARTING_CASH,
        "enabled": True,
        "started_on": started_on,
        "last_run_date": None,
        "runs": 0,
        "last_processed_bar_date": {},  # symbol -> ISO date of last bar processed
        "last_close": {},  # symbol -> last completed close seen
        "open_positions": [],  # one per symbol at most, each with trade_id
        "closed_trades": [],  # each with trade_id
        "blocked_count": 0,
        "fetch_failures": {},  # symbol -> count of failed fetches
        "run_history": [],  # per-run summaries, newest last (capped at 365)
    }


def load_state(ava_dir: Path) -> dict:
    path = Path(ava_dir) / STATE_FILE
    if not path.exists():
        return fresh_state(started_on=date.today().isoformat())
    state = json.loads(path.read_text(encoding="utf-8"))
    base = fresh_state(state.get("started_on", date.today().isoformat()))
    base.update(state)
    return base


def save_state(ava_dir: Path, state: dict) -> Path:
    """Atomic save: write a temp file, then rename over the state."""
    path = Path(ava_dir) / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def _build_engine(state: dict) -> tuple[Portfolio, RiskEngine, PaperTradingEngine]:
    """Rebuild Ava's in-memory paper engine from durable state, so a
    run resumes exactly where the last one left off: same cash, same
    holdings, same open trades (so close_position can mark them).
    Trades are rebuilt with source "ava-paper" so her lessons say
    whose trades they are."""
    limits = RISK_PROFILES[state.get("risk_profile", RISK_PROFILE)]
    profile = UserProfile(
        risk_tolerance=state.get("risk_profile", RISK_PROFILE),
        max_position_pct=limits["max_position_pct"],
        daily_loss_limit_pct=limits["daily_loss_limit_pct"],
        allowed_markets=["stocks", "crypto"])
    risk = RiskEngine(
        max_position_pct=limits["max_position_pct"],
        max_concentration_pct=limits["max_concentration_pct"],
        max_exposure_pct=limits["max_exposure_pct"],
        daily_loss_limit_pct=limits["daily_loss_limit_pct"],
        min_risk_reward=limits["min_risk_reward"])
    portfolio = Portfolio(cash=float(state["cash_usd"]))
    engine = PaperTradingEngine(portfolio, risk)
    for pos in state["open_positions"]:
        from ..portfolio.manager import Holding

        portfolio.holdings[pos["symbol"]] = Holding(
            symbol=pos["symbol"], quantity=pos["quantity"],
            avg_cost=pos["entry_price"])
        engine.trades.append(PaperTrade(
            symbol=pos["symbol"], side="buy", quantity=pos["quantity"],
            price=pos["entry_price"], stop_loss=pos["stop_loss"],
            take_profit=pos["take_profit"],
            reason=f"{pos['strategy']} mean-reversion trigger, exit variant {STRATEGY_ID}",
            source="ava-paper", status="open"))
    return portfolio, risk, engine


# --- Evidence ---------------------------------------------------------------

def _write_evidence(evidence_file: Path, record: dict) -> None:
    """Append one JSON line to Ava's evidence log (the same file
    her historical-window records already live in)."""
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    with evidence_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _reasoning(*, symbol: str, source: str, entry: float, stop: float,
               take: float, quantity: float, risk_usd: float,
               scanner, trend_now: str, portfolio_value: float) -> str:
    """Risk first, in plain language — the same wording Ava used
    for her historical-window trades: the case against the trade,
    then the case for it. Every number is real — nothing invented."""
    position_usd = round(entry * quantity, 2)
    reward_usd = round((take - entry) * quantity, 2)
    risk_pct = round(risk_usd / portfolio_value * 100, 2) if portfolio_value else 0.0
    against = (
        f"Against first: if this hits the stop I lose ${risk_usd:.2f} "
        f"({risk_pct:.1f}% of the pot) on a ${position_usd:.2f} position, "
        f"and the short-term trend is {trend_now} — a bounce is possible, "
        "never promised, and a stop that gets hit is the stop doing its job."
    )
    for_case = (
        f"For: the {source} signal fired under our wide-6 rules "
        f"(scanner confidence {scanner.confidence:.0%}: {scanner.evidence}); "
        f"stop ${stop:.2f} and target ${take:.2f} are set, so a win pays "
        f"about ${reward_usd:.2f}. Small size, planned loss, no chasing."
    )
    return f"{against} {for_case}"


# --- The daily run ----------------------------------------------------------

def run_ava_daily(run_date: date | None = None, provider=None,
                  ava_dir: str | Path | None = None,
                  evidence_file: str | Path | None = None,
                  symbols: list[str] | None = None) -> dict:
    """Run one Ava paper day.

    ``run_date`` defaults to today (America/New_York). ``provider``
    may be injected (tests use a stub — the real run uses yfinance).
    Returns a summary dict; the durable state, evidence log and
    report are written as side effects (except on a total fetch
    failure, where no trade state changes).
    """
    assert_paper_only()
    run_date = run_date or datetime.now(NY_TZ).date()
    ava_dir = Path(ava_dir) if ava_dir else default_ava_daily_dir()
    ava_dir.mkdir(parents=True, exist_ok=True)
    evidence_file = Path(evidence_file) if evidence_file is not None else evidence_path()
    symbols = symbols or list(SCAN_UNIVERSE)
    run_id = run_date.isoformat()

    state = load_state(ava_dir)
    if (ava_dir / STOP_FILE).exists() or not state.get("enabled", True):
        state["run_history"].append({
            "run_date": run_id, "status": "stopped",
            "trades_opened": 0, "trades_closed": 0, "realised_pnl_usd": 0.0,
            "symbols_processed": [], "failed_symbols": {},
            "cash_usd": state["cash_usd"],
            "open_positions": len(state["open_positions"]),
            "closed_trades_total": len(state["closed_trades"]),
        })
        state["run_history"] = state["run_history"][-365:]
        save_state(ava_dir, state)
        return {"run_date": run_id, "status": "stopped",
                "reason": "kill-switch active (ava-daily/STOP exists or "
                          "state enabled=false) — no fetch, no trades",
                "trades_opened": 0, "trades_closed": 0,
                "realised_pnl_usd": 0.0, "symbols_processed": [],
                "failed_symbols": {}}

    if provider is None:
        provider = LiveYFinanceProvider(run_date)

    portfolio, risk, engine = _build_engine(state)
    positions = {p["symbol"]: dict(p) for p in state["open_positions"]}
    counts: Counter = Counter()
    failed: dict[str, str] = {}
    processed_symbols: list[str] = []

    for symbol in symbols:
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

        last_processed = state["last_processed_bar_date"].get(symbol)
        bars, init_to, initialised = _unprocessed_bars(history, run_date, last_processed)
        if initialised and init_to is not None:
            # Warm-up bars are never traded: mark them processed.
            state["last_processed_bar_date"][symbol] = init_to
        if bars.empty:
            counts["symbols_no_new_bar"] += 1
            continue
        processed_symbols.append(symbol)

        for row_idx in range(len(bars)):
            bar = bars.iloc[row_idx]
            bar_date = str(bar["date"])[:10]
            history_to_bar = history.copy()
            history_to_bar["date"] = pd.to_datetime(
                history_to_bar["date"]).dt.tz_localize(None)
            # History up to and including this bar only — no look-ahead.
            history_to_bar = history_to_bar[
                history_to_bar["date"] <= pd.Timestamp(bar["date"])
            ].reset_index(drop=True)
            state["last_close"][symbol] = round(float(bar["close"]), 2)
            # A new bar is a new day: the daily-loss tracker resets.
            engine.realised_pnl = 0.0

            # 1) Exit check first, for any open position.
            position = positions.get(symbol)
            exited_this_bar = False
            if position is not None:
                position["bars_held"] = int(position.get("bars_held", 0)) + 1
                exit_hit = check_exit(bar, position)
                if exit_hit is None and position["bars_held"] >= HORIZON_BARS:
                    exit_hit = (round(float(bar["close"]), 2),
                                f"time exit ({HORIZON_BARS} days)")
                if exit_hit is not None:
                    exit_price, exit_reason = exit_hit
                    pnl = engine.close_position(symbol, exit_price, exit_reason)
                    pnl = 0.0 if pnl is None else round(float(pnl), 2)
                    closed = {
                        "trade_id": position["trade_id"],
                        "symbol": symbol, "strategy": position["strategy"],
                        "entry_date": position["entry_date"],
                        "entry_price": position["entry_price"],
                        "exit_date": bar_date, "exit_price": exit_price,
                        "quantity": position["quantity"],
                        "stop_loss": position["stop_loss"],
                        "take_profit": position["take_profit"],
                        "exit_reason": exit_reason,
                        "days_held": position["bars_held"],
                        "pnl_usd": pnl,
                    }
                    state["closed_trades"].append(closed)
                    del positions[symbol]
                    exited_this_bar = True
                    counts["trades_closed"] += 1
                    counts["lessons_learned"] += 1
                    counts["realised_pnl_usd"] = round(
                        counts.get("realised_pnl_usd", 0.0) + pnl, 2)
                    _write_evidence(evidence_file, {
                        "when": datetime.utcnow().isoformat(),
                        "run": DAILY_RUN, "run_date": run_id,
                        "trade_id": position["trade_id"],
                        "symbol": symbol, "signal": position["strategy"],
                        "status": "closed",
                        "entry": position["entry_price"],
                        "stop": position["stop_loss"],
                        "target": position["take_profit"],
                        "position_size": position["quantity"],
                        "exit": exit_price, "exit_reason": exit_reason,
                        "days_held": position["bars_held"],
                        "pnl_usd": pnl, "won": pnl > 0,
                    })
                    closed_trade = next(
                        (t for t in reversed(engine.trades)
                         if t.symbol == symbol and t.status == "closed"),
                        None)
                    if closed_trade is not None:
                        learn_from_trade(closed_trade)

            # 2) Entry check — only if no position is open now, and
            # not on a bar where this symbol just exited: buying back
            # into the same falling bar it just stopped out of would
            # churn, and the validated walk-forward never re-entered
            # inside one window.
            if symbol not in positions and not exited_this_bar:
                fired = None
                for strategy in STRATEGIES:
                    if _live_trigger(strategy, history_to_bar):
                        fired = strategy
                        break
                if fired is None and trend_trigger("macd", history_to_bar):
                    fired = "macd"
                if fired is not None:
                    counts["signals_seen"] += 1
                    entry = float(bar["close"])
                    stop = round(entry * (1 - STOP_PCT), 2)
                    take = math.ceil((entry + RISK_REWARD * (entry - stop)) * 100) / 100
                    raw_qty = risk.position_size(
                        portfolio.value({symbol: entry}), entry)
                    quantity = math.floor(raw_qty * 10000) / 10000
                    tid = trade_id(run_date, symbol)
                    if quantity <= 0:
                        counts["skipped_too_small"] += 1
                        _write_evidence(evidence_file, {
                            "when": datetime.utcnow().isoformat(),
                            "run": DAILY_RUN, "run_date": run_id,
                            "trade_id": tid,
                            "symbol": symbol, "signal": fired,
                            "status": "blocked",
                            "block_reason": (
                                f"Too small: a {STARTING_CASH:.0f}-dollar pot "
                                f"sizes to 0.0000 of {symbol} at ${entry:,.2f} "
                                "(10% position cap, quantity floored to 4 decimals) — "
                                "the trade could not be sized, so it was not placed."),
                            "entry": entry,
                        })
                        continue
                    from ..market.indicators import trend as trend_direction

                    scanner = generate_signal(symbol, history_to_bar)
                    risk_usd = round((entry - stop) * quantity, 2)
                    trend_now = trend_direction(history_to_bar["close"])
                    reasoning = _reasoning(
                        symbol=symbol, source=fired, entry=entry, stop=stop,
                        take=take, quantity=quantity, risk_usd=risk_usd,
                        scanner=scanner, trend_now=trend_now,
                        portfolio_value=portfolio.value({symbol: entry}))
                    trade = engine.place_order(
                        symbol, "buy", quantity, entry, stop, take,
                        reason=f"{fired} trigger, Ava paper wide-6",
                        source="ava-paper")
                    if trade is None:
                        counts["blocked_by_risk"] += 1
                        state["blocked_count"] = state.get("blocked_count", 0) + 1
                        reasons = engine.blocked[-1]["reasons"] if engine.blocked else []
                        _write_evidence(evidence_file, {
                            "when": datetime.utcnow().isoformat(),
                            "run": DAILY_RUN, "run_date": run_id,
                            "trade_id": tid,
                            "symbol": symbol, "signal": fired,
                            "confidence": round(scanner.confidence, 3),
                            "status": "blocked",
                            "block_reason": "; ".join(reasons),
                            "entry": entry, "stop": stop, "target": take,
                            "position_size_usd": round(entry * quantity, 2),
                            "risk_usd": risk_usd,
                            "reasoning": reasoning,
                        })
                    else:
                        positions[symbol] = {
                            "trade_id": tid, "symbol": symbol,
                            "strategy": fired,
                            "entry_date": bar_date, "entry_price": entry,
                            "quantity": quantity, "stop_loss": stop,
                            "take_profit": take, "bars_held": 0,
                        }
                        counts["trades_opened"] += 1
                        _write_evidence(evidence_file, {
                            "when": datetime.utcnow().isoformat(),
                            "run": DAILY_RUN, "run_date": run_id,
                            "trade_id": tid,
                            "symbol": symbol, "signal": fired,
                            "confidence": round(scanner.confidence, 3),
                            "scanner_evidence": scanner.evidence,
                            "status": "placed",
                            "entry": entry, "stop": stop, "target": take,
                            "position_size": quantity,
                            "position_size_usd": round(entry * quantity, 2),
                            "risk_usd": risk_usd,
                            "reasoning": reasoning,
                        })

            state["last_processed_bar_date"][symbol] = bar_date

    # Total fetch failure: no trades, no cash/position change — but
    # the failure counts ARE durable (they are the audit trail), so
    # save the state with them recorded. Nothing is invented.
    if processed_symbols == [] and failed and len(failed) == len(symbols):
        state["run_history"].append({
            "run_date": run_id, "status": "not_run_no_data",
            "trades_opened": 0, "trades_closed": 0,
            "realised_pnl_usd": 0.0, "symbols_processed": [],
            "symbols_no_new_bar": 0, "signals_seen": 0,
            "blocked_by_risk": 0, "skipped_too_small": 0,
            "failed_symbols": failed, "cash_usd": state["cash_usd"],
            "open_positions": len(state["open_positions"]),
            "closed_trades_total": len(state["closed_trades"]),
        })
        state["run_history"] = state["run_history"][-365:]
        save_state(ava_dir, state)
        return {"run_date": run_id, "status": "not_run_no_data",
                "reason": "not run — no data: all symbols failed to fetch",
                "trades_opened": 0, "trades_closed": 0,
                "realised_pnl_usd": 0.0, "symbols_processed": [],
                "failed_symbols": failed}

    # Sync durable state from the engine.
    state["cash_usd"] = round(float(portfolio.cash), 2)
    state["open_positions"] = [positions[s] for s in sorted(positions)]
    state["last_run_date"] = run_id
    state["runs"] = int(state.get("runs", 0)) + 1
    status = "already_processed" if not processed_symbols else "ok"
    summary = {
        "run_date": run_id,
        "status": status,
        "trades_opened": int(counts["trades_opened"]),
        "trades_closed": int(counts["trades_closed"]),
        "realised_pnl_usd": round(float(counts.get("realised_pnl_usd", 0.0)), 2),
        "symbols_processed": processed_symbols,
        "symbols_no_new_bar": int(counts["symbols_no_new_bar"]),
        "signals_seen": int(counts["signals_seen"]),
        "blocked_by_risk": int(counts["blocked_by_risk"]),
        "skipped_too_small": int(counts["skipped_too_small"]),
        "lessons_learned": int(counts["lessons_learned"]),
        "failed_symbols": failed,
        "cash_usd": state["cash_usd"],
        "open_positions": len(state["open_positions"]),
        "closed_trades_total": len(state["closed_trades"]),
    }
    state["run_history"].append(summary)
    state["run_history"] = state["run_history"][-365:]
    save_state(ava_dir, state)
    save_report(ava_dir, state)
    return summary


# --- Reporting ---------------------------------------------------------------

def compute_summary(state: dict) -> dict:
    """Portfolio summary from durable state (no network, no engine)."""
    closed = state.get("closed_trades", [])
    wins = [t for t in closed if t["pnl_usd"] > 0]
    losses = [t for t in closed if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in closed), 2)
    open_positions = state.get("open_positions", [])
    last_close = state.get("last_close", {})
    holdings_value = round(sum(
        p["quantity"] * last_close.get(p["symbol"], p["entry_price"])
        for p in open_positions), 2)
    portfolio_value = round(float(state.get("cash_usd", STARTING_CASH)) + holdings_value, 2)
    return {
        "paper_only": True,
        "strategy": state.get("strategy", STRATEGY_ID),
        "started_on": state.get("started_on"),
        "last_run_date": state.get("last_run_date"),
        "runs": state.get("runs", 0),
        "starting_cash_usd": state.get("starting_cash_usd", STARTING_CASH),
        "cash_usd": round(float(state.get("cash_usd", STARTING_CASH)), 2),
        "holdings_value_usd": holdings_value,
        "portfolio_value_usd": portfolio_value,
        "total_pnl_usd": total_pnl,
        "total_pnl_pct": round(total_pnl / STARTING_CASH * 100, 2),
        "closed_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "avg_win_usd": round(sum(t["pnl_usd"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_usd": round(sum(t["pnl_usd"] for t in losses) / len(losses), 2) if losses else 0.0,
        "expectancy_usd": round(total_pnl / len(closed), 2) if closed else 0.0,
        "exits": dict(Counter(t["exit_reason"] for t in closed)),
        "open_positions": len(open_positions),
        "blocked_count": state.get("blocked_count", 0),
        "fetch_failures": state.get("fetch_failures", {}),
    }


def render_report(state: dict) -> str:
    s = compute_summary(state)
    lines = [
        "# Ava — Daily Paper Trading (real days, paper only)",
        "",
        f"> **{PAPER_ONLY_BANNER}**",
        "",
        "## Strategy",
        "",
        f"- Variant: **{s['strategy']}** — 6% stop-loss / 9% take-profit "
        f"(1.5:1), 10-bar time exit, RSI + Bollinger mean-reversion "
        f"(the lead) with MACD trend-following (the complement), "
        f"long-only, balanced profile, **$100 virtual cash**.",
        f"- Started: {s['started_on'] or 'not started yet'} — "
        f"last run: {s['last_run_date'] or 'never'} — "
        f"runs completed: {s['runs']}.",
        f"- Data: delayed real prices via yfinance (free). Signals use "
        f"history up to the processed bar only — no look-ahead. A bar "
        f"is only traded once its day is complete.",
        "",
        "## Portfolio (paper)",
        "",
        f"- Virtual cash: **${s['cash_usd']:,.2f}**",
        f"- Open holdings value: ${s['holdings_value_usd']:,.2f} "
        f"(at last completed close)",
        f"- Portfolio value: **${s['portfolio_value_usd']:,.2f}**",
        f"- Total realised paper P&L: **${s['total_pnl_usd']:+,.2f} "
        f"({s['total_pnl_pct']:+.2f}% of starting cash)**",
        "",
        "## Closed trades",
        "",
        f"- Closed: {s['closed_trades']} — wins: {s['wins']} — "
        f"losses: {s['losses']} — win rate: **{s['win_rate_pct']}%** "
        f"(break-even at 1.5:1 is 40%)",
        f"- Average win: ${s['avg_win_usd']:,.2f} — average loss: "
        f"${s['avg_loss_usd']:,.2f} — expectancy: "
        f"${s['expectancy_usd']:+,.2f} per trade",
        f"- Exits: {s['exits'] or 'none yet'}",
        f"- Open positions: {s['open_positions']} — blocked by risk: "
        f"{s['blocked_count']} — fetch failures: "
        f"{s['fetch_failures'] or 'none'}",
        "",
    ]
    if state.get("open_positions"):
        lines += [
            "## Open positions",
            "",
            "| Trade | Symbol | Strategy | Entry | Qty | Stop | Target | Bars held |",
            "|---|---|---|---|---:|---:|---:|---:|",
        ]
        for p in state["open_positions"]:
            lines.append(
                f"| {p.get('trade_id', '')} | {p['symbol']} | {p['strategy']} | "
                f"${p['entry_price']:,.2f} ({p['entry_date']}) | {p['quantity']} | "
                f"${p['stop_loss']:,.2f} | ${p['take_profit']:,.2f} | {p['bars_held']} |")
        lines.append("")
    if state.get("closed_trades"):
        lines += [
            "## Closed trades (every trade, in order)",
            "",
            "| # | Trade | Symbol | Strategy | Entry | Exit | Reason | Days | P&L ($) |",
            "|---:|---|---|---|---|---|---|---|---:|",
        ]
        for i, t in enumerate(state["closed_trades"], 1):
            lines.append(
                f"| {i} | {t.get('trade_id', '')} | {t['symbol']} | {t['strategy']} | "
                f"${t['entry_price']:,.2f} ({t['entry_date']}) | "
                f"${t['exit_price']:,.2f} ({t['exit_date']}) | "
                f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
        lines.append("")
    if state.get("run_history"):
        lines += ["## Run history (latest last)", ""]
        for run in state["run_history"][-30:]:
            lines.append(
                f"- {run['run_date']}: {run['status']} — opened "
                f"{run['trades_opened']}, closed {run['trades_closed']}, "
                f"realised P&L ${run['realised_pnl_usd']:+,.2f}, "
                f"processed {run['symbols_processed'] or 'no symbols'}, "
                f"failed: {run['failed_symbols'] or 'none'}")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        "Ava's daily paper trades arrive one day at a time and cannot "
        "be re-run — that is the point. A good week here still does "
        "not prove future profits, and a compliance/legal review is "
        "still required before any real money is considered. Past "
        "performance does not guarantee future results.",
        "",
    ]
    return "\n".join(lines)


def save_report(ava_dir: str | Path, state: dict) -> Path:
    path = Path(ava_dir) / REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(state), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ava daily paper trading — one day at a time, "
                    "paper only. No broker, no real money.")
    parser.add_argument("--date", default=None,
                        help="run date YYYY-MM-DD (America/New_York); "
                             "default: today")
    parser.add_argument("--state-dir", default=None,
                        help="ava-daily directory "
                             "(default: vaulttec/data/ava-daily)")
    parser.add_argument("--evidence-file", default=None,
                        help="evidence jsonl (default: data/ava-evidence.jsonl)")
    args = parser.parse_args(argv)
    run_date = date.fromisoformat(args.date) if args.date else None
    ava_dir = Path(args.state_dir) if args.state_dir else default_ava_daily_dir()
    evidence_file = Path(args.evidence_file) if args.evidence_file else None
    summary = run_ava_daily(run_date=run_date, ava_dir=ava_dir,
                            evidence_file=evidence_file)
    print(f"PAPER ONLY — Ava daily run {summary['run_date']}: {summary['status']}")
    print(f"Symbols processed: {summary['symbols_processed'] or 'none'}")
    print(f"Trades opened: {summary['trades_opened']} — "
          f"closed: {summary['trades_closed']} — realised P&L: "
          f"${summary['realised_pnl_usd']:+,.2f} — "
          f"lessons learned: {summary.get('lessons_learned', 0)}")
    if summary["failed_symbols"]:
        print(f"Fetch failures: {summary['failed_symbols']}")
    print(f"Report: {ava_dir / REPORT_FILE}")
    print(f"State: {ava_dir / STATE_FILE}")
    ok_statuses = ("ok", "already_processed", "stopped")
    return 0 if summary["status"] in ok_statuses else 2


if __name__ == "__main__":
    sys.exit(main())
