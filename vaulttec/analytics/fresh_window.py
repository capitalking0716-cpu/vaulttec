"""Phase 4d — fresh-window test: did the wider stop survive, or was
Phase 4c selection luck?

Phase 4c tested seven exit variants on the same three out-of-sample
windows (OOS-1/2/3) plus the Phase 4 window. The wider stop won:
RSI wide-5 (5% stop / 7.5% target) 59.7% win, +$1,517.23 pooled;
RSI wide-6 (6% / 9%) 59.7% win, +$1,441.19, the only RSI variant
surviving the falling OOS-2 window; Bollinger wide-5 65.0% win,
+$888.92 and wide-6 65.0% win, +$880.48, both surviving OOS-2.
The downtrend filter failed / threw away winners.

But seven variants were tested on the same three windows, so the
winner is partly the best by chance (multiple comparisons). This
module tests ONLY the two winning variants (wide-5 and wide-6),
for BOTH RSI and Bollinger mean-reversion, plus the baseline
(3% / 4.5%) as a control, on FRESH 180-calendar-day windows that
were never used for selection — not OOS-1/2/3, not the Phase 4
window:

- FRESH-1: 2024-03-04 -> 2024-09-01
- FRESH-2: 2023-09-06 -> 2024-03-04
- FRESH-3: 2023-03-10 -> 2023-09-06

All three end before OOS-3 starts (2024-09-01) and none overlap
each other or any earlier window. Same method as Phase 4c:
delayed real yfinance history, 70 days of warm-up so indicators
are defined on day one, 12 symbols, 5-day walk-forward steps,
signals from history up to the trade day only (no look-ahead),
every trade through the real PaperTradingEngine and Risk Engine,
balanced profile, $10,000 virtual cash, long-only, 10-day exit.
Every variant keeps a stop-loss; the stop is never removed.

Verdict rule — fixed before the run, so the report cannot move
the goalposts: a variant "holds up" on fresh data when its pooled
fresh-window paper P&L is > $0 AND its pooled win rate is > 40%
(the 1.5:1 break-even) AND it is positive in at least 2 of the 3
fresh windows. Fresh results are pooled ONLY across the fresh
windows — never pooled with the selection windows (OOS-1/2/3 or
Phase 4), which are not re-run here at all.

Nothing here is live: paper only, no broker, no real money, no
leverage, no options. Past performance does not guarantee future
results, and a good result here still needs live paper trades
over real days plus a compliance/legal review before real money
is ever considered.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from .exit_test import (
    STARTING_CASH,
    WARMUP_DAYS,
    run_window_exits,
    variant_by_id,
)
from .mean_reversion import DatedYFinanceProvider, OOS_WINDOWS, STRATEGIES, strategy_label

# Fresh windows: (label, start, end-exclusive). All end on or
# before OOS-3 starts (2024-09-01); none overlaps OOS-1/2/3 or
# the Phase 4 window (2026-02-23 -> 2026-11-06), or each other.
FRESH_WINDOWS: list[tuple[str, str, str]] = [
    ("FRESH-1", "2024-03-04", "2024-09-01"),
    ("FRESH-2", "2023-09-06", "2024-03-04"),
    ("FRESH-3", "2023-03-10", "2023-09-06"),
]

# Only the two Phase 4c winners, plus the baseline as a control.
FRESH_VARIANT_IDS = ("baseline", "wide-5", "wide-6")
FRESH_VARIANTS = tuple(variant_by_id(vid) for vid in FRESH_VARIANT_IDS)

# Verdict rule, fixed before the run (see module docstring).
MIN_POSITIVE_WINDOWS = 2
BREAK_EVEN_WIN_RATE_PCT = 40.0

# Disk cache for fetched histories. Each yfinance fetch needs a
# foreground permission approval and takes minutes, and a long run
# can be interrupted (the first Phase 4d run was killed mid-way
# through FRESH-2 with all fetched data still only in memory).
# Caching each symbol's history to data/fresh-cache/ as soon as it
# is fetched makes a re-run resume instead of starting over. The
# cache is keyed by window label + symbol, and the window dates are
# fixed constants above, so a cached file always means the same
# date range. The cache holds delayed real market data only — never
# sample data — and a stale/wrong file can be deleted to force a
# re-fetch.
CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "fresh-cache"


class CachedDatedProvider:
    """Wraps a dated history provider and caches each symbol's
    fetched history to disk (parquet) on first fetch, returning the
    cached copy on later runs. A cache hit never touches the network."""

    def __init__(self, inner, label: str, cache_dir: str | Path = CACHE_DIR):
        self.inner = inner
        self.label = label
        self.cache_dir = Path(cache_dir)

    def _path(self, symbol: str) -> Path:
        safe = symbol.replace("/", "_")
        return self.cache_dir / f"{self.label}_{safe}.parquet"

    def get_history(self, symbol: str, days: int | None = None) -> pd.DataFrame:
        path = self._path(symbol)
        if path.exists():
            return pd.read_parquet(path)
        df = self.inner.get_history(symbol, days=days)
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path, index=False)
        return df


def _pool_fresh(windows: list[dict], strategy: str, variant_id: str) -> dict:
    """Pool the fresh windows for one strategy/variant. Fresh only —
    selection windows are never mixed in."""
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
        "holds_up": bool(pnl > 0 and win_rate > BREAK_EVEN_WIN_RATE_PCT
                         and positive_windows >= MIN_POSITIVE_WINDOWS),
    }


def run_fresh_window_test() -> dict:
    """Run the fresh-window test: 3 fresh windows, both strategies,
    baseline + wide-5 + wide-6 only. No selection window is re-run."""
    fresh_windows: list[dict] = []
    for label, start, end in FRESH_WINDOWS:
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
        window, _histories = run_window_exits(
            label, start, end, "fresh — never used for selection",
            variants=FRESH_VARIANTS, provider=provider)
        fresh_windows.append(window)

    pooled: dict[str, dict] = {}
    verdict: dict[str, dict] = {}
    for strategy in STRATEGIES:
        pooled[strategy] = {
            vid: _pool_fresh(fresh_windows, strategy, vid)
            for vid in FRESH_VARIANT_IDS
        }
        best_id = max(pooled[strategy],
                      key=lambda vid: pooled[strategy][vid]["total_pnl_usd"])
        verdict[strategy] = {
            "best_variant_by_pooled_fresh_pnl": best_id,
            "best_pooled_fresh_pnl_usd": pooled[strategy][best_id]["total_pnl_usd"],
            "variants_holding_up": [vid for vid in FRESH_VARIANT_IDS
                                    if pooled[strategy][vid]["holds_up"]],
            "verdict_rule": ("holds up = pooled fresh P&L > $0 AND pooled win rate "
                             "> 40% AND positive in at least 2 of 3 fresh windows"),
        }

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "title": "VaultTec — Phase 4d Fresh-Window Test Report",
        "method": ("Fresh-window test of the Phase 4c winners only: "
                   "wide-5 (5% stop / 7.5% target) and wide-6 (6% / 9%), "
                   "for RSI and Bollinger mean-reversion, plus the baseline "
                   "(3% / 4.5%) as a control, on three fresh 180-calendar-day "
                   "windows never used for selection (FRESH-1/2/3, all ending "
                   "before OOS-3 starts). Delayed real market history from "
                   "yfinance (free), 70 days of warm-up history before each "
                   "window, 12 symbols, 5-day walk-forward steps, signals "
                   "from history up to the trade day only — no look-ahead. "
                   "Every trade goes through the real PaperTradingEngine and "
                   "Risk Engine, balanced profile, $10,000 virtual cash, "
                   "long-only, 10-day exit. Every variant keeps a stop-loss; "
                   "the stop is never removed. Fetched histories are cached "
                   "to data/fresh-cache/ as they arrive, so an interrupted "
                   "run resumes from disk instead of re-fetching. Fresh results are pooled ONLY "
                   "across the fresh windows — never with the selection "
                   "windows, which are not re-run here."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance)",
        "fresh_windows_definition": [
            {"label": label, "start": start, "end": end}
            for label, start, end in FRESH_WINDOWS
        ],
        "selection_windows_not_used": {
            "oos_windows": [{"label": label, "start": start, "end": end}
                            for label, start, end in OOS_WINDOWS],
            "phase4_window": "2026-02-23 -> 2026-11-06 (stocks; crypto 2026-05-14 -> 2026-11-09)",
            "phase4c_pooled_selection_results": {
                "rsi": {"wide-5": {"trades": 67, "win_rate_pct": 59.7, "total_pnl_usd": 1517.23},
                        "wide-6": {"trades": 67, "win_rate_pct": 59.7, "total_pnl_usd": 1441.19},
                        "baseline": {"trades": 67, "win_rate_pct": 47.8, "total_pnl_usd": 341.61}},
                "bollinger": {"wide-5": {"trades": 40, "win_rate_pct": 65.0, "total_pnl_usd": 888.92},
                              "wide-6": {"trades": 40, "win_rate_pct": 65.0, "total_pnl_usd": 880.48},
                              "baseline": {"trades": 40, "win_rate_pct": 42.5, "total_pnl_usd": 27.76}},
            },
        },
        "verdict_rule": ("A variant 'holds up' on fresh data when its pooled "
                         "fresh-window paper P&L is > $0 AND its pooled win rate "
                         "is > 40% (the 1.5:1 break-even) AND it is positive in "
                         "at least 2 of the 3 fresh windows."),
        "variants": [
            {"id": v.id, "label": v.label, "stop_pct": v.stop_pct,
             "take_pct": v.take_pct, "horizon_days": v.horizon_days,
             "use_filter": v.use_filter, "signal_exit": v.signal_exit,
             "description": v.description}
            for v in FRESH_VARIANTS
        ],
        "fresh_windows": fresh_windows,
        "pooled_fresh": pooled,
        "verdict": verdict,
        "note": ("Fresh-window results are the honest check on Phase 4c: "
                 "the wide-stop variants were picked because they looked "
                 "good on OOS-1/2/3, so those windows cannot confirm them. "
                 "A variant that holds up here — positive pooled, above "
                 "break-even win rate, positive in at least 2 of 3 fresh "
                 "windows — has survived a genuinely new test; a variant "
                 "that fades or reverses here means the Phase 4c result "
                 "was selection luck, and the wider stop should not be "
                 "trusted on its own. Nothing here proves future profits: "
                 "past performance does not guarantee future results, and "
                 "live paper trades over real days plus a compliance/legal "
                 "review are still required before any real money is "
                 "considered."),
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
        "This report tests exit rules on past prices — it does not "
        "promise profits. Past performance does not guarantee future results.",
        "",
        "## How it was run",
        "",
        f"- {report['method']}",
        f"- Data: {report['data_source']}",
        f"- Verdict rule: {report['verdict_rule']}",
        "",
        "## Fresh windows (never used for selection)",
        "",
        "All three end before OOS-3 starts (2024-09-01) and none overlaps "
        "OOS-1/2/3, the Phase 4 window, or each other:",
        "",
    ]
    for w in report["fresh_windows_definition"]:
        lines.append(f"- **{w['label']}**: {w['start']} → {w['end']}")
    lines += [
        "",
        "## What Phase 4c found on the selection windows (for comparison only — NOT pooled with fresh results)",
        "",
    ]
    sel = report["selection_windows_not_used"]["phase4c_pooled_selection_results"]
    for strategy in STRATEGIES:
        lines.append(f"### {strategy_label(strategy)} — Phase 4c pooled OOS-1/2/3")
        lines.append("")
        for vid, r in sel[strategy].items():
            lines.append(f"- {vid}: {r['trades']} trades, {r['win_rate_pct']}% win, "
                         f"{_fmt_money(r['total_pnl_usd'])}")
        lines.append("")
    lines += ["## Pooled fresh-window verdict — 3 fresh windows, per strategy", ""]
    for strategy in STRATEGIES:
        lines += [f"### {strategy_label(strategy)}", "",
                  "| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Holds up |",
                  "|---|---:|---:|---:|---:|:---:|:---:|"]
        for variant_id, pooled in report["pooled_fresh"][strategy].items():
            lines.append(
                f"| {variant_id} | {pooled['trades']} | {pooled['win_rate_pct']:.1f}% | "
                f"{_fmt_money(pooled['total_pnl_usd'])} | {_fmt_money(pooled['expectancy_usd'])} | "
                f"{pooled['positive_windows']}/{pooled['windows_total']} | "
                f"{'yes' if pooled['holds_up'] else 'NO'} |")
        lines.append("")
    lines += ["## Verdict", ""]
    for strategy in STRATEGIES:
        verdict = report["verdict"][strategy]
        lines += [
            f"### {strategy_label(strategy)}",
            "",
            f"- Best variant by pooled fresh P&L: **{verdict['best_variant_by_pooled_fresh_pnl']}** "
            f"({_fmt_money(verdict['best_pooled_fresh_pnl_usd'])}).",
            f"- Variants holding up on fresh data: "
            f"{verdict['variants_holding_up'] or 'none'}.",
            f"- Verdict rule: {verdict['verdict_rule']}.",
            "",
        ]
    lines += [
        "## Reading it honestly",
        "",
        "A wider stop helps only if the win rate rises enough to pay "
        "for the bigger losses when the stop does fire — at 1.5:1 the "
        "break-even win rate is 40%, so a 60% win rate with a 5% stop "
        "is worth far more than a 60% win rate with a 3% stop, and a "
        "win rate just above 40% with a wide stop can still lose money. "
        "Fresh windows are a genuinely new test, but they are still "
        "past prices: three more windows do not prove the next window, "
        "and a variant that holds up here still needs live paper "
        "trades over real days — where prices arrive one day at a time "
        "and cannot be re-run — before real money is ever considered.",
        "",
    ]
    for window in report["fresh_windows"]:
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
        "## Trades (every trade, in order) — wide-5 and wide-6",
        "",
        "Trade-by-trade rows for the two winning variants are printed "
        "here. Every trade for every variant (including the baseline) "
        "is in the JSON report.",
        "",
    ]
    for window in report["fresh_windows"]:
        for strategy in STRATEGIES:
            for variant_id in ("wide-5", "wide-6"):
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
                stem: str = "phase4d-fresh-window-report") -> tuple[Path, Path]:
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
    report = run_fresh_window_test()
    json_path, md_path = save_report(report, base / "validation")
    print(f"Data: {report['data_source']}")
    for strategy in STRATEGIES:
        for variant_id, pooled in report["pooled_fresh"][strategy].items():
            print(f"{strategy} / {variant_id}: {pooled['trades']} trades, "
                  f"{pooled['win_rate_pct']}% win, P&L {_fmt_money(pooled['total_pnl_usd'])}, "
                  f"expectancy {_fmt_money(pooled['expectancy_usd'])}, "
                  f"positive {pooled['positive_windows']}/{pooled['windows_total']} windows "
                  f"({'HOLDS UP' if pooled['holds_up'] else 'does NOT hold up'})")
        verdict = report["verdict"][strategy]
        print(f"{strategy}: best fresh = {verdict['best_variant_by_pooled_fresh_pnl']}, "
              f"holding up = {verdict['variants_holding_up'] or 'none'}")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    sys.exit(0)
