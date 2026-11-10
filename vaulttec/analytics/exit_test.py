"""Phase 4c — exit test: can a better exit raise the win rate?

Phase 4 found the main signal method break-even on real data
(40 trades, 40% win, -$92.40). Phase 4b found the mean-reversion
bounce is real — the no-stop native backtest replicates out-of-sample
(RSI +10.98%, Bollinger +12.95% mean of window means, positive in
3 of 3 windows) — but the risk-managed version with a 3% stop is
roughly break-even pooled (RSI +$341.61, Bollinger +$27.76) and is
killed in the falling OOS-2 window (Feb-Aug 2025) by stop whipsaw:
RSI was stopped out 18 of 21 times there (14.3% win).

This module tests the exit, not the entry, on the SAME three
out-of-sample windows as Phase 4b (OOS-1, OOS-2, OOS-3) plus the
Phase 4 window re-run and labelled in-sample. Same 12-symbol
universe, delayed real yfinance history, walk-forward, 5-day steps,
signals from history up to the trade day only (no look-ahead),
every trade through the real PaperTradingEngine and Risk Engine,
balanced profile, $10,000 virtual cash, long-only.

Exit variants (exact rules — every variant keeps a stop-loss; the
stop is never removed):

- baseline: 3% stop / 4.5% target (1.5:1) / 10-day exit — the
  Phase 4b Variant A control, re-run here as a sanity check.
- wide-5: 5% stop / 7.5% target (still 1.5:1) / 10-day exit.
- wide-6: 6% stop / 9% target (still 1.5:1) / 10-day exit.
- filter: 3% stop / 4.5% target / 10-day exit, PLUS the downtrend
  filter (see below) — oversold buys are skipped while the market
  is in a downtrend.
- time-5d: 3% stop / 4.5% target / 5-day exit (half the holding time).
- signal-exit: 3% stop, NO fixed take-profit target — exit when the
  entry signal reverses (RSI > 70 for RSI entries, close >= upper
  Bollinger Band for Bollinger entries) or after 10 days. The stop
  still protects every trade; the Risk Engine is passed no target,
  which it allows (it only checks risk/reward when a target exists).
  Method note: this codebase's RSI is undefined (NaN) after 14
  straight up-days (its loss term is zero), so a reversal that is
  a straight 14-day rise never registers as RSI > 70 and the trade
  then closes on the 10-day time exit instead.
- combined: the best base variant per strategy (see selection rule
  below) run WITH the downtrend filter added.

Downtrend filter — exact rule, fixed before the run: a buy is
skipped when BOTH hold on the trade day (history up to that day
only): (a) the close is below its 50-day simple moving average,
and (b) that 50-day average is falling — today's SMA-50 is below
the SMA-50 of 10 bars ago. If the SMA-50 is not yet defined
(fewer than 50 bars of history), the filter does NOT block — a
trade is never skipped on missing data. Warm-up is 70 days (up
from Phase 4b's 40) so the SMA-50 is defined on day one of every
window.

Combined-variant selection rule — fixed before the run, applied
per strategy: among the four new exit ideas (wide-5, wide-6,
time-5d, signal-exit), pick the one with the highest pooled
out-of-sample total paper P&L (OOS-1 + OOS-2 + OOS-3); run that
variant with the downtrend filter added. The combined result is
therefore post-hoc — it was chosen after seeing the base results
on these same windows — and is flagged as such in the report; it
needs a fresh window to confirm, it is not independent evidence.

Verdict rules — also fixed before the run, so the report cannot
move the goalposts: a variant "survives OOS-2" when its OOS-2
paper P&L is >= $0. A variant is "worth keeping" when its pooled
out-of-sample P&L is > $0 AND it survives OOS-2. Expectancy
(paper P&L per trade) is reported next to win rate throughout:
at 1.5:1 risk/reward the break-even win rate is exactly 40%, so a
win rate above 40% with a smaller average win can still lose
money, and a win rate below 40% with bigger wins can still profit.

Nothing here is live: paper only, no broker, no real money, no
leverage, no options. Past performance does not guarantee future
results, and any variant that looks good here still needs live
paper trades over real days plus a compliance/legal review before
real money is ever considered. Testing seven variants on the same
three windows also means the best-looking one is partly the best
by chance (multiple comparisons) — the report says so.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from ..db.models import UserProfile
from ..market.data import SCAN_UNIVERSE, YFinanceProvider
from ..market.indicators import bollinger_bands, rsi, sma
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import max_drawdown_pct
from .mean_reversion import (
    DatedYFinanceProvider,
    MIN_HISTORY_ROWS,
    OOS_WINDOWS,
    STRATEGIES,
    mean_reversion_trigger,
    strategy_label,
    trade_start_index,
)
from .validation import fetch_histories

WARMUP_DAYS = 70  # SMA-50 must be defined on day one of every window
WINDOW_STEP_DAYS = 5
STARTING_CASH = PAPER_STARTING_CASH
FILTER_SMA_WINDOW = 50
FILTER_FALL_LOOKBACK = 10  # SMA-50 today vs SMA-50 this many bars ago
RISK_REWARD = 1.5

# Candidate base variants for the combined run (the filter variant
# itself is excluded — combining it with the filter would be itself).
COMBINED_CANDIDATES = ("wide-5", "wide-6", "time-5d", "signal-exit")


@dataclass(frozen=True)
class ExitVariant:
    """One exit rule-set. ``take_pct`` None means no fixed target
    (signal-exit variant only); the stop is always set."""

    id: str
    label: str
    stop_pct: float
    take_pct: float | None
    horizon_days: int
    use_filter: bool
    signal_exit: bool
    description: str


BASE_VARIANTS: tuple[ExitVariant, ...] = (
    ExitVariant("baseline", "Baseline — 3% stop / 4.5% target / 10 days",
                0.03, 0.045, 10, False, False,
                "Phase 4b Variant A control, re-run as a sanity check."),
    ExitVariant("wide-5", "Wider stop — 5% stop / 7.5% target / 10 days",
                0.05, 0.075, 10, False, False,
                "Wider stop so normal daily wobbles do not stop the trade out; target widens to keep 1.5:1."),
    ExitVariant("wide-6", "Wider stop — 6% stop / 9% target / 10 days",
                0.06, 0.09, 10, False, False,
                "Even wider stop; target widens to keep 1.5:1."),
    ExitVariant("filter", "Downtrend filter — 3% stop / 4.5% target / 10 days + filter",
                0.03, 0.045, 10, True, False,
                "Same exits as baseline, but oversold buys are skipped while the downtrend filter says the market is falling."),
    ExitVariant("time-5d", "Time-based exit — 3% stop / 4.5% target / 5 days",
                0.03, 0.045, 5, False, False,
                "Half the holding time: if the bounce has not happened in 5 days, exit instead of waiting 10."),
    ExitVariant("signal-exit", "Signal exit — 3% stop, no fixed target, exit on reversal / 10 days",
                0.03, None, 10, False, True,
                "Stop still protects every trade; otherwise hold until the entry signal reverses (RSI > 70 / close >= upper band) or 10 days pass. No fixed target — the Risk Engine is passed no target."),
)

VARIANT_IDS = tuple(v.id for v in BASE_VARIANTS)


def variant_by_id(variant_id: str) -> ExitVariant:
    for variant in BASE_VARIANTS:
        if variant.id == variant_id:
            return variant
    raise ValueError(f"unknown exit variant: {variant_id}")


def downtrend_filter(history_up_to_day: pd.DataFrame) -> bool:
    """True when the market is in a downtrend on the last bar of
    ``history_up_to_day`` — history up to the trade day only, so no
    look-ahead. Rule: close below its 50-day SMA AND the 50-day SMA
    is falling (today's SMA-50 below the SMA-50 of 10 bars ago).
    Returns False when the SMA-50 is not yet defined — a trade is
    never skipped on missing data."""
    closes = history_up_to_day["close"].reset_index(drop=True)
    if len(closes) < FILTER_SMA_WINDOW + FILTER_FALL_LOOKBACK:
        return False
    sma50 = sma(closes, FILTER_SMA_WINDOW)
    today = sma50.iloc[-1]
    ten_ago = sma50.iloc[-1 - FILTER_FALL_LOOKBACK]
    if pd.isna(today) or pd.isna(ten_ago):
        return False
    return bool(closes.iloc[-1] < today and today < ten_ago)


def mean_reversion_exit_signal(strategy: str, history_up_to_day: pd.DataFrame) -> bool:
    """True when the entry signal has reversed on the last bar of
    ``history_up_to_day``: RSI above 70 for RSI entries, close at or
    above the upper Bollinger Band for Bollinger entries."""
    closes = history_up_to_day["close"].reset_index(drop=True)
    if strategy == "rsi":
        value = rsi(closes).iloc[-1]
        return bool(not pd.isna(value) and value > 70)
    if strategy == "bollinger":
        bands = bollinger_bands(closes)
        upper = bands["upper"].iloc[-1]
        return bool(not pd.isna(upper) and closes.iloc[-1] >= upper)
    raise ValueError(f"unknown mean-reversion strategy: {strategy}")


def _exit_trade_exit(history: pd.DataFrame, entry_index: int, entry: float,
                     stop: float, take: float | None, horizon_days: int,
                     strategy: str, signal_exit: bool) -> tuple[float, str, int]:
    """Walk forward from the entry bar and find the exit.

    Returns (exit_price, exit_reason, days_held). Each day, in this
    order: stop-loss first (conservative — if the day's low touched
    the stop, the trade is stopped out), then the fixed target if
    one exists, then the reversal signal if ``signal_exit``. If
    nothing fires within the horizon, exit at the close on the
    horizon day. ``take`` None means no fixed target exists.
    """
    for offset in range(1, horizon_days + 1):
        idx = entry_index + offset
        if idx >= len(history):
            break
        bar = history.iloc[idx]
        if bar["low"] <= stop:
            return round(float(stop), 2), "stop-loss", offset
        if take is not None and bar["high"] >= take:
            return round(float(take), 2), "take-profit", offset
        if signal_exit and mean_reversion_exit_signal(strategy, history.iloc[: idx + 1]):
            return round(float(bar["close"]), 2), "signal exit (reversal)", offset
    last = min(entry_index + horizon_days, len(history) - 1)
    return (round(float(history.iloc[last]["close"]), 2),
            f"time exit ({horizon_days} days)", last - entry_index)


def _summarise_variant(strategy: str, variant: ExitVariant,
                       trade_rows: list[dict], counts: Counter,
                       starting_cash: float, equity: list[float]) -> dict:
    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    trades = len(trade_rows)
    return {
        "strategy": strategy_label(strategy),
        "variant_id": variant.id,
        "variant": variant.label,
        "rules": variant.description,
        "stop_pct": variant.stop_pct,
        "take_pct": variant.take_pct,
        "horizon_days": variant.horizon_days,
        "use_filter": variant.use_filter,
        "signal_exit": variant.signal_exit,
        "trades_placed": trades,
        "signals_seen": counts["signals_seen"],
        "windows_checked": counts["windows_checked"],
        "skipped_filter": counts["skipped_filter"],
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


def run_variant_validation(strategy: str, variant: ExitVariant,
                           histories: dict[str, pd.DataFrame],
                           window_start: str | None = None,
                           starting_cash: float = STARTING_CASH,
                           risk_profile: str = "balanced",
                           symbols: list[str] | None = None) -> dict:
    """Walk-forward validation for one mean-reversion strategy under
    one exit variant, over already-fetched histories.

    ``window_start`` marks where trading starts; earlier rows are
    warm-up. When None, trading starts at row ``MIN_HISTORY_ROWS``
    (used by tests with stub histories and by the in-sample window).
    Every triggered trade goes through the real PaperTradingEngine
    and Risk Engine with the variant's stop / target / horizon.
    For the signal-exit variant the Risk Engine is passed no target
    (it allows that — it only checks risk/reward when a target
    exists); the stop is always set, for every variant.
    ``symbols`` limits the run to the given symbols (default: the
    full scan universe) — Phase 7 uses it for crypto-only and
    wider-symbol runs; symbols missing from ``histories`` are
    skipped, never invented.
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
                     if window_start else MIN_HISTORY_ROWS)
        for start in range(start_idx, len(history) - variant.horizon_days, WINDOW_STEP_DAYS):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            if not mean_reversion_trigger(strategy, window_history):
                continue
            counts["signals_seen"] += 1
            if variant.use_filter and downtrend_filter(window_history):
                counts["skipped_filter"] += 1
                continue
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            entry = float(history.iloc[start]["close"])
            stop = round(entry * (1 - variant.stop_pct), 2)
            if variant.take_pct is not None:
                # Build the target from the *rounded* stop and round
                # it UP to the cent, so the trade is always at least
                # 1.5:1 after cent-rounding.
                take = math.ceil((entry + RISK_REWARD * (entry - stop)) * 100) / 100
            else:
                take = None
            raw_qty = risk.position_size(portfolio.value({symbol: entry}), entry)
            quantity = math.floor(raw_qty * 10000) / 10000
            if quantity <= 0:
                counts["skipped_too_small"] += 1
                counts["too_small_by_symbol"][symbol] += 1
                continue
            engine.realised_pnl = 0.0  # each window is a different simulated day
            trade = engine.place_order(
                symbol, "buy", quantity, entry, stop, take,
                reason=f"{strategy} mean-reversion trigger, exit variant {variant.id}",
                source="phase4c-exit-test")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade_exit(
                history, start, entry, stop, take, variant.horizon_days,
                strategy, variant.signal_exit)
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
    return _summarise_variant(strategy, variant, trade_rows, counts, starting_cash, equity)


