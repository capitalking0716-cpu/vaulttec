"""Live paper trading over real days — paper only.

Phase 4d proved the wide-6 exit (6% stop / 9% target, 1.5:1) on
fresh past windows: RSI wide-6 +$1,226.24 (61.6% win, 3/3 windows),
Bollinger wide-6 +$1,043.47 (63.9% win, 3/3 windows). Those are
still past prices. This module is the next step the Phase 4d report
called for: trade the same wide-6 rules, one day at a time, on
delayed real prices as they arrive — no re-runs, no look-ahead.

How it works
------------
- Once per day (see ``live_paper/RUNBOOK.md``), the runner fetches
  the latest delayed real history for the same 12-symbol universe
  via yfinance, then processes every *completed* daily bar it has
  not processed yet, in order. A bar counts as completed only when
  its date is before the run date (America/New_York), so a
  still-forming intraday bar is never traded on.
- For each new bar, per symbol, in order: first check any open
  position against that bar (stop-loss on the bar's low, then
  take-profit on the bar's high, then the 10-bar time exit), then
  — only if no position is open for that symbol — evaluate the
  RSI / Bollinger mean-reversion trigger on history up to and
  including that bar (no look-ahead). A triggered trade goes
  through the real PaperTradingEngine and Risk Engine with the
  wide-6 rules (6% stop, 9% target, 10-bar horizon), balanced
  profile, $10,000 virtual cash, long-only.
- State is durable on disk (``live_paper/state.json``): cash, open
  positions (with bars held), closed trades, per-symbol last
  processed bar, run history. A second run on the same day finds
  no new completed bars and does nothing — the runner is
  idempotent per day. Every decision is appended to
  ``live_paper/trades.jsonl`` and the running report
  ``live_paper/live-paper-report.md`` is regenerated each run.
- Market holidays and no-data days are logged and skipped, never
  traded on. A yfinance fetch failure is retried 3 times, recorded
  per symbol, and never replaced with sample data — a symbol that
  cannot be fetched is simply not traded that day, and if every
  symbol fails the run exits non-zero with no state change.
- Kill-switch: create ``live_paper/STOP`` (or set ``enabled`` to
  false in the state file) and the next run does nothing at all
  except log that it was stopped. Delete the file to resume.
  Stopping freezes the run — open positions stay open until the
  runner is resumed and their exit bars arrive.
- Two live-only guards (they cannot change any validated backtest
  result, which used real prices): a position that exits on a bar
  is never re-entered on that same bar, and a Bollinger trigger
  needs a real (non-zero-width) band — a flat line is not a bounce.

Hard rules (same as every phase before this one)
------------------------------------------------
- PAPER ONLY. No broker is ever contacted, no brokerage account
  is created, no real money moves, no leverage, no options.
- Every trade keeps its stop-loss. The stop is never removed.
- Past performance does not guarantee future results. A good live
  paper run still needs a compliance/legal review before real
  money is ever considered.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from .db.models import PaperTrade, UserProfile
from .market.data import SCAN_UNIVERSE
from .portfolio.manager import Portfolio
from .paper_trading import PaperTradingEngine
from .risk import RiskEngine
from .analytics.mean_reversion import STRATEGIES, mean_reversion_trigger, strategy_label

# --- The live strategy: wide-6, exactly as validated in Phase 4c/4d ---
STRATEGY_ID = "wide-6"
STOP_PCT = 0.06
TAKE_PCT = 0.09  # 9% reward vs 6% risk = 1.5:1, the profile minimum
HORIZON_BARS = 10  # time exit after 10 daily bars held
RISK_REWARD = 1.5
RISK_PROFILE = "balanced"
STARTING_CASH = PAPER_STARTING_CASH
HISTORY_DAYS = 280  # enough warm-up (70+ bars) for RSI-14 / Bollinger-20
FETCH_RETRIES = 3
NY_TZ = ZoneInfo("America/New_York")

LIVE_DIR_NAME = "live_paper"
STATE_FILE = "state.json"
LOG_FILE = "trades.jsonl"
REPORT_FILE = "live-paper-report.md"
STOP_FILE = "STOP"

PAPER_ONLY_BANNER = (
    "PAPER ONLY — virtual money, no live brokerage, no real money. "
    "Trading involves substantial risk of loss. This live paper run "
    "does not promise profits. Past performance does not guarantee "
    "future results."
)


def default_live_dir() -> Path:
    """live_paper/ next to this package's project root.

    This module lives at vaulttec/vaulttec/live_paper_trading.py,
    so parents[1] is the project root (vaulttec/) — parents[2]
    would be the goals files folder, which is wrong.
    """
    return Path(__file__).resolve().parents[1] / LIVE_DIR_NAME


class LiveYFinanceProvider:
    """Delayed real history for the live run via yfinance.

    Fetches ``run_date - HISTORY_DAYS`` .. ``run_date + 1 day`` so
    the latest completed bar is included and indicators are warm.
    Retries 3 times with backoff; a symbol that still cannot be
    fetched raises, and the caller records it as failed — it is
    never silently replaced with sample data.
    """

    def __init__(self, run_date: date, history_days: int = HISTORY_DAYS):
        self.run_date = run_date
        self.fetch_start = run_date - timedelta(days=history_days)
        self.fetch_end = run_date + timedelta(days=1)

    def get_history(self, symbol: str, days: int | None = None) -> pd.DataFrame:
        import yfinance as yf

        last_error: Exception | None = None
        df = None
        for attempt in range(FETCH_RETRIES):
            try:
                df = yf.Ticker(symbol).history(
                    start=self.fetch_start.isoformat(),
                    end=self.fetch_end.isoformat())
            except Exception as exc:  # noqa: BLE001 — retry, then raise
                last_error = exc
                df = None
            if df is not None and not df.empty:
                break
            last_error = last_error or ValueError(
                f"yfinance returned no history for {symbol}")
            time.sleep(5 * (attempt + 1))  # transient Yahoo blocks recover
        if df is None or df.empty:
            raise ValueError(f"yfinance returned no history for {symbol} "
                             f"after {FETCH_RETRIES} attempts ({last_error})")
        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"]
                if c in df.columns]
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        time.sleep(1.0)  # be polite to the free data feed
        return df[cols]


# --- State -----------------------------------------------------------------

def fresh_state(started_on: str) -> dict:
    """A brand-new live paper state: $10,000 virtual cash, no
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
        "open_positions": [],  # one per symbol at most
        "closed_trades": [],
        "blocked_count": 0,
        "fetch_failures": {},  # symbol -> count of failed fetches
        "run_history": [],  # per-run summaries, newest last (capped at 365)
    }


