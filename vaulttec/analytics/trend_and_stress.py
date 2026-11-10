"""Phase 5 — trend-following complement + one more fresh stress window.

Two tests, paper only, no broker, no real money, no leverage, no
options. Past performance does not guarantee future results.

Test (a) — trend-following complement.
Phase 4b/4c/4d showed wide-6 (6% stop / 9% target, 1.5:1, 10-day
exit) RSI/Bollinger mean-reversion is the leading variant, but it
is weakest in the falling OOS-2 window (Feb-Aug 2025): RSI wide-6
only +$63.26 there (42.9% win), Bollinger wide-6 +$482.00. The
question here is whether buying *with* the trend instead of
against the fall does better when prices are falling. Two trend
strategies, exactly as defined in ``analytics/backtest.py`` so the
entry rules are not tuned to these windows:

- sma: SMA crossover — buy when the 10-day SMA crosses ABOVE the
  30-day SMA (short average overtakes the long average).
- macd: MACD crossover — buy when the MACD line crosses ABOVE its
  9-day signal line.

Exits are wide-6 for both: 6% stop / 9% target (1.5:1) / 10-day
exit, through the real PaperTradingEngine and Risk Engine,
balanced profile, $10,000 virtual cash, long-only. Every variant
keeps a stop-loss; the stop is never removed.

Windows: the SAME windows used before — OOS-1/2/3, the Phase 4
window (re-run, labelled in-sample), and FRESH-1/2/3 — so each
trend result can be compared window-by-window with the
mean-reversion wide-6 figures already reported in Phase 4c
(pooled OOS: RSI wide-6 67 trades, 59.7% win, +$1,441.19;
Bollinger wide-6 40 trades, 65.0% win, +$880.48) and Phase 4d
(pooled fresh: RSI wide-6 73 trades, 61.6% win, +$1,226.24;
Bollinger wide-6 36 trades, 63.9% win, +$1,043.47). Those
mean-reversion numbers are quoted from the earlier reports, not
re-run here — the method is identical, so the comparison is
like-for-like, except for one deliberate difference, stated
below.

One deliberate method difference: the walk-forward step is EVERY
BAR (1 day) for trend entries, not the 5-day step used for
mean-reversion. A crossover is a single-bar event — the cross
happens on one day and is gone the next — so a 5-day step would
miss most entries by sampling past them. A mean-reversion trigger
(RSI < 30, price at the lower band) is a *state* that persists
for several days, so a 5-day step still catches it. Checking
every bar does not look ahead: the trigger uses history up to
the trade day only. Trade counts are therefore NOT directly
comparable between trend and mean-reversion (trend gets more
chances to be seen); P&L, win rate, and expectancy per trade
are the comparison, and the step difference is flagged wherever
the two are set side by side.

Test (b) — stress test on ONE more fresh window.
Wide-6 mean-reversion (RSI + Bollinger, baseline and wide-5 as
controls, exactly as in Phase 4d) on FRESH-4: 2022-09-12 ->
2023-03-10, a 180-calendar-day window that ends the day FRESH-3
starts (2023-03-10), so it touches no window used before and
goes earlier than FRESH-3. Same method as Phase 4d: delayed real
yfinance history, 70 days of warm-up, 12 symbols, 5-day
walk-forward steps, no look-ahead, real PaperTradingEngine +
Risk Engine, $10,000 virtual cash, long-only, 10-day exit.

Verdict rules — fixed before the run:
- (a) A trend strategy "beats mean-reversion in OOS-2" when its
  OOS-2 paper P&L is greater than BOTH mean-reversion wide-6
  OOS-2 figures (RSI +$63.26 and Bollinger +$482.00). It
  "beats mean-reversion pooled" when its pooled OOS-1/2/3 P&L
  is greater than both pooled OOS mean-reversion wide-6 figures
  (RSI +$1,441.19, Bollinger +$880.48). The same comparisons
  are also reported on the fresh windows (FRESH-1/2/3 pooled:
  RSI wide-6 +$1,226.24, Bollinger wide-6 +$1,043.47).
- (b) Wide-6 "holds up" on FRESH-4 when its FRESH-4 paper P&L
  is > $0 AND its win rate is > 40% (the 1.5:1 break-even).
  This is a SINGLE window, so it is weaker evidence than the
  Phase 4d rule (positive in at least 2 of 3 windows) — the
  report says so and does not claim a 3-window hold-up.

Fetched histories are cached to data/fresh-cache/ as they arrive
(reusing ``fresh_window.CachedDatedProvider``), so an interrupted
run resumes from disk. The FRESH-1/2/3 histories are already
cached from Phase 4d and are not re-fetched.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from ..db.models import UserProfile
from ..market.data import SCAN_UNIVERSE, YFinanceProvider
from ..market.indicators import macd, sma
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import max_drawdown_pct
from .exit_test import (
    STARTING_CASH,
    WARMUP_DAYS,
    _exit_trade_exit,
    variant_by_id,
)
from .fresh_window import (
    FRESH_VARIANT_IDS,
    FRESH_VARIANTS,
    FRESH_WINDOWS,
    CachedDatedProvider,
)
from .mean_reversion import (
    DatedYFinanceProvider,
    OOS_WINDOWS,
    STRATEGIES as MR_STRATEGIES,
    strategy_label as mr_strategy_label,
    trade_start_index,
)
from .validation import fetch_histories

# --- Trend strategies -------------------------------------------------
TREND_STRATEGIES: tuple[str, ...] = ("sma", "macd")
# Walk-forward step for trend entries: every bar. A crossover is a
# single-bar event; a 5-day step would sample past most entries.
TREND_STEP_DAYS = 1
TREND_HORIZON_DAYS = 10
WIDE6 = variant_by_id("wide-6")  # 6% stop / 9% target, 10-day exit

# Mean-reversion wide-6 reference figures, quoted from the Phase 4c
# (pooled OOS-1/2/3) and Phase 4d (pooled FRESH-1/2/3) reports —
# same method, same exits, same cash and profile. Not re-run here.
MR_WIDE6_REFERENCE = {
    "rsi": {
        "oos_pooled_pnl_usd": 1441.19,
        "oos_pooled_trades": 67,
        "oos_pooled_win_rate_pct": 59.7,
        "oos2_pnl_usd": 63.26,
        "oos2_win_rate_pct": 42.9,
        "fresh_pooled_pnl_usd": 1226.24,
        "fresh_pooled_trades": 73,
        "fresh_pooled_win_rate_pct": 61.6,
        "source": "Phase 4c (OOS) and Phase 4d (fresh) reports",
    },
    "bollinger": {
        "oos_pooled_pnl_usd": 880.48,
        "oos_pooled_trades": 40,
        "oos_pooled_win_rate_pct": 65.0,
        "oos2_pnl_usd": 482.00,
        "oos2_win_rate_pct": 69.2,
        "fresh_pooled_pnl_usd": 1043.47,
        "fresh_pooled_trades": 36,
        "fresh_pooled_win_rate_pct": 63.9,
        "source": "Phase 4c (OOS) and Phase 4d (fresh) reports",
    },
}

# --- Stress window ------------------------------------------------------
# One more fresh 180-calendar-day window, earlier than FRESH-3: it
# ends 2023-03-10, the day FRESH-3 starts, so it overlaps nothing
# used before (OOS-1/2/3, Phase 4 window, FRESH-1/2/3).
STRESS_WINDOW: tuple[str, str, str] = ("FRESH-4", "2022-09-12", "2023-03-10")
STRESS_WINDOWS: list[tuple[str, str, str]] = [STRESS_WINDOW]

# Verdict rule for the stress test (single window — weaker than the
# Phase 4d 3-window rule; see module docstring).
STRESS_BREAK_EVEN_WIN_RATE_PCT = 40.0


def trend_label(strategy: str) -> str:
    return {
        "sma": "SMA trend-following (buy SMA-10 cross above SMA-30)",
        "macd": "MACD trend-following (buy MACD cross above signal line)",
    }[strategy]


def trend_trigger(strategy: str, window_history: pd.DataFrame) -> bool:
    """True when the trend entry fires on the last bar of
    ``window_history`` — history up to the trade day only, so no
    look-ahead. A crossover is judged on the last two bars: the
    fast line above the slow line today, at or below it yesterday.
    Returns False when either line is not yet defined."""
    closes = window_history["close"].reset_index(drop=True)
    if len(closes) < 2:
        return False
    if strategy == "sma":
        fast = sma(closes, 10)
        slow = sma(closes, 30)
    elif strategy == "macd":
        m = macd(closes)
        fast, slow = m["macd"], m["signal"]
    else:
        raise ValueError(f"unknown trend strategy: {strategy}")
    today_fast, today_slow = fast.iloc[-1], slow.iloc[-1]
    prev_fast, prev_slow = fast.iloc[-2], slow.iloc[-2]
    if any(pd.isna(v) for v in (today_fast, today_slow, prev_fast, prev_slow)):
        return False
    return bool(today_fast > today_slow and prev_fast <= prev_slow)


def _summarise_trend(strategy: str, trade_rows: list[dict], counts: Counter,
                     starting_cash: float, equity: list[float]) -> dict:
    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    trades = len(trade_rows)
    return {
        "strategy": trend_label(strategy),
        "variant_id": WIDE6.id,
        "variant": WIDE6.label,
        "rules": WIDE6.description,
        "stop_pct": WIDE6.stop_pct,
        "take_pct": WIDE6.take_pct,
        "horizon_days": WIDE6.horizon_days,
        "use_filter": WIDE6.use_filter,
        "signal_exit": WIDE6.signal_exit,
        "walk_forward_step_days": TREND_STEP_DAYS,
        "trades_placed": trades,
        "signals_seen": counts["signals_seen"],
        "windows_checked": counts["windows_checked"],
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / trades * 100, 1) if trades else 0.0,
        "total_pnl_usd": total_pnl,
        "total_pnl_pct": round(total_pnl / starting_cash * 100, 2),
        "expectancy_usd": round(total_pnl / trades, 2) if trades else 0.0,
        "avg_win_usd": round(sum(t["pnl_usd"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_usd": round(sum(t["pnl_usd"] for t in losses) / len(losses), 2) if losses else 0.0,
        "max_drawdown_pct": max_drawdown_pct(equity),
        "exits": dict(Counter(t["exit_reason"] for t in trade_rows)),
        "blocked_by_risk": counts["blocked_by_risk"],
        "blocked_reasons": dict(counts["blocked_reasons"]),
        "skipped_already_in_position": counts["skipped_already_in_position"],
        "skipped_too_small": counts["skipped_too_small"],
        "too_small_by_symbol": dict(counts["too_small_by_symbol"]),
        "per_symbol_trades": dict(counts["per_symbol"]),
        "trades": trade_rows,
    }


def run_trend_validation(strategy: str, histories: dict[str, pd.DataFrame],
                         window_start: str | None = None,
                         starting_cash: float = STARTING_CASH,
                         risk_profile: str = "balanced",
                         symbols: list[str] | None = None) -> dict:
    """Walk-forward validation for one trend strategy under wide-6
    exits, over already-fetched histories. Entries are checked on
    EVERY bar (see TREND_STEP_DAYS) because a crossover is a
    single-bar event. Every triggered trade goes through the real
    PaperTradingEngine and Risk Engine with a 6% stop / 9% target /
    10-day exit. ``window_start`` marks where trading starts;
    earlier rows are warm-up. When None, trading starts at row 60
    (used by tests with stub histories and by the in-sample window).
    ``symbols`` limits the run to the given symbols (default: the
    full scan universe) — Phase 7 uses it for crypto-only runs;
    symbols missing from ``histories`` are skipped, never invented.
    """
    limits = RISK_PROFILES[risk_profile]
    profile = UserProfile(risk_tolerance=risk_profile,
                          max_position_pct=limits["max_position_pct"],
                          daily_loss_limit_pct=limits["daily_loss_limit_pct"],
                          allowed_markets=["stocks", "crypto"])
    risk = RiskEngine(max_position_pct=limits["max_position_pct"],
                      max_concentration_pct=limits["max_concentration_pct"],
                      max_exposure_pct=limits["max_exposure_pct"],
                      daily_loss_limit_pct=limits["daily_loss_limit_pct"],
                      min_risk_reward=limits["min_risk_reward"])
    portfolio = Portfolio(cash=starting_cash)
    engine = PaperTradingEngine(portfolio, risk)

    counts: Counter = Counter()
    counts["blocked_reasons"] = Counter()
    counts["per_symbol"] = Counter()
    counts["too_small_by_symbol"] = Counter()
    trade_rows: list[dict] = []
    equity = [starting_cash]

    symbols = [s for s in (symbols or SCAN_UNIVERSE) if s in histories]
    for symbol in symbols:
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else 60)
        for start in range(start_idx, len(history) - TREND_HORIZON_DAYS, TREND_STEP_DAYS):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            if not trend_trigger(strategy, window_history):
                continue
            counts["signals_seen"] += 1
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            entry = float(history.iloc[start]["close"])
            stop = round(entry * (1 - WIDE6.stop_pct), 2)
            take = math.ceil((entry + 1.5 * (entry - stop)) * 100) / 100
            raw_qty = risk.position_size(portfolio.value({symbol: entry}), entry)
            quantity = math.floor(raw_qty * 10000) / 10000
            if quantity <= 0:
                counts["skipped_too_small"] += 1
                counts["too_small_by_symbol"][symbol] += 1
                continue
            engine.realised_pnl = 0.0  # each window is a different simulated day
            trade = engine.place_order(
                symbol, "buy", quantity, entry, stop, take,
                reason=f"{strategy} trend trigger, exit variant wide-6",
                source="phase5-trend-test")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade_exit(
                history, start, entry, stop, take, TREND_HORIZON_DAYS,
                strategy, False)
            pnl = engine.close_position(symbol, exit_price, exit_reason)
            pnl = 0.0 if pnl is None else round(pnl, 2)
            equity.append(round(portfolio.cash, 2))
            trade_rows.append({
                "symbol": symbol, "entry": entry, "exit": exit_price,
                "quantity": quantity, "stop_loss": stop, "take_profit": take,
                "exit_reason": exit_reason, "days_held": days_held,
                "pnl_usd": pnl,
                "pnl_pct": round(pnl / (entry * quantity) * 100, 2) if entry * quantity else 0.0,
            })
            counts["per_symbol"][symbol] += 1
    return _summarise_trend(strategy, trade_rows, counts, starting_cash, equity)


def run_trend_window(label: str, start: str, end: str, sample: str,
                     symbols: list[str] | None = None,
                     provider=None) -> tuple[dict, dict]:
    """Run both trend strategies under wide-6 exits on one calendar
    window. Returns (window_report, histories)."""
    symbols = symbols or list(SCAN_UNIVERSE)
    if provider is None:
        provider = DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS)
    histories, failed, summary = fetch_histories(provider, symbols, days=180)
    strategies = {
        strategy: run_trend_validation(strategy, histories, window_start=start)
        for strategy in TREND_STRATEGIES
    }
    window = {
        "label": label, "start": start, "end": end, "sample": sample,
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "strategies": strategies,
    }
    return window, histories


def run_trend_insample_window(symbols: list[str] | None = None) -> tuple[dict, dict]:
    """Re-run both trend strategies under wide-6 on the Phase 4
    window (yfinance 180d period, as of today) — labelled
    in-sample, for comparison."""
    symbols = symbols or list(SCAN_UNIVERSE)
    histories, failed, summary = fetch_histories(YFinanceProvider(), symbols, days=180)
    strategies = {
        strategy: run_trend_validation(strategy, histories)
        for strategy in TREND_STRATEGIES
    }
    window = {
        "label": "Phase-4 window (in-sample)",
        "start": summary.get("AAPL", {}).get("first_date"),
        "end": summary.get("AAPL", {}).get("last_date"),
        "sample": "in-sample — the window the hypothesis was picked from",
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "strategies": strategies,
    }
    return window, histories


def _pool_trend(windows: list[dict], strategy: str) -> dict:
    """Pool trend windows for one strategy. Windows are pooled only
    as passed in — OOS, fresh, and in-sample pools stay separate."""
    results = [w["strategies"][strategy] for w in windows]
    trades = sum(r["trades_placed"] for r in results)
    wins = sum(r["wins"] for r in results)
    pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
    per_window_pnl = {w["label"]: r["total_pnl_usd"] for w, r in zip(windows, results)}
    return {
        "strategy": trend_label(strategy),
        "trades": trades,
        "wins": wins,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "total_pnl_usd": pnl,
        "total_pnl_pct": round(pnl / (STARTING_CASH * len(windows)) * 100, 2) if windows else 0.0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "per_window_pnl_usd": per_window_pnl,
        "per_window_win_rate_pct": {w["label"]: r["win_rate_pct"] for w, r in zip(windows, results)},
        "per_window_trades": {w["label"]: r["trades_placed"] for w, r in zip(windows, results)},
        "positive_windows": sum(1 for v in per_window_pnl.values() if v > 0),
        "windows_total": len(windows),
    }


def _pool_stress(windows: list[dict], strategy: str, variant_id: str) -> dict:
    """Pool the stress window(s) for one mean-reversion strategy /
    variant — same shape as Phase 4d's _pool_fresh."""
    results = [w["strategies"][strategy][variant_id] for w in windows]
    trades = sum(r["trades_placed"] for r in results)
    wins = sum(r["wins"] for r in results)
    pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
    per_window_pnl = {w["label"]: r["total_pnl_usd"] for w, r in zip(windows, results)}
    positive_windows = sum(1 for v in per_window_pnl.values() if v > 0)
    win_rate = round(wins / trades * 100, 1) if trades else 0.0
    return {
        "variant_id": variant_id,
        "trades": trades,
        "wins": wins,
        "win_rate_pct": win_rate,
        "total_pnl_usd": pnl,
        "total_pnl_pct": round(pnl / (STARTING_CASH * len(windows)) * 100, 2) if windows else 0.0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "per_window_pnl_usd": per_window_pnl,
        "per_window_win_rate_pct": {w["label"]: r["win_rate_pct"] for w, r in zip(windows, results)},
        "per_window_trades": {w["label"]: r["trades_placed"] for w, r in zip(windows, results)},
        "positive_windows": positive_windows,
        "windows_total": len(windows),
        "holds_up": bool(pnl > 0 and win_rate > STRESS_BREAK_EVEN_WIN_RATE_PCT
                         and positive_windows >= len(windows)),
    }


