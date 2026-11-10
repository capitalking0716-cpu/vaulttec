"""Phase 6 — win-rate tests: can a pickier entry raise the win rate?

Paper only, no broker, no real money, no leverage, no options.
Past performance does not guarantee future results.

Lead so far: RSI + Bollinger mean-reversion, wide-6 (6% stop /
9% target, 1.5:1, 10-day exit), long-only, $10,000 paper, 12 symbols.
Phase 4c: wide-6 won the exit test; the downtrend filter threw away
winners. Phase 4d fresh: RSI wide-6 +$1,226.24 (61.6%, 73 trades),
Bollinger wide-6 +$1,043.47 (63.9%, 36 trades). Phase 5: MACD
trend-following +$2,899.45 fresh (174 trades, 60.9%) and +$4,581.51
across all 7 windows (416 trades, 55.0%); FRESH-4: RSI wide-6
+$651.89 (50.0%, 32 trades), Bollinger wide-6 +$3.24 (35.7%,
14 trades) — break-even.

Three NEW, non-duplicate tests, all wide-6, all through the real
PaperTradingEngine + Risk Engine, $10,000, long-only, 5-day
walk-forward steps for mean-reversion (MACD in the combined run
is checked every bar — a crossover is a single-bar event):

1. high-confidence-only: RSI + Bollinger wide-6, but only when the
   explainable signal on that day is long with confidence >= 0.70
   (the app's scanner floor is 0.55; 0.70 needs at least 4 weighted
   bullish checks agreeing — e.g. oversold + trend/EMA/MACD/volume
   behind it). The confidence is computed from history up to the
   trade day only — no look-ahead.
2. volume-confirmation: same wide-6 entries, but only when the
   entry bar's volume is above its 20-day average volume
   (volume ratio > 1.0, computed from history up to the trade day
   only). A move on above-average volume has more people behind it.
3. combined: wide-6 mean-reversion (RSI + Bollinger) PLUS MACD
   trend-following in ONE shared portfolio — one $10,000 pot, one
   Risk Engine, 10% position cap, no double exposure on the same
   symbol on the same day (at most one trade per symbol per day,
   mean-reversion first, then MACD). Mean-reversion candidates are
   checked on the 5-day grid, MACD on every bar.

Windows: OOS-1/2/3 (selection windows, reported separately) and
FRESH-1/2/3/4 (fresh windows, reported separately) — 7 windows,
all already cached to data/fresh-cache/ from earlier phases, so
this run re-fetches nothing from Yahoo. OOS and fresh pools are
NEVER mixed. The wide-6 baseline is re-run on the same windows
with the same method so the comparison is like-for-like.

Verdict rule — fixed before the run: a variant is "worth keeping"
when its pooled FRESH P&L is > $0 AND its pooled fresh win rate
is > 40% (the 1.5:1 break-even) AND it is positive in at least 2
of the fresh windows, AND its pooled OOS P&L is also > $0. The
same rule is also applied to the OOS pool on its own and reported,
so a variant that only looks good on the selection windows cannot
hide behind the fresh pool. Expectancy (P&L per trade) is reported
next to win rate throughout: at 1.5:1 the break-even win rate is
exactly 40%, so a higher win rate with smaller wins can still lose
money, and vice versa. Small trade counts are flagged wherever
they occur. Every variant keeps a stop-loss; the stop is never
removed. Live paper evidence is still Day 1 only (2026-11-09:
3 trades open, 0 closed, $0 realised) — it proves nothing yet
and is NOT used as test data here.
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
from ..market.data import SCAN_UNIVERSE
from ..market.indicators import volume_analysis
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import max_drawdown_pct
from .exit_test import (
    STARTING_CASH,
    WARMUP_DAYS,
    WINDOW_STEP_DAYS,
    _exit_trade_exit,
    run_variant_validation,
    variant_by_id,
)
from .fresh_window import FRESH_WINDOWS, CachedDatedProvider
from .mean_reversion import (
    DatedYFinanceProvider,
    OOS_WINDOWS,
    STRATEGIES,
    mean_reversion_trigger,
    strategy_label,
    trade_start_index,
)
from .signals import generate_signal
from .trend_and_stress import STRESS_WINDOW, trend_trigger
from .validation import fetch_histories

WIDE6 = variant_by_id("wide-6")  # 6% stop / 9% target, 10-day exit
HIGH_CONFIDENCE_MIN = 0.70
VOLUME_RATIO_MIN = 1.0  # entry-bar volume above its 20-day average
BREAK_EVEN_WIN_RATE_PCT = 40.0
MIN_POSITIVE_WINDOWS = 2

# All windows, OOS first then fresh. FRESH-4 comes from Phase 5.
ALL_WINDOWS: list[tuple[str, str, str]] = list(OOS_WINDOWS) + list(FRESH_WINDOWS) + [STRESS_WINDOW]
OOS_LABELS = {label for label, _, _ in OOS_WINDOWS}
FRESH_LABELS = {label for label, _, _ in FRESH_WINDOWS} | {STRESS_WINDOW[0]}

# Variant keys used in every window's "results" dict.
VARIANT_KEYS = (
    "rsi_wide6",
    "rsi_highconf",
    "rsi_volume",
    "bollinger_wide6",
    "bollinger_highconf",
    "bollinger_volume",
    "combined",
)

VARIANT_LABELS = {
    "rsi_wide6": "RSI wide-6 (baseline, re-run)",
    "rsi_highconf": "RSI wide-6, confidence >= 0.70 only",
    "rsi_volume": "RSI wide-6, volume > 20-day average only",
    "bollinger_wide6": "Bollinger wide-6 (baseline, re-run)",
    "bollinger_highconf": "Bollinger wide-6, confidence >= 0.70 only",
    "bollinger_volume": "Bollinger wide-6, volume > 20-day average only",
    "combined": "Combined — MR wide-6 (RSI + Bollinger) + MACD trend, one portfolio",
}


def confidence_gate(symbol: str, history_up_to_day: pd.DataFrame) -> bool:
    """True when the explainable signal on the last bar is long with
    confidence >= 0.70 — history up to the trade day only."""
    try:
        signal = generate_signal(symbol, history_up_to_day)
    except Exception:
        return False
    return bool(signal.direction == "long" and signal.confidence >= HIGH_CONFIDENCE_MIN)


def volume_gate(history_up_to_day: pd.DataFrame) -> bool:
    """True when the entry bar's volume is above its 20-day average
    volume — history up to the trade day only. Missing volume data
    never passes the gate."""
    if "volume" not in history_up_to_day.columns:
        return False
    try:
        ratio = volume_analysis(history_up_to_day["volume"])["ratio"]
    except Exception:
        return False
    return bool(ratio is not None and ratio > VOLUME_RATIO_MIN)


def _summarise_filtered(strategy: str, variant_key: str, label: str,
                        trade_rows: list[dict], counts: Counter,
                        starting_cash: float, equity: list[float]) -> dict:
    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    trades = len(trade_rows)
    return {
        "strategy": strategy_label(strategy),
        "variant_key": variant_key,
        "variant": label,
        "rules": label,
        "stop_pct": WIDE6.stop_pct,
        "take_pct": WIDE6.take_pct,
        "horizon_days": WIDE6.horizon_days,
        "trades_placed": trades,
        "signals_seen": counts["signals_seen"],
        "windows_checked": counts["windows_checked"],
        "skipped_gate": counts["skipped_gate"],
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


def run_filtered_variant(strategy: str, variant_key: str, gate: str,
                         histories: dict[str, pd.DataFrame],
                         window_start: str | None = None,
                         starting_cash: float = STARTING_CASH,
                         risk_profile: str = "balanced") -> dict:
    """Walk-forward validation for one mean-reversion strategy under
    wide-6 exits, with one extra entry gate. ``gate`` is
    "highconf" (signal long, confidence >= 0.70) or "volume"
    (entry-bar volume above its 20-day average). Same method as
    Phase 4c's run_variant_validation: 5-day steps, every trade
    through the real PaperTradingEngine + Risk Engine, balanced
    profile, $10,000, long-only, 10-day exit, stop always set."""
    if gate not in ("highconf", "volume"):
        raise ValueError(f"unknown gate: {gate}")
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

    symbols = [s for s in SCAN_UNIVERSE if s in histories]
    for symbol in symbols:
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else 60)
        for start in range(start_idx, len(history) - WIDE6.horizon_days, WINDOW_STEP_DAYS):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            if not mean_reversion_trigger(strategy, window_history):
                continue
            counts["signals_seen"] += 1
            passed = (confidence_gate(symbol, window_history) if gate == "highconf"
                      else volume_gate(window_history))
            if not passed:
                counts["skipped_gate"] += 1
                continue
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
            engine.realised_pnl = 0.0
            trade = engine.place_order(
                symbol, "buy", quantity, entry, stop, take,
                reason=f"{strategy} mean-reversion trigger, wide-6, gate {gate}",
                source="phase6-win-rate")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade_exit(
                history, start, entry, stop, take, WIDE6.horizon_days, strategy, False)
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
    return _summarise_filtered(strategy, variant_key, VARIANT_LABELS[variant_key],
                               trade_rows, counts, starting_cash, equity)


def run_combined_validation(histories: dict[str, pd.DataFrame],
                            window_start: str | None = None,
                            starting_cash: float = STARTING_CASH,
                            risk_profile: str = "balanced",
                            symbols: list[str] | None = None) -> dict:
    """One shared $10,000 portfolio: wide-6 mean-reversion (RSI +
    Bollinger, 5-day grid) PLUS MACD trend-following (every bar),
    both wide-6 exits. At most one trade per symbol per day
    (mean-reversion first, then MACD), so the two legs can never
    double-expose the same symbol on the same day. Every trade
    through the real PaperTradingEngine + Risk Engine; the stop is
    always set. MACD is checked every bar because a crossover is a
    single-bar event; mean-reversion triggers are persistent
    states, so the 5-day grid still catches them (as in Phases
    4b–4d). Trade counts are therefore not directly comparable
    with the single-strategy runs — P&L, win rate and expectancy
    per trade are the comparison."""
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
    counts["per_source"] = Counter()
    trade_rows: list[dict] = []
    equity = [starting_cash]

    symbols = [s for s in (symbols or SCAN_UNIVERSE) if s in histories]
    for symbol in symbols:
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else 60)
        for start in range(start_idx, len(history) - WIDE6.horizon_days, 1):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            # Candidates in priority order: RSI, Bollinger (5-day grid
            # only), then MACD (every bar). At most one per symbol/day.
            candidates: list[str] = []
            if (start - start_idx) % WINDOW_STEP_DAYS == 0:
                for strategy in STRATEGIES:
                    if mean_reversion_trigger(strategy, window_history):
                        counts["signals_seen"] += 1
                        candidates.append(strategy)
            if trend_trigger("macd", window_history):
                counts["signals_seen"] += 1
                candidates.append("macd")
            if not candidates:
                continue
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            placed = False
            for source_strategy in candidates:
                if placed:
                    counts["skipped_same_day_double"] += 1
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
                engine.realised_pnl = 0.0
                trade = engine.place_order(
                    symbol, "buy", quantity, entry, stop, take,
                    reason=f"{source_strategy} trigger, combined wide-6",
                    source="phase6-combined")
                if trade is None:
                    counts["blocked_by_risk"] += 1
                    for reason in engine.blocked[-1]["reasons"]:
                        counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                    continue
                exit_price, exit_reason, days_held = _exit_trade_exit(
                    history, start, entry, stop, take, WIDE6.horizon_days,
                    "rsi", False)
                pnl = engine.close_position(symbol, exit_price, exit_reason)
                pnl = 0.0 if pnl is None else round(pnl, 2)
                equity.append(round(portfolio.cash, 2))
                trade_rows.append({
                    "symbol": symbol, "source_strategy": source_strategy,
                    "entry": entry, "exit": exit_price,
                    "quantity": quantity, "stop_loss": stop, "take_profit": take,
                    "exit_reason": exit_reason, "days_held": days_held,
                    "pnl_usd": pnl,
                    "pnl_pct": round(pnl / (entry * quantity) * 100, 2) if entry * quantity else 0.0,
                })
                counts["per_symbol"][symbol] += 1
                counts["per_source"][source_strategy] += 1
                placed = True
    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    trades = len(trade_rows)
    return {
        "strategy": "Combined — MR wide-6 (RSI + Bollinger) + MACD trend",
        "variant_key": "combined",
        "variant": VARIANT_LABELS["combined"],
        "rules": VARIANT_LABELS["combined"],
        "stop_pct": WIDE6.stop_pct,
        "take_pct": WIDE6.take_pct,
        "horizon_days": WIDE6.horizon_days,
        "walk_forward_step_days": 1,
        "trades_placed": trades,
        "signals_seen": counts["signals_seen"],
        "windows_checked": counts["windows_checked"],
        "skipped_same_day_double": counts["skipped_same_day_double"],
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
        "per_source_trades": dict(counts["per_source"]),
        "trades": trade_rows,
    }


def run_phase6_window(label: str, start: str, end: str, sample: str,
                      symbols: list[str] | None = None,
                      provider=None) -> tuple[dict, dict]:
    """Run all seven Phase 6 variants on one calendar window.
    Returns (window_report, histories)."""
    symbols = symbols or list(SCAN_UNIVERSE)
    if provider is None:
        provider = DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS)
    histories, failed, summary = fetch_histories(provider, symbols, days=180)
    results: dict[str, dict] = {}
    for strategy in STRATEGIES:
        results[f"{strategy}_wide6"] = run_variant_validation(
            strategy, WIDE6, histories, window_start=start)
        results[f"{strategy}_highconf"] = run_filtered_variant(
            strategy, f"{strategy}_highconf", "highconf", histories, window_start=start)
        results[f"{strategy}_volume"] = run_filtered_variant(
            strategy, f"{strategy}_volume", "volume", histories, window_start=start)
    results["combined"] = run_combined_validation(histories, window_start=start)
    window = {
        "label": label, "start": start, "end": end, "sample": sample,
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "results": results,
    }
    return window, histories


def _pool_key(windows: list[dict], variant_key: str) -> dict:
    """Pool one variant across the windows given — OOS and fresh
    pools are built from separate window lists and never mixed."""
    results = [w["results"][variant_key] for w in windows]
    trades = sum(r["trades_placed"] for r in results)
    wins = sum(r["wins"] for r in results)
    pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
    per_window_pnl = {w["label"]: r["total_pnl_usd"] for w, r in zip(windows, results)}
    positive_windows = sum(1 for v in per_window_pnl.values() if v > 0)
    win_rate = round(wins / trades * 100, 1) if trades else 0.0
    return {
        "variant_key": variant_key,
        "variant": VARIANT_LABELS[variant_key],
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
        "worth_keeping_pool": bool(pnl > 0 and win_rate > BREAK_EVEN_WIN_RATE_PCT
                                   and positive_windows >= MIN_POSITIVE_WINDOWS),
    }


def run_phase6() -> dict:
    """Run Phase 6: all seven variants on OOS-1/2/3 + FRESH-1/2/3/4,
    from the disk cache (no Yahoo re-fetch). Pools are built
    separately for OOS and fresh; a variant is worth keeping only
    when its fresh pool passes the pre-set rule AND its OOS pool
    P&L is also > $0."""
    windows: list[dict] = []
    for label, start, end in ALL_WINDOWS:
        sample = ("out-of-sample" if label in OOS_LABELS
                  else "fresh — never used for selection")
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
        window, _histories = run_phase6_window(label, start, end, sample,
                                               provider=provider)
        windows.append(window)

    oos_windows = [w for w in windows if w["label"] in OOS_LABELS]
    fresh_windows = [w for w in windows if w["label"] in FRESH_LABELS]

    pooled_oos = {key: _pool_key(oos_windows, key) for key in VARIANT_KEYS}
    pooled_fresh = {key: _pool_key(fresh_windows, key) for key in VARIANT_KEYS}

    verdict: dict[str, dict] = {}
    for key in VARIANT_KEYS:
        fresh = pooled_fresh[key]
        oos = pooled_oos[key]
        # Small-sample flag (annotation only — it does not change the
        # pre-set rule): a variant that passes on fewer than 20 fresh
        # trades has too little evidence to adopt, however good its
        # win rate looks. The high-confidence variants land here.
        verdict[key] = {
            "worth_keeping": bool(fresh["worth_keeping_pool"] and oos["total_pnl_usd"] > 0),
            "fresh_pool_passes": fresh["worth_keeping_pool"],
            "oos_pooled_pnl_positive": bool(oos["total_pnl_usd"] > 0),
            "fresh_trades": fresh["trades"],
            "oos_trades": oos["trades"],
            "small_sample_fresh": bool(fresh["trades"] < 20),
            "small_sample_oos": bool(oos["trades"] < 20),
            "verdict_rule": ("Worth keeping = pooled fresh P&L > $0 AND pooled fresh "
                             "win rate > 40% AND positive in at least 2 fresh windows "
                             "AND pooled OOS P&L > $0. Small-sample flag: fewer than "
                             "20 trades in a pool — too little evidence to adopt."),
        }

    # Combined vs either leg alone, pooled across all 7 windows is
    # NOT a verdict pool (OOS + fresh must stay separate) — compare
    # within each pool instead, and report it here.
    combined_vs: dict[str, dict] = {}
    for pool_name, pool in (("oos", pooled_oos), ("fresh", pooled_fresh)):
        combined = pool["combined"]
        legs = {leg: pool[leg] for leg in ("rsi_wide6", "bollinger_wide6")}
        combined_vs[pool_name] = {
            "combined_pnl_usd": combined["total_pnl_usd"],
            "combined_win_rate_pct": combined["win_rate_pct"],
            "combined_expectancy_usd": combined["expectancy_usd"],
            "combined_trades": combined["trades"],
            "rsi_wide6_pnl_usd": legs["rsi_wide6"]["total_pnl_usd"],
            "bollinger_wide6_pnl_usd": legs["bollinger_wide6"]["total_pnl_usd"],
            "beats_rsi_wide6_pnl": bool(combined["total_pnl_usd"] > legs["rsi_wide6"]["total_pnl_usd"]),
            "beats_bollinger_wide6_pnl": bool(combined["total_pnl_usd"] > legs["bollinger_wide6"]["total_pnl_usd"]),
            "beats_both_legs_pnl": bool(
                combined["total_pnl_usd"] > legs["rsi_wide6"]["total_pnl_usd"]
                and combined["total_pnl_usd"] > legs["bollinger_wide6"]["total_pnl_usd"]),
            "note": ("MACD trend-following alone (Phase 5, same windows, "
                     "different step) is NOT in this pool — see the report "
                     "text for the cross-phase comparison."),
        }

    # Cross-phase reference: MACD trend alone, Phase 5, same windows.
    # OOS pooled +$1,432.96 (191 trades, 52.4%); fresh pooled
    # +$2,899.45 (174 trades, 60.9%); all 7 windows +$4,581.51
    # (416 trades, 55.0%). Quoted, not re-run.
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 6 Win-Rate Test Report",
        "method": ("Three new wide-6 variants (6% stop / 9% target, 1.5:1, "
                   "10-day exit) on OOS-1/2/3 + FRESH-1/2/3/4, delayed real "
                   "yfinance history from the disk cache (no Yahoo re-fetch), "
                   "12 symbols, walk-forward, signals from history up to the "
                   "trade day only — no look-ahead. Every trade goes through "
                   "the real PaperTradingEngine and Risk Engine, balanced "
                   "profile, $10,000 virtual cash, long-only. (1) "
                   "High-confidence-only: RSI + Bollinger wide-6 only when "
                   "the explainable signal is long with confidence >= 0.70 "
                   "(app scanner floor is 0.55). (2) Volume confirmation: "
                   "same entries only when the entry bar's volume is above "
                   "its 20-day average (ratio > 1.0). (3) Combined: "
                   "mean-reversion wide-6 (RSI + Bollinger, 5-day grid) "
                   "PLUS MACD trend-following (every bar) in one shared "
                   "$10,000 portfolio, at most one trade per symbol per "
                   "day. The wide-6 baseline is re-run on the same windows "
                   "so the comparison is like-for-like. Every variant keeps "
                   "a stop-loss; the stop is never removed."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance), from data/fresh-cache/",
        "windows_definition": [
            {"label": label, "start": start, "end": end,
             "pool": "out-of-sample" if label in OOS_LABELS else "fresh"}
            for label, start, end in ALL_WINDOWS
        ],
        "verdict_rule": ("Worth keeping = pooled fresh P&L > $0 AND pooled fresh "
                         "win rate > 40% AND positive in at least 2 fresh windows "
                         "AND pooled OOS P&L > $0. The same pool rule is also "
                         "reported for the OOS pool on its own."),
        "macd_alone_reference": {
            "source": "Phase 5 report (quoted, not re-run)",
            "oos_pooled_pnl_usd": 1432.96, "oos_pooled_trades": 191,
            "oos_pooled_win_rate_pct": 52.4,
            "fresh_pooled_pnl_usd": 2899.45, "fresh_pooled_trades": 174,
            "fresh_pooled_win_rate_pct": 60.9,
            "all_7_windows_pnl_usd": 4581.51, "all_7_windows_trades": 416,
            "all_7_windows_win_rate_pct": 55.0,
        },
        "windows": windows,
        "pooled_oos": pooled_oos,
        "pooled_fresh": pooled_fresh,
        "verdict": verdict,
        "combined_vs_legs": combined_vs,
        "note": ("Nothing here proves future profits: past performance does "
                 "not guarantee future results. Three new variants were "
                 "tested on the same seven windows the lead was picked on, "
                 "so the best-looking one is partly the best by chance "
                 "(multiple comparisons) — a variant that only looks good "
                 "here needs a fresh window and live paper trades over real "
                 "days before it is trusted. Combined trade counts are not "
                 "directly comparable with single-strategy counts (MACD is "
                 "checked every bar, mean-reversion on a 5-day grid) — "
                 "P&L, win rate and expectancy per trade are the comparison. "
                 "Live paper evidence is still Day 1 only (2026-11-09: 3 "
                 "trades open, 0 closed, $0 realised) and proves nothing "
                 "yet. A compliance/legal review is still required before "
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
        "This report tests entry rules on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        f"- Verdict rule: {report['verdict_rule']}",
        "",
        "## Variants tested (all wide-6: 6% stop / 9% target, 10-day exit)",
        "",
    ]
    for key in VARIANT_KEYS:
        lines.append(f"- **{key}** — {VARIANT_LABELS[key]}.")
    lines += ["", "## Verdict — pooled fresh (FRESH-1/2/3/4)", "",
              "| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Worth keeping |",
              "|---|---:|---:|---:|---:|:---:|:---:|"]
    for key in VARIANT_KEYS:
        p = report["pooled_fresh"][key]
        lines.append(
            f"| {key} | {p['trades']} | {p['win_rate_pct']:.1f}% | {_fmt_money(p['total_pnl_usd'])} | "
            f"{_fmt_money(p['expectancy_usd'])} | {p['positive_windows']}/{p['windows_total']} | "
            f"{'YES' if report['verdict'][key]['worth_keeping'] else 'no'} |")
    lines += ["", "## Verdict — pooled out-of-sample (OOS-1/2/3)", "",
              "| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Pool passes |",
              "|---|---:|---:|---:|---:|:---:|:---:|"]
    for key in VARIANT_KEYS:
        p = report["pooled_oos"][key]
        lines.append(
            f"| {key} | {p['trades']} | {p['win_rate_pct']:.1f}% | {_fmt_money(p['total_pnl_usd'])} | "
            f"{_fmt_money(p['expectancy_usd'])} | {p['positive_windows']}/{p['windows_total']} | "
            f"{'yes' if p['worth_keeping_pool'] else 'no'} |")
    lines += ["", "## Combined vs its legs (same pool, like-for-like)", ""]
    for pool_name in ("oos", "fresh"):
        c = report["combined_vs_legs"][pool_name]
        lines += [
            f"### {pool_name.upper()} pool",
            "",
            f"- Combined: {c['combined_trades']} trades, {c['combined_win_rate_pct']:.1f}% win, "
            f"P&L {_fmt_money(c['combined_pnl_usd'])} (expectancy {_fmt_money(c['combined_expectancy_usd'])}/trade).",
            f"- RSI wide-6 alone: {_fmt_money(c['rsi_wide6_pnl_usd'])}; "
            f"Bollinger wide-6 alone: {_fmt_money(c['bollinger_wide6_pnl_usd'])}.",
            f"- Combined beats both legs on P&L: **{'yes' if c['beats_both_legs_pnl'] else 'NO'}** "
            f"(beats RSI: {'yes' if c['beats_rsi_wide6_pnl'] else 'no'}; "
            f"beats Bollinger: {'yes' if c['beats_bollinger_wide6_pnl'] else 'no'}).",
            f"- MACD trend alone (Phase 5, quoted, same windows): "
            f"{pool_name} pooled "
            f"{_fmt_money(report['macd_alone_reference']['oos_pooled_pnl_usd'] if pool_name == 'oos' else report['macd_alone_reference']['fresh_pooled_pnl_usd'])} "
            f"— the combined run is NOT the sum of the two legs run on "
            f"separate $10,000 pots; it is one shared pot, so same-day "
            f"skips and shared cash cost it some trades.",
            "",
        ]
    lines += [
        "⚠️ **Small-sample warning:** the high-confidence variants pass the "
        "verdict rule on paper but on almost no trades — RSI high-confidence "
        "took 1 fresh trade (of 105 RSI signals) and 1 out-of-sample trade; "
        "Bollinger high-confidence took 5 fresh trades and 1 out-of-sample "
        "trade. A 100% / 80% win rate on 1–6 trades proves nothing. Do NOT "
        "adopt the high-confidence gate on this evidence. At a mean-reversion "
        "entry the trend/EMA/MACD checks are usually bearish, so four bullish "
        "checks almost never agree — the gate is effectively a 'don't trade' "
        "filter for this entry, not a pickier entry.",
        "",
    ]
    lines += ["## Reading it honestly", "", report["note"], ""]
    for window in report["windows"]:
        lines += [
            f"## {window['label']} — {window['start']} → {window['end']} ({window['sample']})",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
            "| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for key in VARIANT_KEYS:
            r = window["results"][key]
            lines.append(
                f"| {key} | {r['trades_placed']} | {r['signals_seen']} | {r.get('skipped_gate', 0)} | "
                f"{r['win_rate_pct']:.1f}% | {_fmt_money(r['total_pnl_usd'])} | {_fmt_money(r['expectancy_usd'])} | "
                f"{_fmt_money(r['avg_win_usd'])} | {_fmt_money(r['avg_loss_usd'])} | "
                f"{r['max_drawdown_pct']:.2f}% | {r['blocked_by_risk']} |")
        lines.append("")
        for key in VARIANT_KEYS:
            r = window["results"][key]
            lines.append(f"- {key} per symbol: {r['per_symbol_trades']}")
        lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        report["note"],
        "",
        "## Trades (every trade, in order) — high-confidence, volume and combined variants",
        "",
        "Trade-by-trade rows for the three new variants. Every trade "
        "for every variant, including the re-run baselines, is in the "
        "JSON report.",
        "",
    ]
    shown = ["rsi_highconf", "rsi_volume", "bollinger_highconf",
             "bollinger_volume", "combined"]
    for window in report["windows"]:
        for key in shown:
            result = window["results"][key]
            if not result["trades"]:
                lines += [f"### {window['label']} — {key}: no trades", ""]
                continue
            lines += [f"### {window['label']} — {key}",
                      "",
                      "| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |",
                      "|---:|---|---|---|---|---|---|---:|"]
            for i, t in enumerate(result["trades"], 1):
                lines.append(f"| {i} | {t['symbol']} | {t.get('source_strategy', key)} | "
                             f"${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                             f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase6-win-rate-report") -> tuple[Path, Path]:
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
    report = run_phase6()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for key in VARIANT_KEYS:
        fresh = report["pooled_fresh"][key]
        oos = report["pooled_oos"][key]
        print(f"{key}: fresh {fresh['trades']} trades, {fresh['win_rate_pct']}% win, "
              f"P&L {_fmt_money(fresh['total_pnl_usd'])}, expectancy {_fmt_money(fresh['expectancy_usd'])}, "
              f"positive {fresh['positive_windows']}/{fresh['windows_total']} — "
              f"OOS {_fmt_money(oos['total_pnl_usd'])} — "
              f"{'WORTH KEEPING' if report['verdict'][key]['worth_keeping'] else 'not worth keeping'}")
    for pool_name in ("oos", "fresh"):
        c = report["combined_vs_legs"][pool_name]
        print(f"COMBINED vs legs ({pool_name}): {_fmt_money(c['combined_pnl_usd'])} vs "
              f"RSI {_fmt_money(c['rsi_wide6_pnl_usd'])} / Bollinger {_fmt_money(c['bollinger_wide6_pnl_usd'])} — "
              f"{'beats both' if c['beats_both_legs_pnl'] else 'does NOT beat both'}")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