def load_state(live_dir: Path) -> dict:
    path = Path(live_dir) / STATE_FILE
    if not path.exists():
        return fresh_state(started_on=date.today().isoformat())
    state = json.loads(path.read_text(encoding="utf-8"))
    # Tolerate older states missing newer keys.
    base = fresh_state(state.get("started_on", date.today().isoformat()))
    base.update(state)
    return base


def save_state(live_dir: Path, state: dict) -> Path:
    """Atomic save: write a temp file, then rename over the state."""
    path = Path(live_dir) / STATE_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def append_log(live_dir: Path, event: dict) -> None:
    """Append one JSON line to the durable decision log."""
    path = Path(live_dir) / LOG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")


# --- Engine reconstruction -------------------------------------------------

def build_engine(state: dict) -> tuple[Portfolio, RiskEngine, PaperTradingEngine]:
    """Rebuild the in-memory paper engine from durable state, so a
    run resumes exactly where the last one left off: same cash, same
    holdings, same open trades (so close_position can mark them)."""
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
        portfolio.holdings[pos["symbol"]] = _holding_from_position(pos)
        engine.trades.append(PaperTrade(
            symbol=pos["symbol"], side="buy", quantity=pos["quantity"],
            price=pos["entry_price"], stop_loss=pos["stop_loss"],
            take_profit=pos["take_profit"],
            reason=f"{pos['strategy']} mean-reversion trigger, exit variant {STRATEGY_ID}",
            source="live-paper", status="open"))
    return portfolio, risk, engine


def _holding_from_position(pos: dict):
    from .portfolio.manager import Holding

    return Holding(symbol=pos["symbol"], quantity=pos["quantity"],
                   avg_cost=pos["entry_price"])


# --- One bar ----------------------------------------------------------------

def check_exit(bar: pd.Series, position: dict) -> tuple[float, str] | None:
    """Exit check for one completed bar, in the same order as the
    validation runs: stop-loss first (the bar's low touched the
    stop), then take-profit (the bar's high touched the target).
    The time exit is checked by the caller (bars held). Returns
    (exit_price, reason) or None."""
    if float(bar["low"]) <= position["stop_loss"]:
        return round(float(position["stop_loss"]), 2), "stop-loss"
    if float(bar["high"]) >= position["take_profit"]:
        return round(float(position["take_profit"]), 2), "take-profit"
    return None