def run_phase5() -> dict:
    """Run both Phase 5 tests: trend-following on OOS-1/2/3, the
    Phase 4 window, and FRESH-1/2/3; wide-6 mean-reversion stress
    test on FRESH-4."""
    from .exit_test import run_window_exits

    trend_windows: list[dict] = []
    for label, start, end in list(OOS_WINDOWS) + list(FRESH_WINDOWS):
        sample = ("out-of-sample" if label.startswith("OOS")
                  else "fresh — never used for selection")
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
        window, _histories = run_trend_window(label, start, end, sample,
                                              provider=provider)
        trend_windows.append(window)
    insample_window, _ = run_trend_insample_window()

    oos_windows = [w for w in trend_windows if w["label"].startswith("OOS")]
    fresh_windows = [w for w in trend_windows if w["label"].startswith("FRESH")]
    all_trend_windows = trend_windows + [insample_window]

    pooled_trend = {}
    for strategy in TREND_STRATEGIES:
        pooled_trend[strategy] = {
            "oos_pooled": _pool_trend(oos_windows, strategy),
            "fresh_pooled": _pool_trend(fresh_windows, strategy),
            "all_windows_pooled_incl_insample": _pool_trend(all_trend_windows, strategy),
        }

    # Trend vs mean-reversion verdicts, per the pre-set rules.
    trend_verdict: dict[str, dict] = {}
    for strategy in TREND_STRATEGIES:
        oos = pooled_trend[strategy]["oos_pooled"]
        fresh = pooled_trend[strategy]["fresh_pooled"]
        oos2_pnl = oos["per_window_pnl_usd"].get("OOS-2")
        beats_oos2 = bool(
            oos2_pnl is not None
            and oos2_pnl > MR_WIDE6_REFERENCE["rsi"]["oos2_pnl_usd"]
            and oos2_pnl > MR_WIDE6_REFERENCE["bollinger"]["oos2_pnl_usd"])
        beats_oos_pooled = bool(
            oos["total_pnl_usd"] > MR_WIDE6_REFERENCE["rsi"]["oos_pooled_pnl_usd"]
            and oos["total_pnl_usd"] > MR_WIDE6_REFERENCE["bollinger"]["oos_pooled_pnl_usd"])
        beats_fresh_pooled = bool(
            fresh["total_pnl_usd"] > MR_WIDE6_REFERENCE["rsi"]["fresh_pooled_pnl_usd"]
            and fresh["total_pnl_usd"] > MR_WIDE6_REFERENCE["bollinger"]["fresh_pooled_pnl_usd"])
        trend_verdict[strategy] = {
            "oos2_pnl_usd": oos2_pnl,
            "mr_wide6_oos2_pnl_usd": {
                "rsi": MR_WIDE6_REFERENCE["rsi"]["oos2_pnl_usd"],
                "bollinger": MR_WIDE6_REFERENCE["bollinger"]["oos2_pnl_usd"],
            },
            "beats_mr_in_oos2": beats_oos2,
            "beats_mr_pooled_oos": beats_oos_pooled,
            "beats_mr_pooled_fresh": beats_fresh_pooled,
            "verdict_rule": ("Beats mean-reversion in OOS-2 when OOS-2 P&L is "
                             "greater than BOTH mean-reversion wide-6 OOS-2 figures "
                             "(RSI +$63.26, Bollinger +$482.00); beats pooled when "
                             "pooled P&L is greater than both pooled mean-reversion "
                             "wide-6 figures (OOS: RSI +$1,441.19, Bollinger +$880.48; "
                             "fresh: RSI +$1,226.24, Bollinger +$1,043.47)."),
        }

    # Stress test: wide-6 (plus baseline / wide-5 controls, as in
    # Phase 4d) mean-reversion on FRESH-4.
    stress_windows: list[dict] = []
    for label, start, end in STRESS_WINDOWS:
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
        window, _histories = run_window_exits(
            label, start, end, "fresh — never used for selection",
            variants=FRESH_VARIANTS, provider=provider)
        stress_windows.append(window)

    pooled_stress: dict[str, dict] = {}
    stress_verdict: dict[str, dict] = {}
    for strategy in MR_STRATEGIES:
        pooled_stress[strategy] = {
            vid: _pool_stress(stress_windows, strategy, vid)
            for vid in FRESH_VARIANT_IDS
        }
        best_id = max(pooled_stress[strategy],
                      key=lambda vid: pooled_stress[strategy][vid]["total_pnl_usd"])
        stress_verdict[strategy] = {
            "best_variant_by_pooled_stress_pnl": best_id,
            "best_pooled_stress_pnl_usd": pooled_stress[strategy][best_id]["total_pnl_usd"],
            "wide6_holds_up": pooled_stress[strategy]["wide-6"]["holds_up"],
            "variants_holding_up": [vid for vid in FRESH_VARIANT_IDS
                                    if pooled_stress[strategy][vid]["holds_up"]],
            "verdict_rule": ("Holds up on FRESH-4 when FRESH-4 paper P&L > $0 AND "
                             "win rate > 40% (the 1.5:1 break-even). Single window "
                             "only — weaker evidence than the Phase 4d 3-window rule."),
        }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 5 Trend-Following & Stress Test Report",
        "method": ("Two paper-only tests on delayed real yfinance history, "
                   "12 symbols, walk-forward, signals from history up to the "
                   "trade day only — no look-ahead. Every trade goes through "
                   "the real PaperTradingEngine and Risk Engine, balanced "
                   "profile, $10,000 virtual cash, long-only, 10-day exit. "
                   "Every variant keeps a stop-loss; the stop is never removed. "
                   "(a) Trend-following: SMA crossover (SMA-10 cross above "
                   "SMA-30) and MACD crossover (MACD cross above signal line), "
                   "exactly as defined in analytics/backtest.py, with wide-6 "
                   "exits (6% stop / 9% target, 1.5:1), on OOS-1/2/3, the "
                   "Phase 4 window (re-run, in-sample), and FRESH-1/2/3. "
                   "Trend entries are checked on EVERY bar because a crossover "
                   "is a single-bar event a 5-day step would miss; "
                   "mean-reversion entries in Phases 4b–4d used a 5-day step "
                   "because their triggers are persistent states. "
                   "(b) Stress: RSI + Bollinger mean-reversion under baseline "
                   "(3% / 4.5%), wide-5 (5% / 7.5%) and wide-6 (6% / 9%) on "
                   "one more fresh window, FRESH-4 (2022-09-12 → 2023-03-10), "
                   "with the Phase 4d method (70 days warm-up, 5-day steps). "
                   "Fetched histories are cached to data/fresh-cache/ as they "
                   "arrive; FRESH-1/2/3 histories were already cached from "
                   "Phase 4d and were not re-fetched."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "trend_windows_definition": [
            {"label": label, "start": start, "end": end}
            for label, start, end in list(OOS_WINDOWS) + list(FRESH_WINDOWS)
        ],
        "stress_window_definition": [
            {"label": label, "start": start, "end": end}
            for label, start, end in STRESS_WINDOWS
        ],
        "trend_strategies": [
            {"id": s, "label": trend_label(s),
             "stop_pct": WIDE6.stop_pct, "take_pct": WIDE6.take_pct,
             "horizon_days": WIDE6.horizon_days,
             "walk_forward_step_days": TREND_STEP_DAYS}
            for s in TREND_STRATEGIES
        ],
        "mean_reversion_wide6_reference": MR_WIDE6_REFERENCE,
        "trend_verdict_rule": ("A trend strategy 'beats mean-reversion in "
                               "OOS-2' when its OOS-2 paper P&L is greater than "
                               "BOTH mean-reversion wide-6 OOS-2 figures (RSI "
                               "+$63.26, Bollinger +$482.00)."),
        "stress_verdict_rule": ("Wide-6 'holds up' on FRESH-4 when its FRESH-4 "
                                "paper P&L is > $0 AND its win rate is > 40% "
                                "(the 1.5:1 break-even). Single window only."),
        "trend_windows": trend_windows,
        "trend_insample_window": insample_window,
        "pooled_trend": pooled_trend,
        "trend_verdict": trend_verdict,
        "stress_windows": stress_windows,
        "pooled_stress": pooled_stress,
        "stress_verdict": stress_verdict,
        "note": ("Nothing here proves future profits: past performance does "
                 "not guarantee future results. Trend trade counts are not "
                 "directly comparable with mean-reversion trade counts "
                 "because trend entries are checked every bar while "
                 "mean-reversion entries were checked every 5 days — P&L, "
                 "win rate, and expectancy per trade are the comparison. "
                 "The FRESH-4 stress check is a single window, so a "
                 "hold-up there is weaker evidence than the Phase 4d "
                 "three-window hold-up. Related work: a parallel Phase 4e "
                 "run (validation/phase4e-trend-following-report.md) tested "
                 "a different trend entry — buy when close > SMA-20 > "
                 "SMA-50, a persistent state, on 5-day steps — on "
                 "FRESH-1/2/3 only, from cache: wide-6 422 trades, 61.8% "
                 "win, +$5,163.64 pooled fresh. It did not cover OOS-2, "
                 "so it cannot answer the falling-window question; this "
                 "Phase 5 test uses crossover entries (SMA-10/30, MACD) "
                 "on the OOS + fresh windows instead. The two trend "
                 "definitions are not the same strategy and their trade "
                 "counts are not comparable. Live paper trades over real days "
                 "plus a compliance/legal review are still required before "
                 "any real money is considered."),
    }


