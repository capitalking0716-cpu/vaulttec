"""Phase 3 — paper-trading validation.

A walk-forward validation run over deterministic offline sample data:

- For each symbol in the scan universe, step through its price history
  in 5-day windows. At each window, generate a signal from the history
  *up to that day only* (no looking ahead), and — if the signal is a
  long — place a real paper trade through ``PaperTradingEngine`` so
  every risk check runs for real.
- Each trade gets a stop-loss (entry -3%) and a take-profit
  (entry +4.5%), exactly 1.5:1 risk/reward. It exits at the first of:
  stop-loss hit, take-profit hit, or 10 days passing (time exit).
- Short signals are skipped and counted: the paper engine in this
  build is long-only. Neutral signals are skipped and counted.
  Skipped trades are reported, never silently dropped.
- Each window is a different simulated trading day, so the engine's
  realised-P&L tracker is reset per window — the daily loss limit is
  a per-day limit, and it is validated separately in the unit tests,
  where losses inside one day do block further trading.

Nothing here is invented: every number in the report comes from
trades the code actually placed and closed on the history it fetched.
Sample data is a random walk, not real market data — so a good result
on sample data proves the *machinery* works (signals, risk checks,
exits, accounting), not that the strategy will make money. The report
says so, in plain language.

Phase 4 Step 1 (real-market validation) reuses this exact machinery
with ``provider_name="yfinance"``: the same walk-forward, the same
40-trade target, the same 3% stop / 4.5% target / 10-day exit, the
same Risk Engine checks — but on delayed real market history instead
of the offline sample random walk. A symbol whose real history cannot
be fetched is recorded in ``failed_symbols`` and skipped; it is never
silently replaced with sample data and presented as real.
"""
from __future__ import annotations

import json
import math
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..config.settings import PAPER_STARTING_CASH, RISK_PROFILES
from ..db.models import UserProfile
from ..market.data import SCAN_UNIVERSE, SampleDataProvider, YFinanceProvider
from ..portfolio.manager import Portfolio
from ..paper_trading import PaperTradingEngine
from ..risk import RiskEngine
from .backtest import run_backtest_suite
from .signals import generate_signal

TARGET_TRADES = 40  # inside the brief's 30–50 paper-trade range
MIN_HISTORY_DAYS = 60  # need enough history for the indicators to work
WINDOW_STEP_DAYS = 5
EXIT_HORIZON_DAYS = 10
STOP_PCT = 0.03
TAKE_PCT = 0.045  # 4.5% reward vs 3% risk = 1.5:1, the profile minimum


def _exit_trade(history: pd.DataFrame, entry_index: int, entry: float,
                stop: float, take: float) -> tuple[float, str, int]:
    """Walk forward from the entry bar and find the exit.

    Returns (exit_price, exit_reason, days_held). Checks each day's
    low/high so a stop or target hit inside the day is caught, not
    just the close.
    """
    for offset in range(1, EXIT_HORIZON_DAYS + 1):
        idx = entry_index + offset
        if idx >= len(history):
            break
        bar = history.iloc[idx]
        if bar["low"] <= stop:
            return round(float(stop), 2), "stop-loss", offset
        if bar["high"] >= take:
            return round(float(take), 2), "take-profit", offset
    last = min(entry_index + EXIT_HORIZON_DAYS, len(history) - 1)
    return round(float(history.iloc[last]["close"]), 2), "time exit (10 days)", last - entry_index


def fetch_histories(provider, symbols: list[str], days: int = 180):
    """Fetch each symbol's history from ``provider``.

    Returns (histories, failed_symbols, history_summary). A symbol
    whose history cannot be fetched is recorded in ``failed_symbols``
    and skipped — it is never silently replaced with sample data.
    """
    histories: dict[str, pd.DataFrame] = {}
    failed: dict[str, str] = {}
    summary: dict[str, dict] = {}
    for symbol in symbols:
        try:
            history = provider.get_history(symbol, days=days)
        except Exception as exc:  # noqa: BLE001 — record and move on
            failed[symbol] = f"{type(exc).__name__}: {exc}"
            continue
        if history is None or history.empty or "close" not in history.columns:
            failed[symbol] = "empty history returned"
            continue
        histories[symbol] = history.reset_index(drop=True)
        summary[symbol] = {
            "rows": len(history),
            "first_date": str(history["date"].min())[:10] if "date" in history.columns else None,
            "last_date": str(history["date"].max())[:10] if "date" in history.columns else None,
            "last_close": round(float(history["close"].iloc[-1]), 2),
        }
        if isinstance(provider, YFinanceProvider):
            time.sleep(0.5)  # be polite to the free data feed
    return histories, failed, summary