def run_window_exits(label: str, start: str, end: str, sample: str,
                     variants: tuple[ExitVariant, ...] = BASE_VARIANTS,
                     symbols: list[str] | None = None,
                     provider=None) -> tuple[dict, dict]:
    """Run both strategies under ``variants`` on one calendar window.

    Returns (window_report, histories) — the histories are returned
    separately (not in the report dict) so the combined variant can
    be run later on the exact same fetched data. The provider uses
    70 days of warm-up so the SMA-50 filter is defined on day one.
    """
    symbols = symbols or list(SCAN_UNIVERSE)
    if provider is None:
        provider = DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS)
    histories, failed, summary = fetch_histories(provider, symbols, days=180)
    strategies = {}
    for strategy in STRATEGIES:
        strategies[strategy] = {
            variant.id: run_variant_validation(strategy, variant, histories,
                                               window_start=start)
            for variant in variants
        }
    window = {
        "label": label, "start": start, "end": end, "sample": sample,
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "strategies": strategies,
    }
    return window, histories


def run_insample_window_exits(variants: tuple[ExitVariant, ...] = BASE_VARIANTS,
                              symbols: list[str] | None = None) -> tuple[dict, dict]:
    """Re-run both strategies under ``variants`` on the Phase 4 window
    (yfinance 180d period, as of today) — labelled in-sample, for
    comparison. Same shape as run_window_exits."""
    symbols = symbols or list(SCAN_UNIVERSE)
    histories, failed, summary = fetch_histories(YFinanceProvider(), symbols, days=180)
    strategies = {}
    for strategy in STRATEGIES:
        strategies[strategy] = {
            variant.id: run_variant_validation(strategy, variant, histories)
            for variant in variants
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


def _pool_variant(windows: list[dict], strategy: str, variant_id: str) -> dict:
    """Pool the out-of-sample windows for one strategy/variant."""
    results = [w["strategies"][strategy][variant_id] for w in windows]
    trades = sum(r["trades_placed"] for r in results)
    wins = sum(r["wins"] for r in results)
    pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
    oos2 = next((r for w, r in zip(windows, results) if w["label"] == "OOS-2"), None)
    return {
        "variant_id": variant_id,
        "trades": trades,
        "wins": wins,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "total_pnl_usd": pnl,
        "total_pnl_pct": round(pnl / (STARTING_CASH * len(windows)) * 100, 2) if windows else 0.0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "per_window_pnl_usd": {w["label"]: r["total_pnl_usd"] for w, r in zip(windows, results)},
        "per_window_win_rate_pct": {w["label"]: r["win_rate_pct"] for w, r in zip(windows, results)},
        "per_window_trades": {w["label"]: r["trades_placed"] for w, r in zip(windows, results)},
        "oos2_pnl_usd": oos2["total_pnl_usd"] if oos2 else None,
        "oos2_win_rate_pct": oos2["win_rate_pct"] if oos2 else None,
        "survives_oos2": bool(oos2 is not None and oos2["total_pnl_usd"] >= 0),
        "worth_keeping": bool(pnl > 0 and oos2 is not None and oos2["total_pnl_usd"] >= 0),
    }


def select_best_variant(pooled: dict, strategy: str) -> str:
    """Combined-variant selection rule, fixed before the run: among
    the four new exit ideas (wide-5, wide-6, time-5d, signal-exit),
    pick the one with the highest pooled out-of-sample total paper
    P&L for this strategy. Ties go to the first listed candidate."""
    best_id, best_pnl = None, None
    for candidate in COMBINED_CANDIDATES:
        pnl = pooled[strategy][candidate]["total_pnl_usd"]
        if best_pnl is None or pnl > best_pnl:
            best_id, best_pnl = candidate, pnl
    return best_id


def combined_variant(base: ExitVariant) -> ExitVariant:
    """The combined variant: a base exit idea run WITH the downtrend
    filter added. Same stop/target/horizon as the base variant."""
    return ExitVariant(
        id=f"combined-{base.id}-filter",
        label=f"Combined — {base.label} + downtrend filter",
        stop_pct=base.stop_pct, take_pct=base.take_pct,
        horizon_days=base.horizon_days, use_filter=True,
        signal_exit=base.signal_exit,
        description=(f"{base.description} PLUS the downtrend filter: "
                     "oversold buys are skipped while the market is in a downtrend. "
                     "Post-hoc: the base variant was chosen after seeing the base "
                     "results on these same windows, so this result needs a fresh "
                     "window to confirm."),
    )


def run_exit_test() -> dict:
    """Run the whole exit test: 3 out-of-sample windows + the
    in-sample Phase 4 window, both strategies, six base variants;
    then select the best base variant per strategy and run it with
    the downtrend filter added (the combined variant) on the same
    fetched histories."""
    oos_windows: list[dict] = []
    oos_histories: list[dict] = []
    for label, start, end in OOS_WINDOWS:
        window, histories = run_window_exits(label, start, end, "out-of-sample")
        oos_windows.append(window)
        oos_histories.append(histories)
    insample, insample_histories = run_insample_window_exits()

    pooled: dict[str, dict] = {}
    for strategy in STRATEGIES:
        pooled[strategy] = {
            variant.id: _pool_variant(oos_windows, strategy, variant.id)
            for variant in BASE_VARIANTS
        }

    combined_selection: dict[str, dict] = {}
    combined_variants: dict[str, ExitVariant] = {}
    for strategy in STRATEGIES:
        best_id = select_best_variant(pooled, strategy)
        base = variant_by_id(best_id)
        combined = combined_variant(base)
        combined_variants[strategy] = combined
        combined_selection[strategy] = {
            "best_base_variant": best_id,
            "combined_variant_id": combined.id,
            "reason": (f"Highest pooled out-of-sample total paper P&L among "
                       f"{list(COMBINED_CANDIDATES)} for {strategy_label(strategy)} "
                       f"(${pooled[strategy][best_id]['total_pnl_usd']:,.2f}). "
                       "Post-hoc selection on these same windows — needs a fresh window to confirm."),
        }

    # Combined pass on the exact same fetched histories.
    for window, histories in zip(oos_windows, oos_histories):
        for strategy in STRATEGIES:
            combined = combined_variants[strategy]
            window["strategies"][strategy][combined.id] = run_variant_validation(
                strategy, combined, histories, window_start=window["start"])
    for strategy in STRATEGIES:
        combined = combined_variants[strategy]
        insample["strategies"][strategy][combined.id] = run_variant_validation(
            strategy, combined, insample_histories)
    for strategy in STRATEGIES:
        combined = combined_variants[strategy]
        pooled[strategy][combined.id] = _pool_variant(oos_windows, strategy, combined.id)

    all_variant_ids = [v.id for v in BASE_VARIANTS] + [
        combined_variants[s].id for s in STRATEGIES]
    verdict = {}
    for strategy in STRATEGIES:
        best_id = max(pooled[strategy],
                      key=lambda vid: pooled[strategy][vid]["total_pnl_usd"])
        verdict[strategy] = {
            "best_variant_by_pooled_pnl": best_id,
            "best_pooled_pnl_usd": pooled[strategy][best_id]["total_pnl_usd"],
            "variants_surviving_oos2": [vid for vid in pooled[strategy]
                                        if pooled[strategy][vid]["survives_oos2"]],
            "variants_worth_keeping": [vid for vid in pooled[strategy]
                                       if pooled[strategy][vid]["worth_keeping"]],
        }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 4c Exit Test Report",
        "method": ("Exit test on the SAME three out-of-sample windows as "
                   "Phase 4b (OOS-1, OOS-2, OOS-3) plus the Phase 4 window "
                   "re-run and labelled in-sample: delayed real market "
                   "history from yfinance (free), 70 days of warm-up "
                   "history before each window so the SMA-50 filter is "
                   "defined on day one, 12 symbols, 5-day walk-forward "
                   "steps, signals from history up to the trade day only "
                   "— no look-ahead. Every trade goes through the real "
                   "PaperTradingEngine and Risk Engine, balanced profile, "
                   "$10,000 virtual cash, long-only. Every variant keeps "
                   "a stop-loss; the stop is never removed."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "downtrend_filter_rule": ("Skip the buy when BOTH hold on the trade "
                                  "day (history up to that day only): (a) the "
                                  "close is below its 50-day simple moving "
                                  "average, and (b) that 50-day average is "
                                  "falling — today's SMA-50 is below the "
                                  "SMA-50 of 10 bars ago. If the SMA-50 is "
                                  "not yet defined, the filter does NOT block."),
        "variants": [
            {"id": v.id, "label": v.label, "stop_pct": v.stop_pct,
             "take_pct": v.take_pct, "horizon_days": v.horizon_days,
             "use_filter": v.use_filter, "signal_exit": v.signal_exit,
             "description": v.description}
            for v in BASE_VARIANTS
        ] + [
            {"id": combined_variants[s].id, "label": combined_variants[s].label,
             "stop_pct": combined_variants[s].stop_pct,
             "take_pct": combined_variants[s].take_pct,
             "horizon_days": combined_variants[s].horizon_days,
             "use_filter": True, "signal_exit": combined_variants[s].signal_exit,
             "description": combined_variants[s].description}
            for s in STRATEGIES
        ],
        "combined_selection": combined_selection,
        "combined_selection_rule": ("Per strategy, the base variant with the "
                                    "highest pooled out-of-sample total paper "
                                    "P&L among wide-5, wide-6, time-5d and "
                                    "signal-exit, run with the downtrend filter "
                                    "added. Post-hoc — chosen after seeing the "
                                    "base results on these same windows."),
        "verdict_rules": ("A variant 'survives OOS-2' when its OOS-2 paper "
                          "P&L is >= $0. A variant is 'worth keeping' when "
                          "its pooled out-of-sample P&L is > $0 AND it "
                          "survives OOS-2. At 1.5:1 risk/reward the "
                          "break-even win rate is exactly 40%."),
        "oos_windows": oos_windows,
        "insample_window": insample,
        "pooled_out_of_sample": pooled,
        "verdict": verdict,
        "note": ("Nothing here proves future profits: past performance "
                 "does not guarantee future results. Seven variants were "
                 "tested on the same three windows, so the best-looking "
                 "one is partly the best by chance (multiple comparisons) "
                 "— a variant that only looks good here needs a fresh "
                 "window before it is trusted. The combined variant was "
                 "selected after seeing the base results on these same "
                 "windows, so it is not independent evidence either. "
                 "Live paper trades over real days plus a compliance/legal "
                 "review are still required before any real money is "
                 "considered."),
    }


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def _variant_short(variant_id: str) -> str:
    return variant_id


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['title']}",
        "",
        f"Generated: {report['generated_at']} (UTC)",
        "",
        "> Risk disclosure: trading involves substantial risk of loss. "
        "This report tests exit rules on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        f"- Downtrend filter: {report['downtrend_filter_rule']}",
        f"- Combined-variant selection: {report['combined_selection_rule']}",
        f"- Verdict rules: {report['verdict_rules']}",
        "",
        "## Exit variants tested",
        "",
    ]
    for variant in report["variants"]:
        take = "no fixed target" if variant["take_pct"] is None else f"{variant['take_pct']:.1%} target"
        lines.append(
            f"- **{variant['id']}** — {variant['label']}: "
            f"{variant['stop_pct']:.0%} stop / {take} / {variant['horizon_days']}-day exit, "
            f"filter {'on' if variant['use_filter'] else 'off'}, "
            f"signal exit {'on' if variant['signal_exit'] else 'off'}. {variant['description']}")
    lines += ["", "## Pooled out-of-sample verdict — 3 windows, per strategy", ""]
    for strategy in STRATEGIES:
        lines += [f"### {strategy_label(strategy)}", "",
                  "| Variant | Trades | Win rate | P&L | Expectancy / trade | OOS-2 P&L | Survives OOS-2 | Worth keeping |",
                  "|---|---:|---:|---:|---:|---:|:---:|:---:|"]
        for variant_id, pooled in report["pooled_out_of_sample"][strategy].items():
            lines.append(
                f"| {variant_id} | {pooled['trades']} | {pooled['win_rate_pct']:.1f}% | "
                f"{_fmt_money(pooled['total_pnl_usd'])} | {_fmt_money(pooled['expectancy_usd'])} | "
                f"{_fmt_money(pooled['oos2_pnl_usd']) if pooled['oos2_pnl_usd'] is not None else 'n/a'} | "
                f"{'yes' if pooled['survives_oos2'] else 'NO'} | "
                f"{'yes' if pooled['worth_keeping'] else 'no'} |")
        lines.append("")
    lines += ["## Verdict", ""]
    for strategy in STRATEGIES:
        verdict = report["verdict"][strategy]
        selection = report["combined_selection"][strategy]
        lines += [
            f"### {strategy_label(strategy)}",
            "",
            f"- Best variant by pooled out-of-sample P&L: **{verdict['best_variant_by_pooled_pnl']}** "
            f"({_fmt_money(verdict['best_pooled_pnl_usd'])}).",
            f"- Variants surviving OOS-2 (the falling window): "
            f"{verdict['variants_surviving_oos2'] or 'none'}.",
            f"- Variants worth keeping (pooled P&L > $0 AND survives OOS-2): "
            f"{verdict['variants_worth_keeping'] or 'none'}.",
            f"- Combined variant: {selection['combined_variant_id']} — {selection['reason']}",
            "",
        ]
    lines += [
        "## Reading it honestly",
        "",
        "A wider stop lets the trade survive normal wobbles, but it also "
        "lets a real fall run further before the stop catches it — the "
        "average loss grows with the stop, so the win rate has to rise "
        "enough to pay for bigger losses. A downtrend filter throws away "
        "trades, including some that would have bounced, and it only helps "
        "if the falling windows are where the losses actually came from. "
        "A 5-day exit cuts losing trades short, but it also cuts winning "
        "bounces short. A signal exit has no fixed target, so a few big "
        "winners can carry it — or a few big losers can sink it — and its "
        "expectancy, not its win rate, is the number that matters. "
        "None of these variants removes the stop-loss: the stop is what "
        "keeps one bad trade from wiping out the account, and the "
        "no-stop backtest numbers from Phase 4b overstate what a "
        "tradeable strategy earns for exactly that reason. One quirk "
        "worth knowing: this codebase's RSI is undefined after 14 "
        "straight up-days, so a reversal that is a straight 14-day "
        "rise never registers as RSI > 70 and the signal-exit variant "
        "then closes on the 10-day time exit instead.",
        "",
    ]
    for window in report["oos_windows"] + [report["insample_window"]]:
        lines += [
            f"## {window['label']} — {window['start']} → {window['end']} "
            f"({window['sample']})",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
        ]
        for strategy in STRATEGIES:
            lines += [f"### {strategy_label(strategy)}", "",
                      "| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |",
                      "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|"]
            for variant_id, result in window["strategies"][strategy].items():
                lines.append(
                    f"| {variant_id} | {result['trades_placed']} | {result['win_rate_pct']:.1f}% | "
                    f"{_fmt_money(result['total_pnl_usd'])} | {_fmt_money(result['expectancy_usd'])} | "
                    f"{_fmt_money(result['avg_win_usd'])} | {_fmt_money(result['avg_loss_usd'])} | "
                    f"{result['max_drawdown_pct']:.2f}% | {result['exits']} | {result['blocked_by_risk']} | "
                    f"{result['skipped_filter']} |")
            lines.append("")
            for variant_id, result in window["strategies"][strategy].items():
                lines.append(f"- {variant_id} per symbol: {result['per_symbol_trades']}")
            lines.append("")
    lines += [
        "## What this does and does not prove",
        "",
        report["note"],
        "",
        "## Trades (every trade, in order) — baseline and combined variants",
        "",
        "Trade-by-trade rows for the baseline and the combined variant "
        "are printed here. Every trade for every variant is in the JSON "
        "report — the Markdown would be seven times as long otherwise.",
        "",
    ]
    shown = ["baseline"] + [report["combined_selection"][s]["combined_variant_id"]
                            for s in STRATEGIES]
    for window in report["oos_windows"] + [report["insample_window"]]:
        for strategy in STRATEGIES:
            for variant_id in shown:
                result = window["strategies"][strategy].get(variant_id)
                if result is None:
                    continue
                if not result["trades"]:
                    lines += [f"### {window['label']} — {strategy_label(strategy)} — {variant_id}: no trades", ""]
                    continue
                lines += [f"### {window['label']} — {strategy_label(strategy)} — {variant_id}",
                          "",
                          "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
                          "|---:|---|---|---|---|---:|---:|"]
                for i, t in enumerate(result["trades"], 1):
                    lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                                 f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
                lines.append("")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase4c-exit-test-report") -> tuple[Path, Path]:
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
    report = run_exit_test()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for strategy in STRATEGIES:
        for variant_id, pooled in report["pooled_out_of_sample"][strategy].items():
            print(f"{strategy} / {variant_id}: {pooled['trades']} trades, "
                  f"{pooled['win_rate_pct']}% win, P&L {_fmt_money(pooled['total_pnl_usd'])}, "
                  f"expectancy {_fmt_money(pooled['expectancy_usd'])}, "
                  f"OOS-2 {_fmt_money(pooled['oos2_pnl_usd'])} "
                  f"({'survives' if pooled['survives_oos2'] else 'does NOT survive'})")
        verdict = report["verdict"][strategy]
        print(f"{strategy}: best = {verdict['best_variant_by_pooled_pnl']}, "
              f"worth keeping = {verdict['variants_worth_keeping'] or 'none'}")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