def _fmt_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['title']}",
        "",
        f"Generated: {report['generated_at']} (UTC)",
        "",
        "> Risk disclosure: trading involves substantial risk of loss. "
        "This report tests strategies on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        f"- Trend verdict rule: {report['trend_verdict_rule']}",
        f"- Stress verdict rule: {report['stress_verdict_rule']}",
        "",
        "## Test (a) — Trend-following vs mean-reversion (wide-6 exits)",
        "",
        "Mean-reversion wide-6 reference figures (Phases 4c/4d, same "
        "method, quoted — not re-run here):",
        "",
        "| Strategy | Pooled OOS P&L | Pooled OOS win | OOS-2 P&L | Pooled fresh P&L |",
        "|---|---:|---:|---:|---:|",
    ]
    for strategy in MR_STRATEGIES:
        ref = report["mean_reversion_wide6_reference"][strategy]
        lines.append(
            f"| {mr_strategy_label(strategy)} | {_fmt_money(ref['oos_pooled_pnl_usd'])} "
            f"({ref['oos_pooled_trades']} trades, {ref['oos_pooled_win_rate_pct']}%) | "
            f"{_fmt_money(ref['oos2_pnl_usd'])} | {_fmt_money(ref['fresh_pooled_pnl_usd'])} "
            f"({ref['fresh_pooled_trades']} trades, {ref['fresh_pooled_win_rate_pct']}%) |")
    lines += ["", "### Trend pooled results", ""]
    for strategy in TREND_STRATEGIES:
        pooled = report["pooled_trend"][strategy]
        lines += [f"#### {trend_label(strategy)}", "",
                  "| Pool | Trades | Win rate | P&L | Expectancy / trade | Positive windows |",
                  "|---|---:|---:|---:|---:|:---:|"]
        for pool_name, pool in (("OOS-1/2/3 pooled", pooled["oos_pooled"]),
                                ("FRESH-1/2/3 pooled", pooled["fresh_pooled"]),
                                ("All 7 windows incl. Phase-4 in-sample", pooled["all_windows_pooled_incl_insample"])):
            lines.append(
                f"| {pool_name} | {pool['trades']} | {pool['win_rate_pct']:.1f}% | "
                f"{_fmt_money(pool['total_pnl_usd'])} | {_fmt_money(pool['expectancy_usd'])} | "
                f"{pool['positive_windows']}/{pool['windows_total']} |")
        lines.append("")
    lines += ["### Trend verdict — does trend-following beat mean-reversion in falling windows?", ""]
    for strategy in TREND_STRATEGIES:
        verdict = report["trend_verdict"][strategy]
        pooled = report["pooled_trend"][strategy]
        lines += [
            f"#### {trend_label(strategy)}",
            "",
            f"- OOS-2 (the falling window) P&L: **{_fmt_money(verdict['oos2_pnl_usd'])}** vs "
            f"RSI wide-6 {_fmt_money(verdict['mr_wide6_oos2_pnl_usd']['rsi'])} and Bollinger "
            f"wide-6 {_fmt_money(verdict['mr_wide6_oos2_pnl_usd']['bollinger'])} — "
            f"**{'BEATS mean-reversion in OOS-2' if verdict['beats_mr_in_oos2'] else 'does NOT beat mean-reversion in OOS-2'}**.",
            f"- Pooled OOS-1/2/3 P&L: {_fmt_money(pooled['oos_pooled']['total_pnl_usd'])} vs "
            f"RSI wide-6 {_fmt_money(report['mean_reversion_wide6_reference']['rsi']['oos_pooled_pnl_usd'])} and "
            f"Bollinger wide-6 {_fmt_money(report['mean_reversion_wide6_reference']['bollinger']['oos_pooled_pnl_usd'])} — "
            f"**{'beats pooled OOS' if verdict['beats_mr_pooled_oos'] else 'does NOT beat pooled OOS'}**.",
            f"- Pooled FRESH-1/2/3 P&L: {_fmt_money(pooled['fresh_pooled']['total_pnl_usd'])} vs "
            f"RSI wide-6 {_fmt_money(report['mean_reversion_wide6_reference']['rsi']['fresh_pooled_pnl_usd'])} and "
            f"Bollinger wide-6 {_fmt_money(report['mean_reversion_wide6_reference']['bollinger']['fresh_pooled_pnl_usd'])} — "
            f"**{'beats pooled fresh' if verdict['beats_mr_pooled_fresh'] else 'does NOT beat pooled fresh'}**.",
            "",
        ]
    lines += [
        "## Test (b) — Stress test: wide-6 mean-reversion on FRESH-4 (2022-09-12 → 2023-03-10)",
        "",
        "One more fresh 180-day window, earlier than FRESH-3, overlapping "
        "no window used before. Single window — a hold-up here is weaker "
        "evidence than the Phase 4d three-window hold-up.",
        "",
    ]
    for strategy in MR_STRATEGIES:
        lines += [f"### {mr_strategy_label(strategy)} — FRESH-4", "",
                  "| Variant | Trades | Win rate | P&L | Expectancy / trade | Holds up |",
                  "|---|---:|---:|---:|---:|:---:|"]
        for variant_id, pooled in report["pooled_stress"][strategy].items():
            lines.append(
                f"| {variant_id} | {pooled['trades']} | {pooled['win_rate_pct']:.1f}% | "
                f"{_fmt_money(pooled['total_pnl_usd'])} | {_fmt_money(pooled['expectancy_usd'])} | "
                f"{'yes' if pooled['holds_up'] else 'NO'} |")
        lines.append("")
        verdict = report["stress_verdict"][strategy]
        lines += [
            f"- Best variant on FRESH-4: **{verdict['best_variant_by_pooled_stress_pnl']}** "
            f"({_fmt_money(verdict['best_pooled_stress_pnl_usd'])}).",
            f"- Wide-6 holds up on FRESH-4: **{'yes' if verdict['wide6_holds_up'] else 'NO'}**.",
            f"- Variants holding up: {verdict['variants_holding_up'] or 'none'}.",
            "",
        ]
    lines += [
        "## Reading it honestly",
        "",
        report["note"],
        "",
    ]
    for window in report["trend_windows"] + [report["trend_insample_window"]]:
        lines += [
            f"## Trend — {window['label']} — {window['start']} → {window['end']} "
            f"({window['sample']})",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
            "| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
        ]
        for strategy in TREND_STRATEGIES:
            result = window["strategies"][strategy]
            lines.append(
                f"| {trend_label(strategy)} | {result['trades_placed']} | {result['win_rate_pct']:.1f}% | "
                f"{_fmt_money(result['total_pnl_usd'])} | {_fmt_money(result['expectancy_usd'])} | "
                f"{_fmt_money(result['avg_win_usd'])} | {_fmt_money(result['avg_loss_usd'])} | "
                f"{result['max_drawdown_pct']:.2f}% | {result['exits']} | {result['blocked_by_risk']} |")
        lines.append("")
        for strategy in TREND_STRATEGIES:
            result = window["strategies"][strategy]
            lines.append(f"- {strategy} per symbol: {result['per_symbol_trades']}")
        lines.append("")
    for window in report["stress_windows"]:
        lines += [
            f"## Stress — {window['label']} — {window['start']} → {window['end']} "
            f"({window['sample']})",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
        ]
        for strategy in MR_STRATEGIES:
            lines += [f"### {mr_strategy_label(strategy)}", "",
                      "| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|"]
            for variant_id, result in window["strategies"][strategy].items():
                lines.append(
                    f"| {variant_id} | {result['trades_placed']} | {result['win_rate_pct']:.1f}% | "
                    f"{_fmt_money(result['total_pnl_usd'])} | {_fmt_money(result['expectancy_usd'])} | "
                    f"{_fmt_money(result['avg_win_usd'])} | {_fmt_money(result['avg_loss_usd'])} | "
                    f"{result['max_drawdown_pct']:.2f}% | {result['exits']} | {result['blocked_by_risk']} |")
            lines.append("")
            for variant_id, result in window["strategies"][strategy].items():
                lines.append(f"- {variant_id} per symbol: {result['per_symbol_trades']}")
            lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        report["note"],
        "",
        "## Trades (every trade, in order) — trend wide-6 and stress wide-6",
        "",
        "Trade-by-trade rows for the trend strategies (wide-6) on every "
        "window and for mean-reversion wide-6 on FRESH-4. Every trade "
        "for every variant is in the JSON report.",
        "",
    ]
    for window in report["trend_windows"] + [report["trend_insample_window"]]:
        for strategy in TREND_STRATEGIES:
            result = window["strategies"][strategy]
            if not result["trades"]:
                lines += [f"### Trend {window['label']} — {trend_label(strategy)}: no trades", ""]
                continue
            lines += [f"### Trend {window['label']} — {trend_label(strategy)}",
                      "",
                      "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
                      "|---:|---|---|---|---|---:|---:|"]
            for i, t in enumerate(result["trades"], 1):
                lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                             f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
            lines.append("")
    for window in report["stress_windows"]:
        for strategy in MR_STRATEGIES:
            result = window["strategies"][strategy].get("wide-6")
            if result is None or not result["trades"]:
                lines += [f"### Stress {window['label']} — {mr_strategy_label(strategy)} — wide-6: no trades", ""]
                continue
            lines += [f"### Stress {window['label']} — {mr_strategy_label(strategy)} — wide-6",
                      "",
                      "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
                      "|---:|---|---|---|---|---:|---:|"]
            for i, t in enumerate(result["trades"], 1):
                lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                             f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase5-trend-and-stress-report") -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    import sys

    base = Path(__file__).resolve().parents[2]
    report = run_phase5()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for strategy in TREND_STRATEGIES:
        pooled = report["pooled_trend"][strategy]
        verdict = report["trend_verdict"][strategy]
        print(f"TREND {strategy}: OOS pooled {pooled['oos_pooled']['trades']} trades, "
              f"{pooled['oos_pooled']['win_rate_pct']}% win, "
              f"P&L {_fmt_money(pooled['oos_pooled']['total_pnl_usd'])}, "
              f"OOS-2 {_fmt_money(verdict['oos2_pnl_usd'])} "
              f"({'BEATS MR in OOS-2' if verdict['beats_mr_in_oos2'] else 'does NOT beat MR in OOS-2'})")
        print(f"TREND {strategy}: fresh pooled {pooled['fresh_pooled']['trades']} trades, "
              f"{pooled['fresh_pooled']['win_rate_pct']}% win, "
              f"P&L {_fmt_money(pooled['fresh_pooled']['total_pnl_usd'])}")
    for strategy in MR_STRATEGIES:
        verdict = report["stress_verdict"][strategy]
        wide6 = report["pooled_stress"][strategy]["wide-6"]
        print(f"STRESS {strategy} wide-6 on FRESH-4: {wide6['trades']} trades, "
              f"{wide6['win_rate_pct']}% win, P&L {_fmt_money(wide6['total_pnl_usd'])} "
              f"({'HOLDS UP' if verdict['wide6_holds_up'] else 'does NOT hold up'})")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