def run_backtests(provider_name: str = "yfinance",
                  symbols: list[str] | None = None,
                  days: int = 180) -> dict:
    """Run the 4-strategy backtest suite on each symbol's full history.

    Returns per-symbol suite results plus a per-strategy aggregate
    (mean return / win rate / drawdown across symbols). Historical
    only — never a promise of future results.
    """
    symbols = symbols or list(SCAN_UNIVERSE)
    provider = YFinanceProvider() if provider_name == "yfinance" else SampleDataProvider()
    histories, failed, _ = fetch_histories(provider, symbols, days)
    per_symbol = {s: run_backtest_suite(h) for s, h in histories.items()}
    aggregate: dict[str, dict] = {}
    for name in ("SMA crossover", "MACD crossover", "RSI mean-reversion", "Bollinger mean-reversion"):
        traded = [r for suite in per_symbol.values() for r in suite["strategies"]
                  if r["strategy"] == name and r["trades"] > 0]
        aggregate[name] = {
            "symbols_with_trades": len(traded),
            "mean_total_return_pct": round(sum(r["total_return_pct"] for r in traded) / len(traded), 2) if traded else 0.0,
            "mean_win_rate_pct": round(sum(r["win_rate_pct"] for r in traded) / len(traded), 1) if traded else 0.0,
            "mean_max_drawdown_pct": round(sum(r["max_drawdown_pct"] for r in traded) / len(traded), 2) if traded else 0.0,
            "total_trades": sum(r["trades"] for r in traded),
        }
    return {"per_symbol": per_symbol, "failed_symbols": failed, "aggregate": aggregate}


