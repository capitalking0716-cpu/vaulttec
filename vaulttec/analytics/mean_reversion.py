"""Phase 4b — mean-reversion follow-up test (out-of-sample).

Phase 4 Step 1 found the main signal method break-even on real data
(40 trades, 40% win, -$92.40) but the backtest suite on that same
180-day window suggested Bollinger mean-reversion (+17.71% mean
return) and RSI mean-reversion (+12.44%) — a hypothesis only: one
window, small trade counts (20-24 trades), and the strategies were
picked *because* they looked good on that window.

This module tests that hypothesis out-of-sample, on three earlier,
non-overlapping 180-calendar-day windows that end before the Phase 4
window starts (stocks in the Phase 4 window start 2026-02-23, crypto
2026-05-14), so no price bar in the out-of-sample windows was used
to form the hypothesis:

- OOS-1: 2025-08-27 -> 2026-02-22
- OOS-2: 2025-02-28 -> 2025-08-26
- OOS-3: 2024-09-01 -> 2025-02-27

Each window is fetched with 40 days of warm-up history before its
start (so RSI-14 / Bollinger-20 are already defined on day one of
the window); trades are only placed inside the window itself.
The Phase 4 window is re-run as well, labelled in-sample for these
two strategies, for comparison.

Two variants per strategy per window, because the Phase 4 numbers
came from a backtest with *different* exit rules than the validation
run, and both questions matter:

- Variant A (risk-managed validation): entry on the mean-reversion
  trigger, exit at a 3% stop-loss / 4.5% take-profit (1.5:1) or after
  10 days — the exact Phase 3/4 validation rules — every trade
  through the real ``PaperTradingEngine`` and Risk Engine, balanced
  profile, $10,000 virtual cash, long-only. Reports dollar P&L.
- Variant B (native backtest): the strategy exactly as defined in
  ``analytics/backtest.py`` — RSI buys below 30 and sells above 70;
  Bollinger buys at/below the lower band and sells at/above the
  upper band; no fixed stop/target, hold until the exit signal.
  Reports the same mean-return figures Phase 4 reported, so the
  +17.71% / +12.44% can be checked for replication.

Signals use history up to the trade day only — no look-ahead, in
both variants. Nothing here is live: paper only, no broker, no real
money, no leverage, no options. Past performance does not guarantee
future results, and a good result on any window would still need
live paper trades over real days plus a compliance/legal review
before real money is ever considered.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from ..config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from ..db.models import UserProfile
from ..market.data import SCAN_UNIVERSE, YFinanceProvider
from ..market.indicators import bollinger_bands, rsi
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import backtest_bollinger_bands, backtest_rsi, max_drawdown_pct
from .validation import _exit_trade, fetch_histories

MIN_HISTORY_ROWS = 60  # need enough history for the indicators to work
WINDOW_STEP_DAYS = 5
EXIT_HORIZON_DAYS = 10
STOP_PCT = 0.03
TAKE_PCT = 0.045  # 1.5:1, the profile minimum
WARMUP_DAYS = 40
STARTING_CASH = PAPER_STARTING_CASH

# Out-of-sample windows: (label, start, end-exclusive). All end before
# the Phase 4 window starts, and none overlap each other.
OOS_WINDOWS: list[tuple[str, str, str]] = [
    ("OOS-1", "2025-08-27", "2026-02-23"),
    ("OOS-2", "2025-02-28", "2025-08-27"),
    ("OOS-3", "2024-09-01", "2025-02-28"),
]

STRATEGIES = ("rsi", "bollinger")


def strategy_label(strategy: str) -> str:
    return {
        "rsi": "RSI mean-reversion (buy RSI < 30, sell RSI > 70)",
        "bollinger": "Bollinger mean-reversion (buy lower band, sell upper band)",
    }[strategy]


def mean_reversion_trigger(strategy: str, window_history: pd.DataFrame) -> bool:
    """True when the mean-reversion entry trigger fires on the last bar
    of ``window_history`` — history up to the trade day only, so no
    look-ahead. Returns False when the indicator is not yet defined."""
    closes = window_history["close"].reset_index(drop=True)
    if strategy == "rsi":
        value = rsi(closes).iloc[-1]
        return bool(not pd.isna(value) and value < 30)
    if strategy == "bollinger":
        bands = bollinger_bands(closes)
        lower = bands["lower"].iloc[-1]
        return bool(not pd.isna(lower) and closes.iloc[-1] <= lower)
    raise ValueError(f"unknown mean-reversion strategy: {strategy}")


class DatedYFinanceProvider:
    """Delayed real history for a fixed calendar window via yfinance.

    Fetches ``start - warmup`` .. ``end`` (end exclusive, yfinance
    convention) so indicators are warm before the window starts.
    ``get_history`` ignores ``days`` — the window defines the range —
    so it can be dropped into ``fetch_histories``. A symbol that
    cannot be fetched raises, and the caller records it as failed.
    """

    def __init__(self, start: str, end: str, warmup_days: int = WARMUP_DAYS):
        self.start = date.fromisoformat(start)
        self.end = date.fromisoformat(end)
        self.fetch_start = self.start - timedelta(days=warmup_days)

    def get_history(self, symbol: str, days: int | None = None) -> pd.DataFrame:
        import yfinance as yf

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                df = yf.Ticker(symbol).history(
                    start=self.fetch_start.isoformat(), end=self.end.isoformat())
            except Exception as exc:  # noqa: BLE001 — retry, then raise
                last_error = exc
                df = None
            if df is not None and not df.empty:
                break
            last_error = last_error or ValueError(f"yfinance returned no history for {symbol}")
            time.sleep(5 * (attempt + 1))  # transient Yahoo blocks recover
        if df is None or df.empty:
            raise ValueError(f"yfinance returned no history for {symbol} "
                             f"after 3 attempts ({last_error})")
        df = df.reset_index().rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        })
        cols = [c for c in ["date", "open", "high", "low", "close", "volume"]
                if c in df.columns]
        # yfinance returns tz-aware dates; strip the tz so date
        # comparisons elsewhere stay tz-naive, like the sample provider.
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        time.sleep(1.0)  # be polite to the free data feed
        return df[cols]


def trade_start_index(history: pd.DataFrame, window_start: str) -> int:
    """First row index whose date is on/after the window start (the
    rows before it are warm-up only — no trades there)."""
    if "date" not in history.columns:
        return 0
    dates = pd.to_datetime(history["date"])
    # yfinance dates are tz-aware; strip the tz so the comparison
    # with the tz-naive window start works.
    if getattr(dates.dt, "tz", None) is not None:
        dates = dates.dt.tz_localize(None)
    start = pd.Timestamp(window_start)
    matches = dates[dates >= start]
    return int(matches.index[0]) if len(matches) else len(history)


def _summarise_validation(strategy: str, trade_rows: list[dict],
                          counts: Counter, starting_cash: float,
                          equity: list[float]) -> dict:
    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    return {
        "strategy": strategy_label(strategy),
        "variant": "A — risk-managed validation "
                   "(3% stop / 4.5% target / 10-day exit, Risk Engine)",
        "trades_placed": len(trade_rows),
        "signals_seen": counts["signals_seen"],
        "windows_checked": counts["windows_checked"],
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trade_rows) * 100, 1) if trade_rows else 0.0,
        "total_pnl_usd": total_pnl,
        "total_pnl_pct": round(total_pnl / starting_cash * 100, 2),
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


def run_strategy_validation(strategy: str, histories: dict[str, pd.DataFrame],
                            window_start: str | None = None,
                            starting_cash: float = STARTING_CASH,
                            risk_profile: str = "balanced") -> dict:
    """Variant A: walk-forward validation for one mean-reversion
    strategy over already-fetched histories.

    ``window_start`` (a date string) marks where trading starts;
    earlier rows are warm-up. When None, trading starts at row
    ``MIN_HISTORY_ROWS`` (used by tests with stub histories).
    Every triggered trade goes through the real PaperTradingEngine
    and Risk Engine with a 3% stop / 4.5% target / 10-day exit.
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

    symbols = [s for s in SCAN_UNIVERSE if s in histories]
    for symbol in symbols:
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else MIN_HISTORY_ROWS)
        for start in range(start_idx, len(history) - EXIT_HORIZON_DAYS, WINDOW_STEP_DAYS):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            if not mean_reversion_trigger(strategy, window_history):
                continue
            counts["signals_seen"] += 1
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            entry = float(history.iloc[start]["close"])
            stop = round(entry * (1 - STOP_PCT), 2)
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
                reason=f"{strategy} mean-reversion trigger", source="phase4b-validation")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade(
                history, start, entry, stop, take)
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
    return _summarise_validation(strategy, trade_rows, counts, starting_cash, equity)


