"""Intraday paper trading over real market hours — paper only.

The daily live-paper runner (``live_paper_trading.py``) trades once
a day, after the close, on daily bars. This module is its
market-hours twin: it runs throughout the open market
(9:30am–4:00pm ET), fetching hourly bars for the same 12-symbol
universe via yfinance, and processes only *completed* hourly bars,
in order, with no look-ahead. A run at 10:35 processes the 9:30
bar (it finished at 10:30); a run at 16:35 processes the final
15:30 bar and writes the session report.

The same wide-6 rules as the daily runner — 6% stop / 9% target,
1.5:1, RSI + Bollinger mean-reversion, long-only, balanced
profile, PaperTradingEngine + Risk Engine — but on an hourly clock
and in a SEPARATE state dir (``live_paper_intraday/``) with a
SEPARATE $10,000 virtual pot, so intraday numbers never mix with
the daily runner's state.

Honest limits — read before trusting any intraday number
---------------------------------------------------------
- The wide-6 rules were VALIDATED on daily bars (Phase 4c/4d).
  The same rules on hourly bars are a different regime and are
  NOT validated: RSI-14 means 14 hours here, not 14 days, and
  Bollinger-20 means 20 hours. Treat intraday results as an
  experiment, not as evidence the strategy works intraday.
- A 6% stop / 9% target almost never triggers inside one market
  session: a stock has to move 6–9% in a day. So most intraday
  wins and losses come from MULTI-DAY holds — a position opened
  on Monday that hits its stop or target on Thursday. The per-
  session report therefore counts ONLY trades that CLOSED during
  that session. Open positions are listed, with their unrealised
  value clearly labelled, and are NEVER counted as wins or losses.
- The 10-bar time exit is measured in SESSIONS here, not hours:
  a position exits at the first processed bar of its 11th
  session (the hourly mirror of the daily runner's 10-bar exit).
  Ten hourly bars would close a trade after ~1.5 sessions, which
  would contradict the multi-day-hold reality above.
- Only bars inside the market session count: a bar whose start
  time (New York) is 9:30am–3:30pm for stocks. Crypto trades
  24/7, but this runner only watches the same 9:30–4:00 ET
  session, matching the stock market — overnight crypto bars are
  ignored, and the indicators run on the session-only hourly
  series (7 bars a day for stocks, 6 for crypto, whose Yahoo
  hourly bars start on the hour). A market holiday still has
  crypto bars, so crypto may trade on holidays; stocks have no
  bars and are skipped.
- Yahoo's free intraday data is delayed ~15 minutes and rate
  limits are the known failure mode (the daily runner already
  hits them). A missed hour is picked up by the next run — the
  runner is idempotent per hour — but more runs a day means more
  chances a fetch fails. A failure is recorded, never replaced
  with sample data, never invented.

How it works
------------
- Each run fetches the last 60 days of hourly bars (the most
  yfinance serves at 1h) per symbol, keeps only in-session bars,
  and processes every completed hourly bar not yet processed, in
  order. A bar counts as completed only when its hour has fully
  ended before the run time, so a still-forming bar is never
  traded on.
- For each new bar, per symbol, in order: first check any open
  position against that bar (stop-loss on the bar's low, then
  take-profit on the bar's high, then the 10-session time exit),
  then — only if no position is open — evaluate the RSI /
  Bollinger trigger on history up to and including that bar (no
  look-ahead). A triggered trade goes through the real
  PaperTradingEngine and Risk Engine with the wide-6 rules.
- State is durable on disk (``live_paper_intraday/state.json``):
  cash, open positions (with bars and sessions held), closed
  trades, per-symbol last processed bar (an ISO timestamp), run
  history. A second run in the same hour finds no new completed
  bars and does nothing — the runner is idempotent per hour.
  Every decision is appended to ``live_paper_intraday/trades.jsonl``
  and the running report is regenerated each run.
- The daily-loss limit in the Risk Engine is reset once per
  session (not per bar), so it applies across a whole market
  session. On a catch-up run that spans two sessions, the tally
  resets once per session as the bars are processed.
- Kill-switch: create ``live_paper_intraday/STOP`` (or set
  ``enabled`` to false in the state file) and the next run does
  nothing at all except log that it was stopped. Delete the file
  to resume. Stopping freezes the run — open positions stay open
  until the runner is resumed and their exit bars arrive.

Hard rules (same as every phase before this one)
------------------------------------------------
- PAPER ONLY. No broker is ever contacted, no brokerage account
  is created, no real money moves, no leverage, no options.
- Every trade keeps its stop-loss. The stop is never removed.
- Past performance does not guarantee future results. A good
  intraday run still needs a compliance/legal review before real
  money is ever considered.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from .config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from .db.models import PaperTrade, UserProfile
from .live_paper_trading import (
    HORIZON_BARS,
    RISK_PROFILE,
    RISK_REWARD,
    STOP_PCT,
    TAKE_PCT,
    _live_trigger,
    check_exit,
)
from .market.data import SCAN_UNIVERSE
from .paper_trading import PaperTradingEngine
from .portfolio.manager import Portfolio
from .risk import RiskEngine
from .analytics.mean_reversion import STRATEGIES

# --- The live strategy: wide-6, exactly as validated on daily bars ---
STRATEGY_ID = "wide-6"
# Time exit measured in SESSIONS (trading days), not hourly bars:
# mirrors the daily runner's 10-bar exit. A position exits at the
# first processed bar of its 11th session (10 full sessions held).
HORIZON_SESSIONS = HORIZON_BARS
STARTING_CASH = PAPER_STARTING_CASH
HISTORY_PERIOD = "60d"  # most yfinance serves at 1h interval
FETCH_RETRIES = 3
NY_TZ = ZoneInfo("America/New_York")
BAR = timedelta(hours=1)
SESSION_OPEN = dtime(9, 30)
SESSION_CLOSE = dtime(16, 0)

INTRADAY_DIR_NAME = "live_paper_intraday"
STATE_FILE = "state.json"
LOG_FILE = "trades.jsonl"
REPORT_FILE = "live-paper-intraday-report.md"
STOP_FILE = "STOP"

PAPER_ONLY_BANNER = (
    "PAPER ONLY — virtual money, no live brokerage, no real money. "
    "Trading involves substantial risk of loss. This intraday paper "
    "run does not promise profits. Past performance does not "
    "guarantee future results."
)


def _usd(value: float) -> float:
    """Round to cents, normalising -0.0 to 0.0 so a flat position
    never renders as -$0.00 (entries are stored unrounded, last
    closes rounded — the dust is real arithmetic, not a loss)."""
    out = round(float(value), 2)
    return 0.0 if out == 0 else out


def default_intraday_dir() -> Path:
    """live_paper_intraday/ next to this package's project root.

    This module lives at vaulttec/intraday_paper_trading.py, so
    parents[1] is the project root (vaulttec/).
    """
    return Path(__file__).resolve().parents[1] / INTRADAY_DIR_NAME


def session_of(bar_start: datetime) -> date:
    """The market session a bar belongs to: its start date (NY)."""
    return bar_start.date()


class LiveIntradayProvider:
    """Delayed real hourly history for the live run via yfinance.

    Fetches the last 60 days at 1h interval (the most yfinance
    serves at that granularity). The frame's DatetimeIndex is
    converted to naive America/New_York datetimes, matching the
    rest of the codebase. Retries 3 times with backoff; a symbol
    that still cannot be fetched raises, and the caller records it
    as failed — it is never silently replaced with sample data.
    """

    def __init__(self, run_time: datetime | None = None):
        self.run_time = run_time or datetime.now(NY_TZ)

    def get_history(self, symbol: str, days: int | None = None) -> pd.DataFrame:
        import yfinance as yf

        last_error: Exception | None = None
        df = None
        for attempt in range(FETCH_RETRIES):
            try:
                df = yf.Ticker(symbol).history(
                    period=HISTORY_PERIOD, interval="1h")
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
            "Datetime": "date", "Date": "date", "Open": "open",
            "High": "high", "Low": "low", "Close": "close",
            "Volume": "volume",
        })
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"]
                if c in df.columns]
        df = df[cols]
        # yfinance intraday index is tz-aware (NY for stocks, UTC for
        # crypto); convert to New York and strip the tz so comparisons
        # stay tz-naive, like the sample provider and the daily runner.
        # If the index ever arrives naive, treat it as New York time.
        dates = pd.to_datetime(df["date"])
        if dates.dt.tz is None:
            dates = dates.dt.tz_localize(NY_TZ)
        else:
            dates = dates.dt.tz_convert(NY_TZ)
        df["date"] = dates.dt.tz_localize(None)
        time.sleep(1.0)  # be polite to the free data feed
        return df


# --- Session filtering and completed bars -------------------------------

def _in_session_bars(history: pd.DataFrame) -> pd.DataFrame:
    """Only bars whose start time (New York) falls inside the
    market session, 9:30am–4:00pm. A bar starting at 9:30, 10:30,
    ..., 15:30 counts; a bar starting before 9:30 or at/after
    16:00 does not. Overnight crypto bars are ignored, so the
    indicators run on a session-only hourly series. Sorted,
    de-duplicated."""
    df = history.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    starts = df["date"].dt.time
    df = df[(starts >= SESSION_OPEN) & (starts < SESSION_CLOSE)]
    df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    return df.reset_index(drop=True)


def _completed_hourly_bars(history: pd.DataFrame,
                           run_time: datetime) -> pd.DataFrame:
    """Only in-session bars whose hour has fully ended before the
    run time — a still-forming bar is never traded on. A bar
    starting 09:30 is complete at 10:30, not before."""
    df = _in_session_bars(history)
    cutoff = run_time - BAR
    df = df[df["date"] <= cutoff]
    return df.reset_index(drop=True)


def _unprocessed_hourly_bars(history: pd.DataFrame, run_time: datetime,
                             last_processed: str | None
                             ) -> tuple[pd.DataFrame, str | None, bool]:
    """The completed bars this run should process, in order.

    First ever run for a symbol (``last_processed`` None): all
    earlier bars are warm-up only — the latest completed bar is
    the first trading hour, so initialise ``last_processed`` to the
    second-latest completed bar and process only the latest one.
    Returns (bars_to_process, new_last_processed_if_no_bars,
    was_initialised). ``last_processed`` is an ISO timestamp
    ("2026-11-10T10:30:00"), not a date.
    """
    completed = _completed_hourly_bars(history, run_time)
    if completed.empty:
        return completed, last_processed, False
    if last_processed is None:
        if len(completed) >= 2:
            init_to = completed["date"].iloc[-2].isoformat()
            return completed.iloc[[-1]], init_to, True
        return completed, None, True
    last = pd.Timestamp(last_processed)
    mask = completed["date"] > last
    return completed[mask].reset_index(drop=True), last_processed, False


# --- State ---------------------------------------------------------------

def fresh_state(started_on: str) -> dict:
    """A brand-new intraday paper state: $10,000 virtual cash, no
    positions, nothing processed yet. Kept SEPARATE from the daily
    runner's state — a different directory, a different pot."""
    return {
        "version": 1,
        "paper_only": True,
        "strategy": STRATEGY_ID,
        "stop_pct": STOP_PCT,
        "take_pct": TAKE_PCT,
        "horizon_sessions": HORIZON_SESSIONS,
        "risk_profile": RISK_PROFILE,
        "starting_cash_usd": STARTING_CASH,
        "cash_usd": STARTING_CASH,
        "enabled": True,
        "started_on": started_on,
        "last_run": None,  # ISO datetime of the last run
        "last_session": None,  # ISO date of the last session processed
        "runs": 0,
        "last_processed_bar": {},  # symbol -> ISO timestamp of last bar processed
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


# --- Engine reconstruction -----------------------------------------------

def _build_engine(state: dict) -> tuple[Portfolio, RiskEngine, PaperTradingEngine]:
    """Rebuild the in-memory paper engine from durable state, so a
    run resumes exactly where the last one left off: same cash, same
    holdings, same open trades (so close_position can mark them).
    Trades are rebuilt with source "live-paper-intraday" so the
    session report says whose trades they are."""
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
        from .portfolio.manager import Holding

        portfolio.holdings[pos["symbol"]] = Holding(
            symbol=pos["symbol"], quantity=pos["quantity"],
            avg_cost=pos["entry_price"])
        engine.trades.append(PaperTrade(
            symbol=pos["symbol"], side="buy", quantity=pos["quantity"],
            price=pos["entry_price"], stop_loss=pos["stop_loss"],
            take_profit=pos["take_profit"],
            reason=f"{pos['strategy']} mean-reversion trigger, exit variant {STRATEGY_ID}",
            source="live-paper-intraday", status="open"))
    return portfolio, risk, engine


# --- The intraday run -----------------------------------------------------

def run_intraday(run_time: datetime | None = None, provider=None,
                 live_dir: str | Path | None = None,
                 symbols: list[str] | None = None) -> dict:
    """Run one intraday paper hour.

    ``run_time`` defaults to now (America/New_York). ``provider``
    may be injected (tests use a stub — the real run uses yfinance).
    Returns a summary dict; the durable state, log and report are
    written as a side effect (except on total fetch failure, where
    the state is left untouched).
    """
    run_time = run_time or datetime.now(NY_TZ)
    if run_time.tzinfo is None:
        run_time = run_time.replace(tzinfo=NY_TZ)
    run_time = run_time.astimezone(NY_TZ).replace(tzinfo=None)
    live_dir = Path(live_dir) if live_dir else default_intraday_dir()
    live_dir.mkdir(parents=True, exist_ok=True)
    symbols = symbols or list(SCAN_UNIVERSE)
    run_id = run_time.isoformat(timespec="minutes")
    session_str = run_time.date().isoformat()

    # Kill-switch: STOP file, or enabled=false in state. Log it and
    # do nothing at all — no fetch, no trades. Open positions stay
    # open until the runner is resumed and their exit bars arrive.
    state = load_state(live_dir)
    if (live_dir / STOP_FILE).exists() or not state.get("enabled", True):
        event = {"date": run_id, "session": session_str,
                 "event": "run_stopped",
                 "reason": "kill-switch active (live_paper_intraday/STOP "
                           "exists or state enabled=false) — no fetch, "
                           "no trades",
                 "paper_only": True}
        append_log(live_dir, event)
        return {"run_time": run_id, "session": session_str,
                "status": "stopped",
                "reason": event["reason"], "trades_opened": 0,
                "trades_closed": 0, "realised_pnl_usd": 0.0,
                "session_wins": 0, "session_losses": 0,
                "session_pnl_usd": 0.0, "total_pnl_usd": 0.0,
                "symbols_processed": [], "failed_symbols": {}}

    if provider is None:
        provider = LiveIntradayProvider(run_time)

    portfolio, risk, engine = _build_engine(state)
    positions = {p["symbol"]: dict(p) for p in state["open_positions"]}
    counts: Counter = Counter()
    failed: dict[str, str] = {}
    processed_symbols: list[str] = []
    run_events: list[dict] = []
    reset_sessions: set[str] = set()

    for symbol in symbols:
        try:
            history = provider.get_history(symbol)
        except Exception as exc:  # noqa: BLE001 — record, never invent data
            failed[symbol] = f"{type(exc).__name__}: {exc}"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            run_events.append({"date": run_id, "session": session_str,
                               "event": "fetch_failed",
                               "symbol": symbol, "error": failed[symbol],
                               "paper_only": True})
            continue
        if history is None or history.empty or "close" not in history.columns:
            failed[symbol] = "empty history returned"
            state["fetch_failures"][symbol] = state["fetch_failures"].get(symbol, 0) + 1
            run_events.append({"date": run_id, "session": session_str,
                               "event": "fetch_failed",
                               "symbol": symbol, "error": failed[symbol],
                               "paper_only": True})
            continue

        last_processed = state["last_processed_bar"].get(symbol)
        bars, init_to, initialised = _unprocessed_hourly_bars(
            history, run_time, last_processed)
        if initialised and init_to is not None:
            # Warm-up bars are never traded: mark them processed.
            state["last_processed_bar"][symbol] = init_to
        if bars.empty:
            # No new completed bar (already run this hour, weekend,
            # holiday, or the session has not started yet) — nothing
            # to do for this symbol.
            counts["symbols_no_new_bar"] += 1
            continue
        processed_symbols.append(symbol)

        for row_idx in range(len(bars)):
            bar = bars.iloc[row_idx]
            bar_start = pd.Timestamp(bar["date"]).to_pydatetime()
            bar_id = bar_start.isoformat()
            bar_session = session_of(bar_start).isoformat()
            history_to_bar = history.copy()
            history_to_bar["date"] = pd.to_datetime(
                history_to_bar["date"]).dt.tz_localize(None)
            # In-session history up to and including this bar only —
            # no look-ahead, and no overnight bars in the indicators.
            history_to_bar = _in_session_bars(history_to_bar)
            history_to_bar = history_to_bar[
                history_to_bar["date"] <= bar_start
            ].reset_index(drop=True)
            state["last_close"][symbol] = round(float(bar["close"]), 2)
            # A new session is a new day for the loss limit: the
            # Risk Engine's daily-loss tally resets once per session.
            if bar_session not in reset_sessions:
                engine.realised_pnl = 0.0
                reset_sessions.add(bar_session)

            # 1) Exit check first, for any open position.
            position = positions.get(symbol)
            exited_this_bar = False
            if position is not None:
                if position.get("last_session") != bar_session:
                    position["sessions_held"] = int(
                        position.get("sessions_held", 0)) + 1
                    position["last_session"] = bar_session
                position["bars_held"] = int(position.get("bars_held", 0)) + 1
                exit_hit = check_exit(bar, position)
                if exit_hit is None and position["sessions_held"] >= HORIZON_SESSIONS:
                    exit_hit = (round(float(bar["close"]), 2),
                                f"time exit ({HORIZON_SESSIONS} sessions)")
                if exit_hit is not None:
                    exit_price, exit_reason = exit_hit
                    pnl = engine.close_position(symbol, exit_price, exit_reason)
                    pnl = 0.0 if pnl is None else round(float(pnl), 2)
                    closed = {
                        "symbol": symbol, "strategy": position["strategy"],
                        "entry_date": position["entry_date"],
                        "entry_bar": position["entry_bar"],
                        "entry_price": position["entry_price"],
                        "exit_date": bar_session, "exit_bar": bar_id,
                        "exit_session": bar_session,
                        "exit_price": exit_price,
                        "quantity": position["quantity"],
                        "stop_loss": position["stop_loss"],
                        "take_profit": position["take_profit"],
                        "exit_reason": exit_reason,
                        "bars_held": position["bars_held"],
                        "sessions_held": position["sessions_held"],
                        "days_held": position["sessions_held"],
                        "pnl_usd": pnl,
                    }
                    state["closed_trades"].append(closed)
                    del positions[symbol]
                    exited_this_bar = True
                    counts["trades_closed"] += 1
                    counts["realised_pnl_usd"] = round(
                        counts.get("realised_pnl_usd", 0.0) + pnl, 2)
                    run_events.append({"date": run_id, "session": bar_session,
                                       "event": "trade_closed",
                                       "paper_only": True, **closed})

            # 2) Entry check — only if no position is open now, and
            # not on a bar where this symbol just exited: buying back
            # into the same hour it just stopped out of would churn,
            # and the validated walk-forward never re-entered inside
            # one window.
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
                            "date": run_id, "session": bar_session,
                            "event": "trade_skipped",
                            "symbol": symbol, "strategy": fired,
                            "reason": "position size rounds to zero",
                            "paper_only": True})
                    else:
                        trade = engine.place_order(
                            symbol, "buy", quantity, entry, stop, take,
                            reason=f"{fired} mean-reversion trigger, "
                                   f"exit variant {STRATEGY_ID}",
                            source="live-paper-intraday")
                        if trade is None:
                            counts["blocked_by_risk"] += 1
                            state["blocked_count"] = state.get("blocked_count", 0) + 1
                            reasons = engine.blocked[-1]["reasons"] if engine.blocked else []
                            run_events.append({
                                "date": run_id, "session": bar_session,
                                "event": "trade_blocked",
                                "symbol": symbol, "strategy": fired,
                                "entry_price": entry, "reasons": reasons,
                                "paper_only": True})
                        else:
                            positions[symbol] = {
                                "symbol": symbol, "strategy": fired,
                                "entry_date": bar_session, "entry_bar": bar_id,
                                "entry_price": entry,
                                "quantity": quantity, "stop_loss": stop,
                                "take_profit": take, "bars_held": 0,
                                "sessions_held": 0,
                                "last_session": bar_session,
                            }
                            counts["trades_opened"] += 1
                            run_events.append({
                                "date": run_id, "session": bar_session,
                                "event": "trade_opened",
                                "paper_only": True,
                                **{k: v for k, v in positions[symbol].items()
                                   if k != "last_session"}})

            state["last_processed_bar"][symbol] = bar_id

    # Total fetch failure: no trades, no cash/position change — but
    # the failure counts ARE durable (they are the audit trail), so
    # save the state with them recorded. The log still records the
    # attempt (a log line is not state).
    session_now = session_summary(state, session_str)
    if processed_symbols == [] and failed and len(failed) == len(symbols):
        state["run_history"].append({
            "run_time": run_id, "session": session_str,
            "status": "fetch_failed",
            "trades_opened": 0, "trades_closed": 0,
            "realised_pnl_usd": 0.0, "symbols_processed": [],
            "symbols_no_new_bar": 0, "signals_seen": 0,
            "blocked_by_risk": 0, "skipped_too_small": 0,
            "session_wins": 0, "session_losses": 0,
            "session_pnl_usd": 0.0,
            "failed_symbols": failed, "cash_usd": state["cash_usd"],
            "open_positions": len(state["open_positions"]),
            "closed_trades_total": len(state["closed_trades"]),
        })
        state["run_history"] = state["run_history"][-365:]
        save_state(live_dir, state)
        for event in run_events:
            append_log(live_dir, event)
        append_log(live_dir, {"date": run_id, "session": session_str,
                              "event": "run_failed",
                              "reason": "all symbols failed to fetch — "
                                        "no state change, no trades",
                              "failed_symbols": failed, "paper_only": True})
        return {"run_time": run_id, "session": session_str,
                "status": "fetch_failed",
                "reason": "all symbols failed to fetch",
                "trades_opened": 0, "trades_closed": 0,
                "realised_pnl_usd": 0.0,
                "session_wins": 0, "session_losses": 0,
                "session_pnl_usd": 0.0,
                "total_pnl_usd": session_now["total_pnl_usd"],
                "symbols_processed": [],
                "failed_symbols": failed}

    # Sync durable state from the engine.
    state["cash_usd"] = round(float(portfolio.cash), 2)
    state["open_positions"] = [positions[s] for s in sorted(positions)]
    state["last_run"] = run_id
    state["last_session"] = session_str
    state["runs"] = int(state.get("runs", 0)) + 1
    status = "already_processed" if not processed_symbols else "ok"
    session_now = session_summary(state, session_str)
    summary = {
        "run_time": run_id,
        "session": session_str,
        "status": status,
        "trades_opened": int(counts["trades_opened"]),
        "trades_closed": int(counts["trades_closed"]),
        "realised_pnl_usd": _usd(counts.get("realised_pnl_usd", 0.0)),
        "session_wins": session_now["wins"],
        "session_losses": session_now["losses"],
        "session_pnl_usd": session_now["session_pnl_usd"],
        "total_pnl_usd": session_now["total_pnl_usd"],
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
    append_log(live_dir, {"date": run_id, "session": session_str,
                          "event": "run_summary",
                          "paper_only": True, **summary})
    save_report(live_dir, state)
    return summary


# --- Reporting ---------------------------------------------------------------

def session_summary(state: dict, session_date: str) -> dict:
    """This session's numbers, in Neko's daily-report format.

    ONLY trades that CLOSED during ``session_date`` count as wins
    or losses. Open positions are listed with their unrealised
    value, clearly labelled — they are NEVER wins or losses.
    ``session_date`` is an ISO date ("2026-11-10").
    """
    closed = [t for t in state.get("closed_trades", [])
              if t.get("exit_session") == session_date
              or t.get("exit_date") == session_date]
    wins = [t for t in closed if t["pnl_usd"] > 0]
    losses = [t for t in closed if t["pnl_usd"] <= 0]
    session_pnl = _usd(sum(t["pnl_usd"] for t in closed))
    total_pnl = _usd(sum(t["pnl_usd"] for t in state.get("closed_trades", [])))
    last_close = state.get("last_close", {})
    open_positions = []
    for p in state.get("open_positions", []):
        last = last_close.get(p["symbol"], p["entry_price"])
        open_positions.append({
            "symbol": p["symbol"], "strategy": p["strategy"],
            "entry_date": p["entry_date"], "entry_price": p["entry_price"],
            "quantity": p["quantity"],
            "stop_loss": p["stop_loss"], "take_profit": p["take_profit"],
            "sessions_held": p.get("sessions_held", 0),
            "bars_held": p.get("bars_held", 0),
            "last_close": last,
            "unrealised_pnl_usd": _usd(
                (last - p["entry_price"]) * p["quantity"]),
        })
    return {
        "paper_only": True,
        "session": session_date,
        "wins": len(wins),
        "losses": len(losses),
        "closed": len(closed),
        "session_pnl_usd": session_pnl,
        "total_pnl_usd": total_pnl,
        "closed_trades": closed,
        "open_positions": open_positions,
        "open_count": len(open_positions),
        "unrealised_pnl_usd": _usd(
            sum(p["unrealised_pnl_usd"] for p in open_positions)),
    }


def compute_summary(state: dict) -> dict:
    """Portfolio summary from durable state (no network, no engine)."""
    closed = state.get("closed_trades", [])
    wins = [t for t in closed if t["pnl_usd"] > 0]
    losses = [t for t in closed if t["pnl_usd"] <= 0]
    total_pnl = _usd(sum(t["pnl_usd"] for t in closed))
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
    latest_session = state.get("last_session")
    return {
        "paper_only": True,
        "strategy": state.get("strategy", STRATEGY_ID),
        "started_on": state.get("started_on"),
        "last_run": state.get("last_run"),
        "last_session": latest_session,
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
        "latest_session": (
            session_summary(state, latest_session) if latest_session else None),
    }


def render_session_report(state: dict, session_date: str) -> str:
    """One market session, in plain language, in Neko's format:
    wins and losses that closed in the session, total profit so
    far, open positions listed as still open — never as wins or
    losses."""
    s = session_summary(state, session_date)
    lines = [
        f"# VaultTec — Intraday Paper, session {session_date}",
        "",
        f"> **{PAPER_ONLY_BANNER}**",
        "",
        "## This session",
        "",
        f"- Wins: **{s['wins']}** — losses: **{s['losses']}**",
        f"- Profit this session: **${s['session_pnl_usd']:+,.2f}**",
        f"- Total profit so far: **${s['total_pnl_usd']:+,.2f}**",
        "",
    ]
    if s["closed_trades"]:
        lines += [
            "## Trades that closed this session",
            "",
            "| Symbol | Strategy | Entry | Exit | Reason | Sessions held | P&L ($) |",
            "|---|---|---|---|---|---:|---:|",
        ]
        for t in s["closed_trades"]:
            lines.append(
                f"| {t['symbol']} | {t['strategy']} | "
                f"${t['entry_price']:,.2f} ({t['entry_date']}) | "
                f"${t['exit_price']:,.2f} ({t['exit_date']}) | "
                f"{t['exit_reason']} | {t.get('sessions_held', t.get('days_held', 0))} | "
                f"{t['pnl_usd']:+,.2f} |")
        lines.append("")
    else:
        lines += [
            "No trades closed this session. A 6% stop / 9% target "
            "almost never triggers inside one day — most wins and "
            "losses here come from holds across several sessions.",
            "",
        ]
    if s["open_positions"]:
        lines += [
            "## Still open — not wins or losses",
            "",
            "| Symbol | Strategy | Entry | Last close | Stop | Target | Sessions held | Unrealised ($) |",
            "|---|---|---|---|---:|---:|---:|---:|---:|",
        ]
        for p in s["open_positions"]:
            lines.append(
                f"| {p['symbol']} | {p['strategy']} | "
                f"${p['entry_price']:,.2f} ({p['entry_date']}) | "
                f"${p['last_close']:,.2f} | ${p['stop_loss']:,.2f} | "
                f"${p['take_profit']:,.2f} | {p['sessions_held']} | "
                f"{p['unrealised_pnl_usd']:+,.2f} |")
        lines.append("")
        lines.append(
            f"Unrealised total: ${s['unrealised_pnl_usd']:+,.2f} — paper "
            f"value on paper positions only, not profit.")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        "These are paper trades on delayed prices, and the wide-6 "
        "rules were validated on daily bars, not hourly ones. A good "
        "session here still does not prove future profits, and a "
        "compliance/legal review is still required before any real "
        "money is considered. Past performance does not guarantee "
        "future results.",
        "",
    ]
    return "\n".join(lines)