def run_validation(symbols: list[str] | None = None,
                   target_trades: int = TARGET_TRADES,
                   starting_cash: float = PAPER_STARTING_CASH,
                   risk_profile: str = "balanced",
                   provider_name: str = "sample",
                   days: int = 180,
                   provider=None) -> dict:
    """Run the walk-forward validation. Returns the full report dict.

    ``provider_name`` is "sample" (Phase 3, deterministic offline
    random walk) or "yfinance" (Phase 4 Step 1, delayed real market
    data). ``provider`` may be passed directly (used by tests to
    inject a stub); otherwise it is built from ``provider_name``.
    """
    symbols = symbols or list(SCAN_UNIVERSE)
    attempted = list(symbols)
    if provider is None:
        provider = YFinanceProvider() if provider_name == "yfinance" else SampleDataProvider()
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

    histories, failed_symbols, history_summary = fetch_histories(provider, symbols, days)
    symbols = [s for s in symbols if s in histories]
    counts = Counter()
    trade_rows: list[dict] = []
    blocked_reasons = Counter()
    per_symbol = Counter()

    # Histories can differ in length (stocks trade weekdays, crypto
    # trades every day), so windows run to the longest history and
    # each symbol is skipped once its own history runs out.
    max_len = max((len(h) for h in histories.values()), default=0)
    windows = range(MIN_HISTORY_DAYS, max_len - EXIT_HORIZON_DAYS, WINDOW_STEP_DAYS)
    placed = 0
    for start in windows:
        if placed >= target_trades:
            break
        for symbol in symbols:
            if placed >= target_trades:
                break
            history = histories[symbol]
            if start >= len(history) - EXIT_HORIZON_DAYS:
                continue
            counts["windows_checked"] += 1
            window_history = history.iloc[: start + 1].reset_index(drop=True)
            signal = generate_signal(symbol, window_history)
            if signal.direction == "neutral":
                counts["skipped_neutral"] += 1
                continue
            if signal.direction != "long":
                counts["skipped_short"] += 1  # long-only paper engine in this build
                continue
            if symbol in portfolio.holdings:
                counts["skipped_already_in_position"] += 1
                continue
            entry = float(history.iloc[start]["close"])
            stop = round(entry * (1 - STOP_PCT), 2)
            # Build the target from the *rounded* stop and round it UP
            # to the cent, so the trade is always at least 1.5:1 after
            # cent-rounding: rounding the target down can shave the
            # ratio to 1.49:1 and the Risk Engine rightly blocks it.
            take = math.ceil((entry + 1.5 * (entry - stop)) * 100) / 100
            # Floor (never round up) so the position cost cannot creep
            # above the profile's max position size by rounding.
            raw_qty = risk.position_size(portfolio.value({symbol: entry}), entry)
            quantity = math.floor(raw_qty * 10000) / 10000
            if quantity <= 0:
                counts["skipped_too_small"] += 1
                continue
            # Each window is a different simulated day: reset the
            # per-day realised-P&L tracker (see module docstring).
            engine.realised_pnl = 0.0
            trade = engine.place_order(
                symbol, "buy", quantity, entry, stop, take,
                reason=signal.evidence, source="validation")
            if trade is None:
                counts["blocked_by_risk"] += 1
                for reason in engine.blocked[-1]["reasons"]:
                    # Normalise dollar amounts so the report groups
                    # identical reasons instead of one entry per amount.
                    blocked_reasons[re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                continue
            exit_price, exit_reason, days_held = _exit_trade(
                history, start, entry, stop, take)
            pnl = engine.close_position(symbol, exit_price, exit_reason)
            pnl = 0.0 if pnl is None else round(pnl, 2)
            trade_rows.append({
                "symbol": symbol, "entry": entry, "exit": exit_price,
                "quantity": quantity, "stop_loss": stop, "take_profit": take,
                "exit_reason": exit_reason, "days_held": days_held,
                "pnl_usd": pnl, "pnl_pct": round(pnl / (entry * quantity) * 100, 2)
                if entry * quantity else 0.0,
                "confidence": round(signal.confidence, 2),
            })
            per_symbol[symbol] += 1
            placed += 1

    wins = [t for t in trade_rows if t["pnl_usd"] > 0]
    losses = [t for t in trade_rows if t["pnl_usd"] <= 0]
    total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
    is_real = provider_name == "yfinance"
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": ("VaultTec — Phase 4 Real-Market Validation Report" if is_real
                  else "VaultTec — Phase 3 Paper-Trading Validation Report"),
        "method": (f"Walk-forward over {'delayed real market history from yfinance' if is_real else 'deterministic offline sample history'} "
                   f"({days} days requested per symbol, 5-day windows, 10-day exit horizon). "
                   "Signals used history up to the trade day only — no look-ahead."),
        "data_source": ("yfinance (delayed real market data, free — Yahoo Finance)"
                        if is_real else
                        "sample (offline demo data — a random walk, NOT real market data)"),
        "provider": provider_name,
        "history_days_requested": days,
        "symbols_attempted": attempted,
        "symbols_traded": symbols,
        "failed_symbols": failed_symbols,
        "history": history_summary,
        "risk_profile": risk_profile,
        "starting_cash_usd": starting_cash,
        "target_trades": target_trades,
        "trades_placed": len(trade_rows),
        "target_met": len(trade_rows) >= 30,
        "windows_checked": counts["windows_checked"],
        "skipped_neutral": counts["skipped_neutral"],
        "skipped_short": counts["skipped_short"],
        "skipped_already_in_position": counts["skipped_already_in_position"],
        "skipped_too_small": counts["skipped_too_small"],
        "blocked_by_risk": counts["blocked_by_risk"],
        "blocked_reasons": dict(blocked_reasons),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(len(wins) / len(trade_rows) * 100, 1) if trade_rows else 0.0,
        "total_pnl_usd": total_pnl,
        "total_pnl_pct": round(total_pnl / starting_cash * 100, 2),
        "avg_win_usd": round(sum(t["pnl_usd"] for t in wins) / len(wins), 2) if wins else 0.0,
        "avg_loss_usd": round(sum(t["pnl_usd"] for t in losses) / len(losses), 2) if losses else 0.0,
        "exits": dict(Counter(t["exit_reason"] for t in trade_rows)),
        "per_symbol_trades": dict(per_symbol),
        "trades": trade_rows,
        "note": (("Validation on delayed real market history — a genuine "
                  "out-of-sample test of the signal + risk machinery on "
                  "prices that actually happened, not a random walk. It "
                  "still does not prove future profits: one 180-day window, "
                  "one signal method, long-only, and past performance does "
                  "not guarantee future results. A real verdict also needs "
                  "live paper trades over real days, and a compliance/legal "
                  "review, before any real money is considered.")
                 if is_real else
                 ("Validation of the machinery on sample data, not proof of "
                  "future profits. Sample history is a random walk, so the "
                  "win rate here says more about the sample data than about "
                  "the strategy. A real verdict needs the same run on real "
                  "market history and the 30–50 live paper trades in Phase 3 "
                  "of the brief. Past performance does not guarantee future results.")),
    }


