"""8-hour backtest of the VaultTec intraday paper system — PAPER ONLY.

Runs the exact intraday runner (``vaulttec/intraday_paper_trading.py``)
over the most recent 8 completed hourly market bars, all 12 symbols,
on a **$100 virtual pot** — the same size as Ava's $100 pot, at
Neko's request (the intraday live pot is $10,000; this test is the
$100 version).

Method — faithful, not a reimplementation
-----------------------------------------
- Prices are real yfinance hourly bars (60d), fetched once per
  symbol. A failed fetch is recorded and that symbol is skipped —
  never invented, never replaced with sample data.
- The runner itself is driven, bar by bar, in order, with the run
  clock set just past each bar's completion — the same "completed
  bars only, no look-ahead" rule the live runner uses.
- The runner's warm-up on its first call processes only the latest
  completed bar, so the checkpoints are chosen so the first call's
  latest completed bar IS the first window bar for every symbol.
  The script asserts that; if it ever fails it aborts instead of
  silently skipping bars.
- Entry/exit triggers, the Risk Engine, position sizing (10% of
  pot, fractional shares floored to 4 decimals), the 6% stop /
  9% target and the 10-session time exit are the runner's own code
  — nothing is reimplemented here.
- The test pot is seeded by writing a fresh state with
  ``starting_cash_usd`` / ``cash_usd`` = $100 into a scratch
  directory under /tmp. Live state is never read or written.
- This file only ADDS code; it modifies no existing file.

$100 scaling (checked, not assumed)
------------------------------------
- ``position_size`` is pure percentage: (pot * 10%) / price, so a
  $10 position on a $100 pot. ``Portfolio.buy`` takes any fractional
  quantity; ``check_order`` has no minimum quantity or dollar
  floor — only percentage limits (concentration, exposure, daily
  loss) which scale identically.
- The only absolute floor is the runner's own 4-decimal quantity
  floor. At $10 a trade nothing rounds to zero, not even BTC
  (~$95,000 -> 0.0001 shares, cost ~$9.50). Expect dollars in
  cents, not dollars: a 9% win on a $10 position is ~$0.90.

Honest limits
-------------
- 8 hours is a very short window. The 6% stop / 9% target almost
  never triggers inside one session, and the 10-session time exit
  cannot fire inside an 8-bar window spanning 2 sessions — so
  expect few or zero closed trades. The number is a data point,
  not proof of anything.
- Wide-6 was validated on daily bars, not hourly. Hourly wide-6
  is an unvalidated experiment.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from vaulttec.intraday_paper_trading import (
    BAR,
    NY_TZ,
    _completed_hourly_bars,
    compute_summary,
    fresh_state,
    load_state,
    run_intraday,
    save_state,
)
from vaulttec.intraday_paper_trading import LiveIntradayProvider
from vaulttec.market.data import SCAN_UNIVERSE

DEFAULT_CASH = 100.0
DEFAULT_BARS = 8
CHECKPOINT_SLACK = timedelta(minutes=5)


class CachedProvider:
    """Holds history fetched once per symbol; the runner is driven
    bar by bar, and refetching 60d of hourly bars on every call
    would burn Yahoo's rate limit for nothing."""

    def __init__(self, frames: dict[str, pd.DataFrame]):
        self._frames = frames

    def get_history(self, symbol: str, days: int | None = None) -> pd.DataFrame:
        return self._frames[symbol].copy()


def window_bars(history: pd.DataFrame, now: datetime,
                n: int = DEFAULT_BARS) -> pd.DataFrame:
    """The most recent ``n`` completed in-session hourly bars, in
    order — the runner's own definition of "completed" is reused
    so the window means exactly what the live runner means."""
    completed = _completed_hourly_bars(history, now)
    return completed.tail(n).reset_index(drop=True)


def build_checkpoints(window: dict[str, pd.DataFrame]) -> list[datetime]:
    """Run times that drive the runner through the window, bar by
    bar, in order.

    The runner's first call warm-up processes only the latest
    completed bar, so the first checkpoint is just past the
    JOINT first completion (the latest of every symbol's first
    window bar completing). At that moment, every symbol's latest
    completed bar is its first window bar — nothing is skipped.
    Later checkpoints sit just past each subsequent bar's
    completion. Every checkpoint is a naive New York datetime,
    which the runner treats as New York time."""
    first_completion = {
        symbol: pd.Timestamp(bars["date"].iloc[0]).to_pydatetime() + BAR
        for symbol, bars in window.items()
    }
    joint_first = max(first_completion.values())
    first_cp = joint_first + CHECKPOINT_SLACK
    all_cps = {
        pd.Timestamp(d).to_pydatetime() + BAR + CHECKPOINT_SLACK
        for bars in window.values() for d in bars["date"]
    }
    return sorted(cp for cp in all_cps if cp >= first_cp)