def _live_trigger(strategy: str, history_up_to_bar: pd.DataFrame) -> bool:
    """The validated mean-reversion trigger, plus one live-only
    guard: a Bollinger trigger needs a real band. When the price
    has not moved at all for 20 days the band collapses to the
    price itself (bandwidth zero), so ``close <= lower`` is true
    on a flat line — buying "because the price hasn't moved" is
    not a bounce. Real market data always has non-zero volatility,
    so this guard cannot change any validated backtest result; it
    only stops a degenerate trigger from firing live."""
    if strategy == "bollinger":
        from .market.indicators import bollinger_bands

        closes = history_up_to_bar["close"].reset_index(drop=True)
        bands = bollinger_bands(closes)
        bandwidth = bands["bandwidth"].iloc[-1]
        if pd.isna(bandwidth) or float(bandwidth) <= 0:
            return False
    return mean_reversion_trigger(strategy, history_up_to_bar)


def _completed_bars(history: pd.DataFrame, run_date: date) -> pd.DataFrame:
    """Only bars dated before the run date — a still-forming
    intraday bar is never traded on. Sorted, de-duplicated."""
    df = history.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df = df[df["date"].dt.date < run_date]
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


def _unprocessed_bars(history: pd.DataFrame, run_date: date,
                      last_processed: str | None) -> tuple[pd.DataFrame, str | None, bool]:
    """The completed bars this run should process, in order.

    First ever run for a symbol (``last_processed`` None): all
    earlier bars are warm-up only — the latest completed bar is
    the first trading day, so initialise ``last_processed`` to the
    second-latest completed bar and process only the latest one.
    Returns (bars_to_process, new_last_processed_if_no_bars, was_initialised).
    """
    completed = _completed_bars(history, run_date)
    if completed.empty:
        return completed, last_processed, False
    if last_processed is None:
        if len(completed) >= 2:
            init_to = str(completed["date"].iloc[-2])[:10]
            return completed.iloc[[-1]], init_to, True
        return completed, None, True
    mask = completed["date"].dt.date.astype(str) > last_processed
    return completed[mask].reset_index(drop=True), last_processed, False


# --- The daily run ----------------------------------------------------------