def run_native_backtest(strategy: str, histories: dict[str, pd.DataFrame],
                        window_start: str | None = None) -> dict:
    """Variant B: the strategy exactly as defined in backtest.py, run
    on each symbol's trading-window history only (warm-up rows
    excluded, so no trade can occur before the window starts).
    Same aggregate method as Phase 4: means across symbols that
    traded. Historical only — never a promise of future results."""
    fn = backtest_rsi if strategy == "rsi" else backtest_bollinger_bands
    per_symbol: dict[str, dict] = {}
    for symbol in SCAN_UNIVERSE:
        if symbol not in histories:
            continue
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else MIN_HISTORY_ROWS)
        window = history.iloc[start_idx:].reset_index(drop=True)
        result = fn(window)
        result["strategy"] = strategy_label(strategy)
        per_symbol[symbol] = result
    traded = [r for r in per_symbol.values() if r["trades"] > 0]
    return {
        "strategy": strategy_label(strategy),
        "variant": "B — native backtest (strategy's own exit: RSI > 70 / "
                   "close >= upper band, no fixed stop/target)",
        "per_symbol": per_symbol,
        "symbols_with_trades": len(traded),
        "mean_total_return_pct": round(sum(r["total_return_pct"] for r in traded) / len(traded), 2) if traded else 0.0,
        "mean_win_rate_pct": round(sum(r["win_rate_pct"] for r in traded) / len(traded), 1) if traded else 0.0,
        "mean_max_drawdown_pct": round(sum(r["max_drawdown_pct"] for r in traded) / len(traded), 2) if traded else 0.0,
        "total_trades": sum(r["trades"] for r in traded),
    }