def verify_first_checkpoint(frames: dict[str, pd.DataFrame],
                            window: dict[str, pd.DataFrame],
                            first_cp: datetime) -> None:
    """At the first checkpoint, every symbol's latest completed
    bar must be its first window bar. Fail loudly if not — a
    silent skip would fake the window."""
    for symbol, bars in window.items():
        latest = _completed_hourly_bars(frames[symbol], first_cp)
        if latest.empty:
            raise ValueError(f"{symbol}: no completed bar at first checkpoint")
        latest_bar = pd.Timestamp(latest["date"].iloc[-1]).to_pydatetime()
        first_bar = pd.Timestamp(bars["date"].iloc[0]).to_pydatetime()
        if latest_bar != first_bar:
            raise ValueError(
                f"{symbol}: first checkpoint latest bar {latest_bar} != "
                f"first window bar {first_bar}; window would be skipped")


def run_backtest(symbols: list[str] | None = None,
                 cash: float = DEFAULT_CASH,
                 n_bars: int = DEFAULT_BARS,
                 now: datetime | None = None,
                 provider=None,
                 scratch_dir: str | Path | None = None) -> dict:
    """Drive the real intraday runner over the most recent
    ``n_bars`` completed hourly bars on a ``cash`` pot.

    Returns a result dict with the window, per-symbol and total
    numbers, and the scratch state dir. State lives only in the
    scratch dir — live state is never touched."""
    now_aware = now or datetime.now(NY_TZ)
    now_aware = now_aware.astimezone(NY_TZ)
    now_naive = now_aware.replace(tzinfo=None)
    symbols = symbols or list(SCAN_UNIVERSE)
    if provider is None:
        provider = LiveIntradayProvider(now_aware)

    frames: dict[str, pd.DataFrame] = {}
    failed: dict[str, str] = {}
    for symbol in symbols:
        try:
            frames[symbol] = provider.get_history(symbol)
        except Exception as exc:  # noqa: BLE001 — record, never invent
            failed[symbol] = f"{type(exc).__name__}: {exc}"
    available = [s for s in symbols if s in frames]
    if not available:
        return {"status": "fetch_failed", "paper_only": True,
                "strategy": "wide-6", "starting_cash_usd": cash,
                "n_bars": n_bars, "now": now_naive.isoformat(timespec="minutes"),
                "symbols": symbols, "failed_symbols": failed, "window": {},
                "checkpoints": [], "scratch_dir": None, "processed_ok": {},
                "trades_opened": 0, "trades_closed": 0,
                "wins": 0, "losses": 0, "win_rate_pct": 0.0,
                "total_pnl_usd": 0.0, "total_pnl_pct": 0.0,
                "avg_win_usd": 0.0, "avg_loss_usd": 0.0,
                "expectancy_usd": 0.0, "exits": {},
                "cash_usd": cash, "holdings_value_usd": 0.0,
                "portfolio_value_usd": cash,
                "unrealised_pnl_usd": 0.0, "open_positions": [],
                "closed_trades": [], "per_symbol": {},
                "blocked_count": 0, "fetch_failures": failed}

    window = {s: window_bars(frames[s], now_naive, n_bars) for s in available}
    window = {s: w for s, w in window.items() if len(w) > 0}
    checkpoints = build_checkpoints(window)
    verify_first_checkpoint(frames, window, checkpoints[0])

    scratch = Path(scratch_dir) if scratch_dir else Path(
        tempfile.mkdtemp(prefix="vaulttec-backtest-8h-"))
    scratch.mkdir(parents=True, exist_ok=True)
    seeded = fresh_state(started_on=now_naive.date().isoformat())
    seeded["starting_cash_usd"] = cash
    seeded["cash_usd"] = cash
    save_state(scratch, seeded)

    cached = CachedProvider(frames)
    run_summaries = []
    for cp in checkpoints:
        run_summaries.append(run_intraday(
            run_time=cp, provider=cached, live_dir=scratch,
            symbols=available))

    final = load_state(scratch)
    summary = compute_summary(final)
    # compute_summary's pct uses the module's $10,000 constant; use
    # this pot's cash instead.
    total_pnl = summary["total_pnl_usd"]
    summary["total_pnl_pct"] = round(total_pnl / cash * 100, 2) if cash else 0.0

    # Verify every symbol's last processed bar is its last window bar.
    processed_ok = {}
    for symbol, bars in window.items():
        last_window = pd.Timestamp(bars["date"].iloc[-1]).isoformat()
        processed_ok[symbol] = (
            final["last_processed_bar"].get(symbol) == last_window)

    open_positions = []
    for p in final.get("open_positions", []):
        last = final.get("last_close", {}).get(p["symbol"], p["entry_price"])
        open_positions.append({
            "symbol": p["symbol"], "strategy": p["strategy"],
            "entry_date": p["entry_date"], "entry_price": p["entry_price"],
            "quantity": p["quantity"], "stop_loss": p["stop_loss"],
            "take_profit": p["take_profit"],
            "bars_held": p.get("bars_held", 0),
            "sessions_held": p.get("sessions_held", 0),
            "last_close": last,
            "unrealised_pnl_usd": round(
                (last - p["entry_price"]) * p["quantity"], 2),
        })

    return {
        "status": "ok",
        "paper_only": True,
        "strategy": "wide-6",
        "starting_cash_usd": cash,
        "n_bars": n_bars,
        "now": now_naive.isoformat(timespec="minutes"),
        "symbols": available,
        "failed_symbols": failed,
        "window": {s: [pd.Timestamp(d).isoformat() for d in w["date"]]
                   for s, w in window.items()},
        "checkpoints": [cp.isoformat(timespec="minutes") for cp in checkpoints],
        "scratch_dir": str(scratch),
        "processed_ok": processed_ok,
        "trades_opened": sum(r["trades_opened"] for r in run_summaries),
        "trades_closed": summary["closed_trades"],
        "wins": summary["wins"],
        "losses": summary["losses"],
        "win_rate_pct": summary["win_rate_pct"],
        "total_pnl_usd": total_pnl,
        "total_pnl_pct": summary["total_pnl_pct"],
        "avg_win_usd": summary["avg_win_usd"],
        "avg_loss_usd": summary["avg_loss_usd"],
        "expectancy_usd": summary["expectancy_usd"],
        "exits": summary["exits"],
        "cash_usd": summary["cash_usd"],
        "holdings_value_usd": summary["holdings_value_usd"],
        "portfolio_value_usd": summary["portfolio_value_usd"],
        "unrealised_pnl_usd": round(
            sum(p["unrealised_pnl_usd"] for p in open_positions), 2),
        "open_positions": open_positions,
        "closed_trades": final.get("closed_trades", []),
        "per_symbol": summary["per_symbol"],
        "blocked_count": summary["blocked_count"],
        "fetch_failures": summary["fetch_failures"],
    }


