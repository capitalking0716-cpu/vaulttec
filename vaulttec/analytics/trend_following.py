"""Phase 4e — trend-following test: the complement to mean-reversion.

Mean-reversion buys weakness (RSI < 30, or price at the lower
Bollinger Band) and bets on a bounce. Trend-following does the
opposite: it buys strength and bets the move keeps going. The two
should behave differently in a falling market — mean-reversion
keeps buying into the fall and gets stopped out, while
trend-following should mostly stay out, because there is no
uptrend to buy.

This module tests ONE trend rule, fixed before the run, on the
THREE FRESH windows from Phase 4d (FRESH-1/2/3) — the same
cached real Yahoo Finance histories, so no network fetch is
needed and no new data is fetched:

- Entry (long-only): on the trade day, using history up to that
  day only (no look-ahead), buy when the price is in an uptrend:
  close > 20-day SMA AND 20-day SMA > 50-day SMA. If either
  average is not yet defined, there is no trade — a trade is
  never placed on missing data.
- Exits: the same three variants as the fresh-window test —
  baseline (3% stop / 4.5% target / 10 days), wide-5 (5% / 7.5%
  / 10 days), wide-6 (6% / 9% / 10 days). Every trade goes
  through the real PaperTradingEngine and Risk Engine, balanced
  profile, $10,000 virtual cash, 5-day walk-forward steps.
  Every variant keeps a stop-loss; the stop is never removed.

Why these windows: the trend entry was never tested or selected
on FRESH-1/2/3 — mean-reversion was — so for this new entry rule
they are a fair first test. But two honest limits:

1. None of FRESH-1/2/3 is a falling window like OOS-2
   (Feb-Aug 2025, the window that killed mean-reversion). So
   this run CANNOT prove trend-following does better in a
   falling market — that needs OOS-2, whose histories are not
   cached and would need a fresh Yahoo fetch.
2. Three windows are still past prices. A good result here
   still needs live paper trades over real days plus a
   compliance/legal review before real money is ever considered.

Verdict rule — fixed before the run, same as Phase 4d: a variant
"holds up" when its pooled fresh-window paper P&L is > $0 AND
its pooled win rate is > 40% (the 1.5:1 break-even) AND it is
positive in at least 2 of the 3 fresh windows.
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
from ..market.indicators import sma
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import max_drawdown_pct
from .exit_test import (
    WARMUP_DAYS,
    WINDOW_STEP_DAYS,
    ExitVariant,
    _exit_trade_exit,
    variant_by_id,
)
from .fresh_window import (
    CACHE_DIR,
    FRESH_VARIANT_IDS,
    FRESH_VARIANTS,
    FRESH_WINDOWS,
    CachedDatedProvider,
    _pool_fresh,
)
from .mean_reversion import (
    DatedYFinanceProvider,
    MIN_HISTORY_ROWS,
    STRATEGIES,
    strategy_label,
    trade_start_index,
)
from .validation import fetch_histories

STARTING_CASH = PAPER_STARTING_CASH
TREND_STRATEGY = "trend"
TREND_LABEL = "Trend-following (buy uptrend: close > SMA-20 > SMA-50)"


def trend_trigger(window_history: pd.DataFrame) -> bool:
    """True when the price is in an uptrend on the last bar of
    ``window_history`` — history up to the trade day only, so no
    look-ahead. Rule: close > SMA-20 AND SMA-20 > SMA-50.
    Returns False when either average is not yet defined."""
    closes = window_history["close"].reset_index(drop=True)
    if len(closes) < 50:
        return False
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    s20, s50 = sma20.iloc[-1], sma50.iloc[-1]
    if pd.isna(s20) or pd.isna(s50):
        return False
    return bool(closes.iloc[-1] > s20 and s20 > s50)


def run_trend_variant(variant: ExitVariant, histories: dict[str, pd.DataFrame],
                      window_start: str | None = None,
                      starting_cash: float = STARTING_CASH,
                      risk_profile: str = "balanced") -> dict:
    """Walk-forward validation for the trend entry under one exit
    variant, over already-fetched histories. Mirrors
    ``run_variant_validation`` in exit_test.py, with the trend
    trigger in place of the mean-reversion trigger."""
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
    trade_rows: list[dict] = []
    equity = [starting_cash]

    symbols = [s for s in SCAN_UNIVERSE if s in histories]
    for symbol in symbols:
        history = histories[symbol].reset_index(drop=True)
        start_idx = (trade_start_index(history, window_start)
                     if window_start else MIN_HISTORY_ROWS)
        for start in range(start_idx, len(history) - variant.horizon_days, WINDOW_STEP_DAYS):
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            if not trend_trigger(window_history):
                continue
            counts["signals_seen"] += 1
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            entry = float(history.iloc[start]["close"])
            stop = round(entry * (1 - variant.stop_pct), 2)
            if variant.take_pct is not None:
                take = math.ceil((entry + 1.5 * (entry - stop)) * 100) / 100
            else:
                take = None
            raw_qty = risk.position_size(portfolio.value({symbol: entry}), entry)
            quantity = math.floor(raw_qty * 10000) / 10000
            if quantity <= 0:
                counts["skipped_too_small"] += 1
                continue
            engine.realised_pnl = 0.0
            trade = engine.place_order(
                symbol, "buy", quantity, entry, stop, take,
                reason=f"trend-following trigger, exit variant {variant.id}",
                source="phase4e-trend-following")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    counts["blocked_reasons"][re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade_exit(
                history, start, entry, stop, take, variant.horizon_days,
                TREND_STRATEGY, False)
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

    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    trades = len(trade_rows)
    return {
        "strategy": TREND_LABEL,
        "variant_id": variant.id,
        "variant": variant.label,
        "rules": variant.description,
        "stop_pct": variant.stop_pct,
        "take_pct": variant.take_pct,
        "horizon_days": variant.horizon_days,
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
        "per_symbol_trades": dict(counts["per_symbol"]),
        "trades": trade_rows,
    }


def run_trend_test() -> dict:
    """Run the trend-following entry on the three FRESH windows,
    using the cached histories only — no network fetch."""
    windows: list[dict] = []
    for label, start, end in FRESH_WINDOWS:
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
        histories, failed, summary = fetch_histories(provider, list(SCAN_UNIVERSE), days=180)
        strategies = {v.id: run_trend_variant(v, histories, window_start=start)
                      for v in FRESH_VARIANTS}
        windows.append({
            "label": label, "start": start, "end": end,
            "sample": "fresh — never used for selection",
            "history": summary, "failed_symbols": failed,
            "symbols_traded": [s for s in SCAN_UNIVERSE if s in histories],
            "strategies": {TREND_STRATEGY: strategies},
        })

    pooled = {}
    for vid in FRESH_VARIANT_IDS:
        results = [w["strategies"][TREND_STRATEGY][vid] for w in windows]
        trades = sum(r["trades_placed"] for r in results)
        wins = sum(r["wins"] for r in results)
        pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
        per_window = {w["label"]: r["total_pnl_usd"] for w, r in zip(windows, results)}
        positive = sum(1 for v in per_window.values() if v > 0)
        win_rate = round(wins / trades * 100, 1) if trades else 0.0
        pooled[vid] = {
            "variant_id": vid, "trades": trades, "wins": wins,
            "win_rate_pct": win_rate, "total_pnl_usd": pnl,
            "total_pnl_pct": round(pnl / (STARTING_CASH * len(windows)) * 100, 2),
            "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
            "per_window_pnl_usd": per_window,
            "per_window_win_rate_pct": {w["label"]: r["win_rate_pct"] for w, r in zip(windows, results)},
            "per_window_trades": {w["label"]: r["trades_placed"] for w, r in zip(windows, results)},
            "positive_windows": positive, "windows_total": len(windows),
            "holds_up": bool(pnl > 0 and win_rate > 40.0 and positive >= 2),
        }
    best_id = max(pooled, key=lambda vid: pooled[vid]["total_pnl_usd"])
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 4e Trend-Following Test Report",
        "method": ("Trend-following test on the three FRESH windows "
                   "(FRESH-1/2/3) from Phase 4d, using the cached real "
                   "Yahoo Finance histories only — no new fetch. Entry: "
                   "buy when close > SMA-20 and SMA-20 > SMA-50, history "
                   "up to the trade day only, no look-ahead. Exits: "
                   "baseline (3% stop / 4.5% target / 10 days), wide-5 "
                   "(5% / 7.5% / 10 days), wide-6 (6% / 9% / 10 days). "
                   "Every trade through the real PaperTradingEngine and "
                   "Risk Engine, balanced profile, $10,000 virtual cash, "
                   "long-only, 5-day walk-forward steps."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance) — cached copies in data/fresh-cache/",
        "entry_rule": ("Buy when close > 20-day SMA AND 20-day SMA > "
                       "50-day SMA, on history up to the trade day only. "
                       "No trade when either average is not yet defined."),
        "fresh_windows_definition": [
            {"label": label, "start": start, "end": end}
            for label, start, end in FRESH_WINDOWS
        ],
        "verdict_rule": ("A variant 'holds up' when its pooled "
                         "fresh-window paper P&L is > $0 AND its pooled "
                         "win rate is > 40% (the 1.5:1 break-even) AND it "
                         "is positive in at least 2 of the 3 fresh windows."),
        "variants": [
            {"id": v.id, "label": v.label, "stop_pct": v.stop_pct,
             "take_pct": v.take_pct, "horizon_days": v.horizon_days,
             "description": v.description}
            for v in FRESH_VARIANTS
        ],
        "fresh_windows": windows,
        "pooled_fresh": {TREND_STRATEGY: pooled},
        "verdict": {
            TREND_STRATEGY: {
                "best_variant_by_pooled_fresh_pnl": best_id,
                "best_pooled_fresh_pnl_usd": pooled[best_id]["total_pnl_usd"],
                "variants_holding_up": [vid for vid in FRESH_VARIANT_IDS
                                        if pooled[vid]["holds_up"]],
                "verdict_rule": ("holds up = pooled fresh P&L > $0 AND pooled win rate "
                                 "> 40% AND positive in at least 2 of 3 fresh windows"),
            }
        },
        "limits": ("None of FRESH-1/2/3 is a falling window like OOS-2 "
                   "(Feb-Aug 2025), so this run cannot prove "
                   "trend-following does better in a falling market — "
                   "that needs OOS-2, whose histories are not cached and "
                   "would need a fresh Yahoo fetch. Three windows are "
                   "still past prices: nothing here proves future "
                   "profits, and live paper trades over real days plus a "
                   "compliance/legal review are still required before "
                   "any real money is considered."),
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
        "This report tests an entry rule on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Entry: {report['entry_rule']}",
        f"- Data: {report['data_source']}",
        f"- Verdict rule: {report['verdict_rule']}",
        "",
        "## Pooled fresh-window verdict — 3 fresh windows",
        "",
        f"### {TREND_LABEL}",
        "",
        "| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Holds up |",
        "|---|---:|---:|---:|---:|:---:|:---:|",
    ]
    for vid, pooled in report["pooled_fresh"][TREND_STRATEGY].items():
        lines.append(
            f"| {vid} | {pooled['trades']} | {pooled['win_rate_pct']:.1f}% | "
            f"{_fmt_money(pooled['total_pnl_usd'])} | {_fmt_money(pooled['expectancy_usd'])} | "
            f"{pooled['positive_windows']}/{pooled['windows_total']} | "
            f"{'yes' if pooled['holds_up'] else 'NO'} |")
    verdict = report["verdict"][TREND_STRATEGY]
    lines += [
        "",
        "## Verdict",
        "",
        f"- Best variant by pooled fresh P&L: **{verdict['best_variant_by_pooled_fresh_pnl']}** "
        f"({_fmt_money(verdict['best_pooled_fresh_pnl_usd'])}).",
        f"- Variants holding up on fresh data: {verdict['variants_holding_up'] or 'none'}.",
        "",
        "## Limits — read this before trusting the result",
        "",
        report["limits"],
        "",
    ]
    for window in report["fresh_windows"]:
        lines += [
            f"## {window['label']} — {window['start']} → {window['end']} "
            f"({window['sample']})",
            "",
            f"- History: {len(window['history'])} symbols fetched from cache; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
            f"### {TREND_LABEL}",
            "",
            "| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|---:|",
        ]
        for vid, result in window["strategies"][TREND_STRATEGY].items():
            lines.append(
                f"| {vid} | {result['trades_placed']} | {result['win_rate_pct']:.1f}% | "
                f"{_fmt_money(result['total_pnl_usd'])} | {_fmt_money(result['expectancy_usd'])} | "
                f"{_fmt_money(result['avg_win_usd'])} | {_fmt_money(result['avg_loss_usd'])} | "
                f"{result['max_drawdown_pct']:.2f}% | {result['exits']} | {result['blocked_by_risk']} |")
        lines.append("")
        for vid, result in window["strategies"][TREND_STRATEGY].items():
            lines.append(f"- {vid} per symbol: {result['per_symbol_trades']}")
        lines.append("")
    lines += [
        "## Trades (every trade, in order) — wide-6",
        "",
    ]
    for window in report["fresh_windows"]:
        result = window["strategies"][TREND_STRATEGY].get("wide-6")
        if result is None or not result["trades"]:
            lines += [f"### {window['label']} — wide-6: no trades", ""]
            continue
        lines += [f"### {window['label']} — wide-6",
                  "",
                  "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
                  "|---:|---|---|---|---|---:|---:|"]
        for i, t in enumerate(result["trades"], 1):
            lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                         f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
        lines.append("")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase4e-trend-following-report") -> tuple[Path, Path]:
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
    report = run_trend_test()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for vid, pooled in report["pooled_fresh"][TREND_STRATEGY].items():
        print(f"trend / {vid}: {pooled['trades']} trades, "
              f"{pooled['win_rate_pct']}% win, P&L {_fmt_money(pooled['total_pnl_usd'])}, "
              f"expectancy {_fmt_money(pooled['expectancy_usd'])}, "
              f"positive {pooled['positive_windows']}/{pooled['windows_total']} windows "
              f"({'HOLDS UP' if pooled['holds_up'] else 'does NOT hold up'})")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