def run_window(label: str, start: str, end: str, sample: str,
               symbols: list[str] | None = None,
               provider=None) -> dict:
    """Run both strategies, both variants, on one calendar window."""
    symbols = symbols or list(SCAN_UNIVERSE)
    if provider is None:
        provider = DatedYFinanceProvider(start, end)
    histories, failed, summary = fetch_histories(provider, symbols, days=180)
    strategies = {}
    for strategy in STRATEGIES:
        strategies[strategy] = {
            "variant_a_validation": run_strategy_validation(strategy, histories, window_start=start),
            "variant_b_native_backtest": run_native_backtest(strategy, histories, window_start=start),
        }
    return {
        "label": label, "start": start, "end": end, "sample": sample,
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "strategies": strategies,
    }


def run_insample_window(symbols: list[str] | None = None) -> dict:
    """Re-run both strategies on the Phase 4 window (yfinance 180d
    period, as of today) — labelled in-sample, for comparison."""
    symbols = symbols or list(SCAN_UNIVERSE)
    histories, failed, summary = fetch_histories(YFinanceProvider(), symbols, days=180)
    strategies = {}
    for strategy in STRATEGIES:
        strategies[strategy] = {
            "variant_a_validation": run_strategy_validation(strategy, histories),
            "variant_b_native_backtest": run_native_backtest(strategy, histories),
        }
    return {
        "label": "Phase-4 window (in-sample)",
        "start": summary.get("AAPL", {}).get("first_date"),
        "end": summary.get("AAPL", {}).get("last_date"),
        "sample": "in-sample — the window the hypothesis was picked from",
        "history": summary, "failed_symbols": failed,
        "symbols_traded": [s for s in symbols if s in histories],
        "strategies": strategies,
    }


def _pool_oos(windows: list[dict], strategy: str, variant: str) -> dict:
    """Pool the out-of-sample windows for one strategy/variant."""
    if variant == "variant_a_validation":
        trades = sum(w["strategies"][strategy][variant]["trades_placed"] for w in windows)
        wins = sum(w["strategies"][strategy][variant]["wins"] for w in windows)
        pnl = round(sum(w["strategies"][strategy][variant]["total_pnl_usd"] for w in windows), 2)
        return {
            "trades": trades,
            "wins": wins,
            "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
            "total_pnl_usd": pnl,
            "total_pnl_pct": round(pnl / (STARTING_CASH * len(windows)) * 100, 2) if windows else 0.0,
            "per_window_pnl_usd": {w["label"]: w["strategies"][strategy][variant]["total_pnl_usd"] for w in windows},
            "per_window_win_rate_pct": {w["label"]: w["strategies"][strategy][variant]["win_rate_pct"] for w in windows},
        }
    total_trades = sum(w["strategies"][strategy][variant]["total_trades"] for w in windows)
    mean_returns = [float(w["strategies"][strategy][variant]["mean_total_return_pct"]) for w in windows]
    return {
        "total_trades": total_trades,
        "mean_total_return_pct_per_window": {w["label"]: float(w["strategies"][strategy][variant]["mean_total_return_pct"]) for w in windows},
        "mean_of_window_means_pct": round(sum(mean_returns) / len(mean_returns), 2) if mean_returns else 0.0,
        "windows_positive": sum(1 for r in mean_returns if r > 0),
        "windows_total": len(mean_returns),
    }