def render_report(result: dict) -> str:
    """The full backtest report, in plain language."""
    lines = [
        "# VaultTec — Intraday 8-Hour Backtest (paper only, $100 pot)",
        "",
        "> **PAPER ONLY — virtual money, no live brokerage, no real "
        "money. Trading involves substantial risk of loss. This "
        "backtest does not promise profits. Past performance does "
        "not guarantee future results.**",
        "",
        "## What was tested",
        "",
        f"- System: intraday paper trading, wide-6 mean-reversion "
        f"(RSI + Bollinger, 6% stop / 9% target, 1.5:1, 10-session "
        f"time exit, long-only, balanced profile).",
        f"- Window: the most recent **{result['n_bars']} completed "
        f"hourly market bars** per symbol, as of "
        f"{result['now']} (America/New_York).",
        f"- Symbols: {', '.join(result['symbols'])}",
        f"- Virtual pot: **${result['starting_cash_usd']:,.2f}** — "
        f"same size as Ava's $100 pot, at Neko's request. Position "
        f"size is 10% of the pot per trade (~$10), fractional shares "
        f"the way Alpaca paper does.",
        "",
    ]
    if result["failed_symbols"]:
        lines += [
            "## Fetch failures (honest)",
            "",
        ]
        for symbol, error in result["failed_symbols"].items():
            lines.append(f"- {symbol}: {error}")
        lines.append("")
    lines += [
        "## The 8 bars tested",
        "",
    ]
    for symbol, bars in sorted(result["window"].items()):
        lines.append(f"- {symbol}: {bars[0]} → {bars[-1]} "
                     f"({len(bars)} bars)")
    lines += [
        "",
        "## Result — total",
        "",
        f"- Trades opened: **{result['trades_opened']}**",
        f"- Trades closed: **{result['trades_closed']}** "
        f"— wins: **{result['wins']}** — losses: "
        f"**{result['losses']}**",
        f"- Total realised profit: **${result['total_pnl_usd']:+,.2f} "
        f"({result['total_pnl_pct']:+.2f}% of the $100 pot)**",
        f"- Cash left: **${result['cash_usd']:,.2f}** — portfolio "
        f"value (cash + holdings at last close): "
        f"**${result['portfolio_value_usd']:,.2f}**",
        f"- Unrealised P&L on open positions: "
        f"**${result['unrealised_pnl_usd']:+,.2f}** (paper value, "
        f"not profit)",
        f"- Win rate: {result['win_rate_pct']}% — average win: "
        f"${result['avg_win_usd']:,.2f} — average loss: "
        f"${result['avg_loss_usd']:,.2f} — expectancy: "
        f"${result['expectancy_usd']:+,.2f} per trade",
        f"- Blocked by risk: {result['blocked_count']}",
        "",
    ]
    lines += [
        "## Per-symbol (closed trades)",
        "",
    ]
    if result["per_symbol"]:
        for symbol, r in sorted(result["per_symbol"].items()):
            lines.append(f"- {symbol}: {r['trades']} trades, "
                         f"{r['wins']} wins, "
                         f"P&L ${r['pnl_usd']:+,.2f}")
    else:
        lines.append("- No trades closed in these 8 hours, so there "
                     "is no per-symbol P&L yet.")
    lines.append("")
    if result["closed_trades"]:
        lines += [
            "## Trades that closed",
            "",
            "| Symbol | Entry | Exit | Reason | P&L ($) |",
            "|---|---|---|---|---:|",
        ]
        for t in result["closed_trades"]:
            lines.append(
                f"| {t['symbol']} | ${t['entry_price']:,.2f} "
                f"({t['entry_date']}) | ${t['exit_price']:,.2f} "
                f"({t['exit_date']}) | {t['exit_reason']} | "
                f"{t['pnl_usd']:+,.2f} |")
        lines.append("")
    if result["open_positions"]:
        lines += [
            "## Still open at the end of the 8 hours — not wins or losses",
            "",
            "| Symbol | Entry | Qty | Stop | Target | Last close | Unrealised ($) |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for p in result["open_positions"]:
            lines.append(
                f"| {p['symbol']} | ${p['entry_price']:,.2f} "
                f"({p['entry_date']}) | {p['quantity']} | "
                f"${p['stop_loss']:,.2f} | ${p['take_profit']:,.2f} | "
                f"${p['last_close']:,.2f} | "
                f"{p['unrealised_pnl_usd']:+,.2f} |")
        lines.append("")
    else:
        lines += ["No positions open at the end of the 8 hours.", ""]
    lines += [
        "## What this does and does not prove",
        "",
        "- 8 hours is a very short window. A 6% stop / 9% target "
        "almost never triggers inside one session, and the "
        "10-session time exit cannot fire inside 8 bars spanning "
        "2 sessions — so few or zero closed trades is the expected "
        "outcome, not a failure of the system.",
        "- The amounts are small by design: on a $100 pot a 9% win "
        "on a ~$10 position is about $0.90. Cents, not dollars.",
        "- Wide-6 was validated on daily bars, not hourly ones. "
        "Hourly wide-6 is an unvalidated experiment — this number "
        "is a data point, not proof of anything.",
        "- A compliance/legal review is still required before any "
        "real money is considered. Past performance does not "
        "guarantee future results.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="VaultTec intraday 8-hour backtest — paper only, "
                    "$100 virtual pot. No broker, no real money.")
    parser.add_argument("--cash", type=float, default=DEFAULT_CASH)
    parser.add_argument("--bars", type=int, default=DEFAULT_BARS)
    parser.add_argument("--out", default=None,
                        help="report path (default: vaulttec/validation/"
                             "intraday-8h-backtest-YYYY-MM-DD.md)")
    parser.add_argument("--scratch-dir", default=None)
    args = parser.parse_args(argv)

    result = run_backtest(cash=args.cash, n_bars=args.bars,
                          scratch_dir=args.scratch_dir)
    if args.out:
        out = Path(args.out)
    else:
        out = (Path(__file__).resolve().parents[1] / "validation"
               / f"intraday-8h-backtest-{datetime.now(NY_TZ).date().isoformat()}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(result), encoding="utf-8")

    print(f"PAPER ONLY — 8h backtest, ${args.cash:,.0f} pot: "
          f"{result['status']}")
    print(f"Window: {result['n_bars']} bars per symbol, "
          f"as of {result['now']} ET")
    print(f"Trades opened: {result['trades_opened']} — closed: "
          f"{result['trades_closed']} — wins: {result['wins']} — "
          f"losses: {result['losses']}")
    print(f"Total realised profit: ${result['total_pnl_usd']:+,.2f} "
          f"— cash left: ${result['cash_usd']:,.2f} — unrealised: "
          f"${result['unrealised_pnl_usd']:+,.2f}")
    if result["failed_symbols"]:
        print(f"Fetch failures: {list(result['failed_symbols'])}")
    print(f"Report: {out}")
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