def render_markdown(report: dict) -> str:
    """Human-readable version of the validation report."""
    lines = [
        f"# {report.get('title', 'VaultTec — Phase 3 Paper-Trading Validation Report')}",
        "",
        f"Generated: {report['generated_at']} (UTC)",
        "",
        "> Risk disclosure: trading involves substantial risk of loss. "
        "This report proves the paper-trading machinery works — it does "
        "not promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        f"- History: {len(report.get('history', {}))} symbols fetched "
        f"({report.get('history_days_requested')} days requested); "
        f"failed to fetch: {report.get('failed_symbols') or 'none'}",
        f"- Risk profile: {report['risk_profile']} — starting virtual cash ${report['starting_cash_usd']:,.2f}",
        "- Every trade: stop-loss at entry -3%, take-profit at entry +4.5% (1.5:1 risk/reward), "
        "exit at stop, target, or after 10 days.",
        "- Short and neutral signals were skipped and counted, not traded — the paper engine in this build is long-only.",
        "",
        "## Results",
        "",
        f"- **Trades placed: {report['trades_placed']}** (target {report['target_trades']}, brief asks for 30–50) — "
        f"target met: {'yes' if report['target_met'] else 'NO'}",
        f"- Wins: {report['wins']} — losses: {report['losses']} — win rate: **{report['win_rate_pct']}%**",
        f"- Total paper P&L: **${report['total_pnl_usd']:,.2f} ({report['total_pnl_pct']:+.2f}% of starting cash)**",
        f"- Average win: ${report['avg_win_usd']:,.2f} — average loss: ${report['avg_loss_usd']:,.2f}",
        f"- Exits: {report['exits']}",
        f"- Windows checked: {report['windows_checked']} — skipped (neutral): {report['skipped_neutral']}, "
        f"skipped (short): {report['skipped_short']}, skipped (already in position): {report['skipped_already_in_position']}",
        f"- Blocked by the Risk Engine: {report['blocked_by_risk']} {report['blocked_reasons']}",
        f"- Trades per symbol: {report['per_symbol_trades']}",
        f"- History per symbol (rows, first → last date, last close): "
        + "; ".join(f"{s}: {h['rows']} rows, {h['first_date']} → {h['last_date']}, ${h['last_close']:,.2f}"
                    for s, h in report.get('history', {}).items()),
        "",
    ]
    if "backtests" in report:
        lines += [
            "## Backtest suite (same history, all four strategies)",
            "",
            "Each strategy ran on every symbol's full fetched history. "
            "Historical only — past performance does not guarantee future results.",
            "",
        ]
        for name, agg in report["backtests"].get("aggregate", {}).items():
            lines.append(
                f"- {name}: mean total return {agg['mean_total_return_pct']:+.2f}%, "
                f"mean win rate {agg['mean_win_rate_pct']:.1f}%, "
                f"mean max drawdown {agg['mean_max_drawdown_pct']:.2f}%, "
                f"symbols with trades {agg['symbols_with_trades']}, "
                f"total trades {agg['total_trades']}")
        lines += ["", "Per-symbol backtest results are in the JSON report.", ""]
    lines += [
        "## What this does and does not prove",
        "",
        report["note"],
        "",
        "## Trades (every trade, in order)",
        "",
        "| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |",
        "|---:|---|---|---|---|---:|---:|",
    ]
    for i, t in enumerate(report["trades"], 1):
        lines.append(f"| {i} | {t['symbol']} | ${t['entry']:,.2f} | ${t['exit']:,.2f} | "
                     f"{t['exit_reason']} | {t['days_held']} | {t['pnl_usd']:+,.2f} |")
    return "\n".join(lines) + "\n"


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase3-paper-validation-report") -> tuple[Path, Path]:
    """Write the report as JSON + Markdown. Returns both paths."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return json_path, md_path


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run the walk-forward paper-trading validation.")
    parser.add_argument("--provider", default="sample", choices=["sample", "yfinance"],
                        help="sample = Phase 3 offline random walk; yfinance = Phase 4 Step 1 real market data")
    parser.add_argument("--days", type=int, default=180, help="history days requested per symbol")
    parser.add_argument("--target", type=int, default=TARGET_TRADES)
    parser.add_argument("--stem", default="phase3-paper-validation-report",
                        help="report filename stem (no extension)")
    parser.add_argument("--backtests", action="store_true",
                        help="also run the 4-strategy backtest suite on each symbol's full history")
    args = parser.parse_args()

    base = Path(__file__).resolve().parents[2]
    report = run_validation(target_trades=args.target, provider_name=args.provider, days=args.days)
    if args.backtests:
        report["backtests"] = run_backtests(args.provider, days=args.days)
    json_path, md_path = save_report(report, base / "validation", stem=args.stem)
    print(f"Provider: {args.provider} — data: {report['data_source']}")
    print(f"Symbols fetched: {len(report['history'])} — failed: {report['failed_symbols'] or 'none'}")
    print(f"Trades placed: {report['trades_placed']} (target {report['target_trades']})")
    print(f"Wins: {report['wins']} / Losses: {report['losses']} — win rate {report['win_rate_pct']}%")
    print(f"Total paper P&L: ${report['total_pnl_usd']:,.2f} ({report['total_pnl_pct']:+.2f}%)")
    print(f"Blocked by risk: {report['blocked_by_risk']}")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0 if report["target_met"] else 1)