def render_report(state: dict) -> str:
    s = compute_summary(state)
    lines = [
        "# VaultTec — Intraday Live Paper Trading (market hours, paper only)",
        "",
        f"> **{PAPER_ONLY_BANNER}**",
        "",
        "## Strategy",
        "",
        f"- Variant: **{s['strategy']}** — 6% stop-loss / 9% take-profit "
        f"(1.5:1), 10-session time exit, RSI + Bollinger mean-reversion "
        f"on hourly bars, long-only, balanced profile, $10,000 virtual "
        f"cash — a SEPARATE pot from the daily runner.",
        f"- Started: {s['started_on'] or 'not started yet'} — "
        f"last run: {s['last_run'] or 'never'} — "
        f"runs completed: {s['runs']}.",
        f"- Data: delayed real hourly prices via yfinance (free, 60d "
        f"max at 1h). Only completed in-session bars are traded, "
        f"history up to the processed bar only — no look-ahead.",
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
    latest = s.get("latest_session")
    if latest is not None:
        lines += [
            f"## This session — {latest['session']}",
            "",
            f"- Wins: **{latest['wins']}** — losses: **{latest['losses']}**",
            f"- Profit this session: **${latest['session_pnl_usd']:+,.2f}**",
            f"- Total profit so far: **${latest['total_pnl_usd']:+,.2f}**",
            f"- Still open (not wins or losses): {latest['open_count']} "
            f"position(s), unrealised "
            f"${latest['unrealised_pnl_usd']:+,.2f}",
            "",
        ]
    if state.get("open_positions"):
        lines += [
            "## Open positions",
            "",
            "| Symbol | Strategy | Entry | Qty | Stop | Target | Sessions held | Bars held |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for p in state["open_positions"]:
            lines.append(
                f"| {p['symbol']} | {p['strategy']} | ${p['entry_price']:,.2f} "
                f"({p['entry_date']}) | {p['quantity']} | ${p['stop_loss']:,.2f} | "
                f"${p['take_profit']:,.2f} | {p.get('sessions_held', 0)} | "
                f"{p.get('bars_held', 0)} |")
        lines.append("")
    if state.get("closed_trades"):
        lines += [
            "## Closed trades (every trade, in order)",
            "",
            "| # | Symbol | Strategy | Entry | Exit | Reason | Sessions | P&L ($) |",
            "|---:|---|---|---|---|---|---:|---:|",
        ]
        for i, t in enumerate(state["closed_trades"], 1):
            lines.append(
                f"| {i} | {t['symbol']} | {t['strategy']} | "
                f"${t['entry_price']:,.2f} ({t['entry_date']}) | "
                f"${t['exit_price']:,.2f} ({t['exit_date']}) | "
                f"{t['exit_reason']} | {t.get('sessions_held', t.get('days_held', 0))} | "
                f"{t['pnl_usd']:+,.2f} |")
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
                f"- {run.get('run_time', run.get('run_date', ''))}: "
                f"{run['status']} — opened {run['trades_opened']}, closed "
                f"{run['trades_closed']}, realised P&L "
                f"${run['realised_pnl_usd']:+,.2f}, processed "
                f"{run['symbols_processed'] or 'no symbols'}, failed: "
                f"{run['failed_symbols'] or 'none'}")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        "Intraday paper trades arrive one hour at a time and cannot "
        "be re-run — that is the point. The wide-6 rules were "
        "validated on daily bars, not hourly ones, so a good session "
        "here proves even less than a good day on the daily runner. "
        "A compliance/legal review is still required before any real "
        "money is considered. Past performance does not guarantee "
        "future results.",
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
        description="VaultTec intraday paper trading — market hours, "
                    "paper only. No broker, no real money.")
    parser.add_argument("--datetime", default=None,
                        help="run time YYYY-MM-DDTHH:MM (America/New_York); "
                             "default: now")
    parser.add_argument("--state-dir", default=None,
                        help="live_paper_intraday directory "
                             "(default: vaulttec/live_paper_intraday)")
    parser.add_argument("--session", default=None,
                        help="print the session report for YYYY-MM-DD "
                             "instead of running (no fetch, no trades)")
    args = parser.parse_args(argv)
    live_dir = Path(args.state_dir) if args.state_dir else default_intraday_dir()
    if args.session is not None:
        state = load_state(live_dir)
        print(render_session_report(state, args.session))
        return 0
    run_time = (datetime.fromisoformat(args.datetime)
                if args.datetime else None)
    summary = run_intraday(run_time=run_time, live_dir=live_dir)
    print(f"PAPER ONLY — intraday run {summary['run_time']}: {summary['status']}")
    print(f"Session: {summary['session']} — "
          f"symbols processed: {summary['symbols_processed'] or 'none'}")
    print(f"Trades opened: {summary['trades_opened']} — "
          f"closed: {summary['trades_closed']} — realised P&L: "
          f"${summary['realised_pnl_usd']:+,.2f}")
    print(f"This session: {summary['session_wins']} wins, "
          f"{summary['session_losses']} losses, "
          f"session P&L ${summary['session_pnl_usd']:+,.2f} — "
          f"total profit so far ${summary['total_pnl_usd']:+,.2f}")
    if summary["failed_symbols"]:
        print(f"Fetch failures: {summary['failed_symbols']}")
    print(f"Report: {live_dir / REPORT_FILE}")
    print(f"State: {live_dir / STATE_FILE} — Log: {live_dir / LOG_FILE}")
    return 0 if summary["status"] in ("ok", "already_processed", "stopped") else 2


if __name__ == "__main__":
    sys.exit(main())