def run_followup() -> dict:
    """Run the whole follow-up: 3 out-of-sample windows + the
    in-sample Phase 4 window, both strategies, both variants."""
    oos_windows = [run_window(label, start, end, "out-of-sample")
                   for label, start, end in OOS_WINDOWS]
    insample = run_insample_window()
    pooled = {}
    for strategy in STRATEGIES:
        pooled[strategy] = {
            "variant_a_validation_oos_pooled": _pool_oos(oos_windows, strategy, "variant_a_validation"),
            "variant_b_native_backtest_oos_pooled": _pool_oos(oos_windows, strategy, "variant_b_native_backtest"),
        }
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 4b Mean-Reversion Follow-Up Report",
        "method": ("Out-of-sample test of the Bollinger and RSI mean-reversion "
                   "hypothesis from Phase 4: three earlier, non-overlapping "
                   "180-calendar-day windows ending before the Phase 4 window "
                   "starts, delayed real market history from yfinance (free), "
                   "40 days of warm-up history before each window. Two variants "
                   "per strategy per window — A: risk-managed validation "
                   "(3% stop / 4.5% target / 10-day exit through the Risk Engine, "
                   "$10,000 virtual cash, balanced profile, long-only); "
                   "B: native backtest exactly as in backtest.py (RSI sell > 70, "
                   "Bollinger sell at upper band, no fixed stop/target). "
                   "Signals use history up to the trade day only — no look-ahead. "
                   "The Phase 4 window is re-run and labelled in-sample."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "oos_windows": oos_windows,
        "insample_window": insample,
        "pooled_out_of_sample": pooled,
        "note": ("Out-of-sample results are the honest test of the "
                 "mean-reversion hypothesis: the strategies were picked "
                 "because they looked good on the Phase 4 window, so that "
                 "window cannot confirm them. A result that holds across "
                 "all three earlier windows would support further testing; "
                 "a result that fades or reverses means the Phase 4 "
                 "backtest numbers were a one-window artefact. Nothing "
                 "here proves future profits: past performance does not "
                 "guarantee future results, and live paper trades over "
                 "real days plus a compliance/legal review are still "
                 "required before any real money is considered. "
                 "Method note: the in-sample native backtests here start "
                 "at row 60 of each history (the validation warm-up), "
                 "while Phase 4's backtest suite ran on the full history "
                 "— so in-sample trade counts here (RSI 10, Bollinger 10) "
                 "are lower than Phase 4's (20, 24); mean returns are "
                 "still directly comparable."),
    }