def run_live_day(run_date: date | None = None, provider=None,
                 live_dir: str | Path | None = None,
                 symbols: list[str] | None = None) -> dict:
    """Run one live paper day.

    ``run_date`` defaults to today (America/New_York). ``provider``
    may be injected (tests use a stub — the real run uses yfinance).
    Returns a summary dict; the durable state, log and report are
    written as a side effect (except on total fetch failure, where
    the state is left untouched).
    """
    run_date = run_date or datetime.now(NY_TZ).date()
    live_dir = Path(live_dir) if live_dir else default_live_dir()
    live_dir.mkdir(parents=True, exist_ok=True)
    symbols = symbols or list(SCAN_UNIVERSE)
    run_id = run_date.isoformat()

    # Kill-switch: STOP file, or enabled=false in state. Log it and
    # do nothing at all — no fetch, no trades. Open positions stay
    # open until the runner is resumed.
    state = load_state(live_dir)
    if (live_dir / STOP_FILE).exists() or not state.get("enabled", True):
        event = {"date": run_id, "event": "run_stopped",
                 "reason": "kill-switch active (live_paper/STOP exists or "
                           "state enabled=false) — no fetch, no trades",
                 "paper_only": True}
        append_log(live_dir, event)
        return {"run_date": run_id, "status": "stopped",
                "reason": event["reason"], "trades_opened": 0,
                "trades_closed": 0, "realised_pnl_usd": 0.0,
                "symbols_processed": [], "failed_symbols": {}}

    if provider is None:
        provider = LiveYFinanceProvider(run_date)

    portfolio, risk, engine = build_engine(state)
    positions = {p["symbol"]: dict(p) for p in state["open_positions"]}
    counts: Counter = Counter()
    failed: dict[str, str] = {}
    processed_symbols: list[str] = []
    run_events: list[dict] = []

    for symbol in symbols:
        try:
            history = provider.get_history(symbol)
        except Exception as exc:  # noqa: BLE001 — record, never invent data
            failed[symbol] = f"{type(exc).__name__}: {exc}"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            run_events.append({"date": run_id, "event": "fetch_failed",
                               "symbol": symbol, "error": failed[symbol],
                               "paper_only": True})
            continue
        if history is None or history.empty or "close" not in history.columns:
            failed[symbol] = "empty history returned"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            run_events.append({"date": run_id, "event": "fetch_failed",
                               "symbol": symbol, "error": failed[symbol],
                               "paper_only": True})
            continue

        last_processed = state["last_processed_bar_date"].get(symbol)
        bars, init_to, initialised = _unprocessed_bars(history, run_date, last_processed)
        if initialised and init_to is not None:
            # Warm-up bars are never traded: mark them processed.
            state["last_processed_bar_date"][symbol] = init_to
        if bars.empty:
            # No new completed bar (weekend / holiday / already run
            # today) — nothing to do for this symbol.
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
                    counts["realised_pnl_usd"] = round(
                        counts.get("realised_pnl_usd", 0.0) + pnl, 2)
                    run_events.append({"date": run_id, "event": "trade_closed",
                                       "paper_only": True, **closed})

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
                if fired is not None:
                    counts["signals_seen"] += 1
                    entry = float(bar["close"])
                    stop = round(entry * (1 - STOP_PCT), 2)
                    take = math.ceil((entry + RISK_REWARD * (entry - stop)) * 100) / 100
                    raw_qty = risk.position_size(
                        portfolio.value({symbol: entry}), entry)
                    quantity = math.floor(raw_qty * 10000) / 10000
                    if quantity <= 0:
                        counts["skipped_too_small"] += 1
                        run_events.append({
                            "date": run_id, "event": "trade_skipped",
                            "symbol": symbol, "strategy": fired,
                            "reason": "position size rounds to zero",
                            "paper_only": True})
                    else:
                        trade = engine.place_order(
                            symbol, "buy", quantity, entry, stop, take,
                            reason=f"{fired} mean-reversion trigger, "
                                   f"exit variant {STRATEGY_ID}",
                            source="live-paper")
                        if trade is None:
                            counts["blocked_by_risk"] += 1
                            state["blocked_count"] = state.get("blocked_count", 0) + 1
                            reasons = engine.blocked[-1]["reasons"] if engine.blocked else []
                            run_events.append({
                                "date": run_id, "event": "trade_blocked",
                                "symbol": symbol, "strategy": fired,
                                "entry_price": entry, "reasons": reasons,
                                "paper_only": True})
                        else:
                            positions[symbol] = {
                                "symbol": symbol, "strategy": fired,
                                "entry_date": bar_date, "entry_price": entry,
                                "quantity": quantity, "stop_loss": stop,
                                "take_profit": take, "bars_held": 0,
                            }
                            counts["trades_opened"] += 1
                            run_events.append({
                                "date": run_id, "event": "trade_opened",
                                "paper_only": True, **positions[symbol]})

            state["last_processed_bar_date"][symbol] = bar_date

    # Total fetch failure: no trades, no cash/position change — but
    # the failure counts ARE durable (they are the audit trail), so
    # save the state with them recorded. The log still records the
    # attempt (a log line is not state).
    if processed_symbols == [] and failed and len(failed) == len(symbols):
        state["run_history"].append({
            "run_date": run_id, "status": "fetch_failed",
            "trades_opened": 0, "trades_closed": 0,
            "realised_pnl_usd": 0.0, "symbols_processed": [],
            "symbols_no_new_bar": 0, "signals_seen": 0,
            "blocked_by_risk": 0, "skipped_too_small": 0,
            "failed_symbols": failed, "cash_usd": state["cash_usd"],
            "open_positions": len(state["open_positions"]),
            "closed_trades_total": len(state["closed_trades"]),
        })
        state["run_history"] = state["run_history"][-365:]
        save_state(live_dir, state)
        for event in run_events:
            append_log(live_dir, event)
        append_log(live_dir, {"date": run_id, "event": "run_failed",
                              "reason": "all symbols failed to fetch — "
                                        "no state change, no trades",
                              "failed_symbols": failed, "paper_only": True})
        return {"run_date": run_id, "status": "fetch_failed",
                "reason": "all symbols failed to fetch",
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
        "failed_symbols": failed,
        "cash_usd": state["cash_usd"],
        "open_positions": len(state["open_positions"]),
        "closed_trades_total": len(state["closed_trades"]),
    }
    state["run_history"].append(summary)
    state["run_history"] = state["run_history"][-365:]
    save_state(live_dir, state)
    for event in run_events:
        append_log(live_dir, event)
    append_log(live_dir, {"date": run_id, "event": "run_summary",
                          "paper_only": True, **summary})
    save_report(live_dir, state)
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
    per_symbol: dict[str, dict] = {}
    for t in closed:
        entry = per_symbol.setdefault(t["symbol"], {"trades": 0, "wins": 0, "pnl_usd": 0.0})
        entry["trades"] += 1
        entry["wins"] += 1 if t["pnl_usd"] > 0 else 0
        entry["pnl_usd"] = round(entry["pnl_usd"] + t["pnl_usd"], 2)
    return {
        "paper_only": True,
        "strategy": state.get("strategy", STRATEGY_ID),
        "started_on": state.get("started_on"),
        "last_run_date": state.get("last_run_date"),
        "runs": state.get("runs", 0),
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
        "per_symbol": per_symbol,
    }