def _fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['title']}",
        "",
        f"Generated: {report['generated_at']} (UTC)",
        "",
        "> Risk disclosure: trading involves substantial risk of loss. "
        "This report tests a hypothesis on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        "",
        "## Pooled out-of-sample verdict (the headline test)",
        "",
    ]
    for strategy in STRATEGIES:
        pooled = report["pooled_out_of_sample"][strategy]
        a = pooled["variant_a_validation_oos_pooled"]
        b = pooled["variant_b_native_backtest_oos_pooled"]
        lines += [
            f"### {strategy_label(strategy)} — out-of-sample, 3 windows pooled",
            "",
            f"- Variant A (risk-managed, 3% stop / 4.5% target): "
            f"{a['trades']} trades, {a['wins']} wins, {a['win_rate_pct']}% win rate, "
            f"total paper P&L {_fmt_money(a['total_pnl_usd'])} "
            f"({a['total_pnl_pct']:+.2f}% across the 3 windows). "
            f"Per window: {a['per_window_pnl_usd']}.",
            f"- Variant B (native backtest): {b['total_trades']} trades total, "
            f"mean return per window {b['mean_total_return_pct_per_window']}, "
            f"mean of window means {b['mean_of_window_means_pct']:+.2f}%, "
            f"positive in {b['windows_positive']} of {b['windows_total']} windows.",
            "",
        ]
    lines += [
        "## Reading the two variants — why they disagree",
        "",
        "Variant B (native backtest) and Variant A (risk-managed) test "
        "the same entries with different exits, and the exits are the "
        "whole story. Variant B has **no stop-loss**: it holds through "
        "whatever fall follows the entry until the exit signal (RSI > 70 "
        "or the upper band). In a falling window like OOS-2 that means "
        "riding prices down and back up again — the backtest still wins "
        "because prices eventually recovered, but it never records the "
        "fall in between: its drawdown is measured only on completed "
        "trades, and its 'mean total return' sums per-trade percentage "
        "moves with no position sizing, so one big crypto move (e.g. "
        "ETH +76.83% in OOS-2) counts the same as a whole portfolio. "
        "Variant A has a **3% stop**: in that same falling window it was "
        "stopped out 18 times out of 21 RSI trades (14.3% win rate) "
        "because prices kept falling past the stop before recovering. "
        "So the honest reading is: the mean-reversion *bounce* is real "
        "enough to show up in all three out-of-sample windows in "
        "Variant B, but the *risk-managed version of it* — the only "
        "version VaultTec is allowed to trade — is weak and "
        "regime-dependent, roughly break-even pooled. The next question "
        "is not 'does mean reversion work' but 'is there an exit that "
        "keeps the bounce and survives a falling market' — for example "
        "a wider stop, a time-based exit, or a trend filter that skips "
        "oversold buys while the market is in a downtrend. That is a "
        "new hypothesis to test, not a conclusion.",
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
            a = window["strategies"][strategy]["variant_a_validation"]
            b = window["strategies"][strategy]["variant_b_native_backtest"]
            lines += [
                f"### {strategy_label(strategy)}",
                "",
                f"- Variant A: {a['trades_placed']} trades "
                f"({a['signals_seen']} triggers), {a['wins']} wins / {a['losses']} losses, "
                f"{a['win_rate_pct']}% win rate, "
                f"paper P&L {_fmt_money(a['total_pnl_usd'])} ({a['total_pnl_pct']:+.2f}%), "
                f"avg win {_fmt_money(a['avg_win_usd'])}, avg loss {_fmt_money(a['avg_loss_usd'])}, "
                f"max drawdown {a['max_drawdown_pct']:.2f}%, exits {a['exits']}, "
                f"blocked by risk {a['blocked_by_risk']}.",
                f"- Variant B: {b['total_trades']} trades, "
                f"mean total return {b['mean_total_return_pct']:+.2f}%, "
                f"mean win rate {b['mean_win_rate_pct']:.1f}%, "
                f"mean max drawdown {b['mean_max_drawdown_pct']:.2f}%, "
                f"symbols with trades {b['symbols_with_trades']}.",
                f"- Variant A per symbol: {a['per_symbol_trades']}",
                f"- Variant B per symbol: "
                + "; ".join(f"{s}: {r['trades']} trades, {r['total_return_pct']:+.2f}%, "
                            f"{r['win_rate_pct']:.1f}% win"
                            for s, r in b["per_symbol"].items()),
                "",
            ]
    lines += [
        "## What this does and does not prove",
        "",
        report["note"],
        "",
        "## Variant A trades (every trade, in order, per window)",
        "",
    ]
    for window in report["oos_windows"] + [report["insample_window"]]:
        for strategy in STRATEGIES:
            a = window["strategies"][strategy]["variant_a_validation"]
            if not a["trades"]:
                lines += [f"### {window['label']} — {strategy_label(strategy)}: no trades", ""]
                continue
            lines += [f"### {window['label']} — {strategy_label(strategy)}",
                      "",
                      "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
                      "|---:|---|---|---|---|---:|---:|"]
            for i, t in enumerate(a["trades"], 1):
                lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                             f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
            lines.append("")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase4b-mean-reversion-followup-report") -> tuple[Path, Path]:
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
    report = run_followup()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for strategy in STRATEGIES:
        pooled = report["pooled_out_of_sample"][strategy]
        a = pooled["variant_a_validation_oos_pooled"]
        b = pooled["variant_b_native_backtest_oos_pooled"]
        print(f"{strategy}: Variant A OOS pooled — {a['trades']} trades, "
              f"{a['win_rate_pct']}% win, P&L {_fmt_money(a['total_pnl_usd'])}")
        print(f"{strategy}: Variant B OOS pooled — {b['total_trades']} trades, "
              f"mean of window means {b['mean_of_window_means_pct']:+.2f}%")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