def render_report(state: dict) -> str:
    s = compute_summary(state)
    lines = [
        "# VaultTec — Live Paper Trading (real days, paper only)",
        "",
        f"> **{PAPER_ONLY_BANNER}**",
        "",
        "## Strategy",
        "",
        f"- Variant: **{s['strategy']}** — 6% stop-loss / 9% take-profit "
        f"(1.5:1), 10-bar time exit, RSI + Bollinger mean-reversion, "
        f"long-only, balanced profile, $10,000 virtual cash.",
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
            "| Symbol | Strategy | Entry | Qty | Stop | Target | Bars held |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for p in state["open_positions"]:
            lines.append(
                f"| {p['symbol']} | {p['strategy']} | ${p['entry_price']:,.2f} "
                f"({p['entry_date']}) | {p['quantity']} | ${p['stop_loss']:,.2f} | "
                f"${p['take_profit']:,.2f} | {p['bars_held']} |")
        lines.append("")
    if state.get("closed_trades"):
        lines += [
            "## Closed trades (every trade, in order)",
            "",
            "| # | Symbol | Strategy | Entry | Exit | Reason | Days | P&L ($) |",
            "|---:|---|---|---|---|---|---|---:|",
        ]
        for i, t in enumerate(state["closed_trades"], 1):
            lines.append(
                f"| {i} | {t['symbol']} | {t['strategy']} | "
                f"${t['entry_price']:,.2f} ({t['entry_date']}) | "
                f"${t['exit_price']:,.2f} ({t['exit_date']}) | "
                f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
        lines.append("")
    if s["per_symbol"]:
        lines += ["## Per-symbol (closed trades)", ""]
        for symbol, r in sorted(s["per_symbol"].items()):
            lines.append(f"- {symbol}: {r['trades']} trades, {r['wins']} wins, "
                         f"P&L ${r['pnl_usd']:+,.2f}")
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
        "Live paper trades arrive one day at a time and cannot be "
        "re-run — that is the point. A good run here still does not "
        "prove future profits, and a compliance/legal review is still "
        "required before any real money is considered. Past "
        "performance does not guarantee future results.",
        "",
    ]
    return "\n".join(lines)


def save_report(live_dir: str | Path, state: dict) -> Path:
    path = Path(live_dir) / REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(state), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VaultTec live paper trading — one day at a time, "
                    "paper only. No broker, no real money.")
    parser.add_argument("--date", default=None,
                        help="run date YYYY-MM-DD (America/New_York); "
                             "default: today")
    parser.add_argument("--state-dir", default=None,
                        help="live_paper directory (default: vaulttec/live_paper)")
    args = parser.parse_args(argv)
    run_date = date.fromisoformat(args.date) if args.date else None
    live_dir = Path(args.state_dir) if args.state_dir else default_live_dir()
    summary = run_live_day(run_date=run_date, live_dir=live_dir)
    print(f"PAPER ONLY — live paper run {summary['run_date']}: {summary['status']}")
    print(f"Symbols processed: {summary['symbols_processed'] or 'none'}")
    print(f"Trades opened: {summary['trades_opened']} — "
          f"closed: {summary['trades_closed']} — realised P&L: "
          f"${summary['realised_pnl_usd']:+,.2f}")
    if summary["failed_symbols"]:
        print(f"Fetch failures: {summary['failed_symbols']}")
    print(f"Report: {live_dir / REPORT_FILE}")
    print(f"State: {live_dir / STATE_FILE} — Log: {live_dir / LOG_FILE}")
    return 0 if summary["status"] in ("ok", "already_processed", "stopped") else 2


if __name__ == "__main__":
    sys.exit(main())
