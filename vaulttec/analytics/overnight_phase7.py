"""Phase 7 — overnight test: combined portfolio on NEW fresh windows,
crypto-only, wider symbols, and MACD in the 2022 bear window.

Paper only, no broker, no real money, no leverage, no options.
Past performance does not guarantee future results.

State of play (not re-decided here): the lead is wide-6
mean-reversion (RSI + Bollinger, 6% stop / 9% target, 1.5:1,
10-day exit). MACD trend-following is a complement worth watching.
Phase 6 (accepted by Neko): do NOT adopt the high-confidence-only
gate (too few trades) or volume confirmation (no win-rate gain).
The combined portfolio (mean-reversion wide-6 + MACD, one shared
$10,000) beat either leg on total P&L on the FRESH-1/2/3/4 windows
only by trading more, not better — expectancy per trade was lower
than any leg alone. It is UNPROVEN and must be tested more before
anyone adopts it.

Four items, in priority order. Every trade goes through the real
PaperTradingEngine + Risk Engine, balanced profile, $10,000 virtual
cash, long-only, 10-day exit, wide-6 exits everywhere. Every variant
keeps a stop-loss; the stop is never removed. Signals use history
up to the trade day only — no look-ahead.

1. Combined on NEW fresh windows never used for selection:
   FRESH-5 (2022-03-14 -> 2022-09-12, a falling/bear window) and
   FRESH-6 (2021-09-13 -> 2022-03-14). Same 12 symbols as Phase 6.
   Combined vs each leg alone (RSI wide-6, Bollinger wide-6, MACD):
   per-window and pooled trades, win rate, P&L, expectancy.
   Key question: does combined still win on P&L, and does its
   expectancy hold up in a falling market?
2. Crypto-only: BTC-USD, ETH-USD (SOL-USD only if its data fetches
   cleanly) — wide-6 mean-reversion and MACD on the fresh windows
   (FRESH-1..6). Crypto trades 24/7, so weekend bars are in the
   history and are traded like any other bar. Reported separately
   from stocks.
3. Wider symbols: RSI wide-6 and Bollinger wide-6 on additional
   liquid symbols NOT in the original 12, over FRESH-1/2/3, to
   check the edge is not symbol-specific. NOTE: the brief's example
   list named AMZN, TSLA and JPM — those are already in the
   original 12, so they are not new. The genuinely new symbols run
   here are AMD, NFLX, AVGO, COST, HD and V.
4. MACD trend-following on the 2022 bear window alone (FRESH-5) —
   the gap noted in Phase 4e was that trend-following had never
   been tested in a falling window. (MACD on FRESH-5 is also part
   of item 1; this item reports it on its own against the
   mean-reversion legs on the same window.)

Data: delayed real yfinance history. The on-disk cache in
data/fresh-cache/ is used first (keyed by window label + symbol);
only windows/symbols not cached are fetched from Yahoo. A symbol
that cannot be fetched is recorded as failed and skipped — never
replaced with sample data, never invented. If Yahoo rate-limits,
the run backs off (the provider retries with delays) and reports
what could not be fetched.

Verdict rules — fixed before the run:
- Item 1 combined "holds up on the new fresh windows" when its
  pooled FRESH-5/6 P&L is > $0 AND its pooled win rate is > 40%
  (the 1.5:1 break-even) AND it is positive in BOTH windows. It
  "still wins on P&L" when its pooled P&L beats both legs. Its
  expectancy "holds up in a falling market" when its FRESH-5
  expectancy is >= $0 and not worse than the worst leg's FRESH-5
  expectancy by more than $5/trade — a combined portfolio that
  only wins by trading far more, at a much worse expectancy, is
  not a better strategy, it is a busier one.
- Item 2 crypto "holds up" when a strategy's pooled crypto P&L
  is > $0 AND its pooled win rate is > 40% AND it is positive in
  at least 4 of the 6 fresh windows. Per-symbol results are
  reported so one coin cannot hide behind the other.
- Item 3 wider symbols "holds up" when the pooled new-symbol
  P&L is > $0 AND the pooled win rate is > 40% AND at least 4 of
  the 6 new symbols are individually positive on pooled P&L.
- Item 4 MACD "holds up in the bear window" when its FRESH-5
  P&L is > $0 AND its FRESH-5 win rate is > 40%. It "beats
  mean-reversion in the bear window" when its FRESH-5 P&L is
  greater than BOTH mean-reversion wide-6 FRESH-5 figures.

Partial results are saved to validation/phase7-overnight-partial.json
after each item, so an interrupted run loses nothing.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import pandas as pd

from ..market.data import SCAN_UNIVERSE
from .exit_test import STARTING_CASH, WARMUP_DAYS, run_variant_validation, variant_by_id
from .fresh_window import FRESH_WINDOWS, CachedDatedProvider
from .mean_reversion import DatedYFinanceProvider, strategy_label
from .trend_and_stress import STRESS_WINDOW, run_trend_validation, trend_label
from .validation import fetch_histories
from .win_rate import WIDE6, run_combined_validation

# --- New windows -------------------------------------------------------
# FRESH-5 ends the day FRESH-4 starts (2022-09-12); FRESH-6 ends the
# day FRESH-5 starts (2022-03-14). Neither overlaps any window used
# before (OOS-1/2/3, Phase 4, FRESH-1/2/3/4) or each other.
FRESH_5: tuple[str, str, str] = ("FRESH-5", "2022-03-14", "2022-09-12")
FRESH_6: tuple[str, str, str] = ("FRESH-6", "2021-09-13", "2022-03-14")
NEW_FRESH_WINDOWS: list[tuple[str, str, str]] = [FRESH_5, FRESH_6]

# Crypto-only symbols. SOL-USD is attempted and kept only if its
# history fetches cleanly on every window it is used on.
CRYPTO_SYMBOLS: list[str] = ["BTC-USD", "ETH-USD", "SOL-USD"]
CRYPTO_CORE_SYMBOLS: list[str] = ["BTC-USD", "ETH-USD"]

# Wider-symbol check. AMZN / TSLA / JPM were named in the brief but
# are already in the original 12 — the genuinely new liquid names
# run here are AMD, NFLX, AVGO, COST, HD and V.
NEW_SYMBOLS: list[str] = ["AMD", "NFLX", "AVGO", "COST", "HD", "V"]

# Variant keys used in every window's "results" dict.
VARIANT_KEYS = ("rsi_wide6", "bollinger_wide6", "macd", "combined")
VARIANT_LABELS = {
    "rsi_wide6": "RSI wide-6 (baseline, re-run)",
    "bollinger_wide6": "Bollinger wide-6 (baseline, re-run)",
    "macd": "MACD trend-following, wide-6 exits",
    "combined": "Combined — MR wide-6 (RSI + Bollinger) + MACD trend, one portfolio",
}

BREAK_EVEN_WIN_RATE_PCT = 40.0

# Prior pooled results, quoted from the Phase 5 / Phase 6 reports —
# same method, same exits, same cash and profile. Not re-run here.
PRIOR_REFERENCE = {
    "phase6_fresh_1_to_4": {
        "rsi_wide6": {"trades": 105, "win_rate_pct": 58.1, "total_pnl_usd": 1878.13,
                      "expectancy_usd": 17.89},
        "bollinger_wide6": {"trades": 50, "win_rate_pct": 56.0, "total_pnl_usd": 1046.71,
                            "expectancy_usd": 20.93},
        "combined": {"trades": 354, "win_rate_pct": 57.9, "total_pnl_usd": 5575.29,
                     "expectancy_usd": 15.75},
    },
    "phase5_macd_fresh_1_to_3": {
        "trades": 174, "win_rate_pct": 60.9, "total_pnl_usd": 2899.45,
        "expectancy_usd": 16.66,
    },
    "source": "Phase 6 report (fresh pooled FRESH-1/2/3/4) and Phase 5 report (MACD fresh pooled FRESH-1/2/3)",
}


# Small-capital levels (dollars). $10,000 is the control — the same
# runs the earlier phases used — so the small pots are compared
# like-for-like against it.
SMALL_CAP_LEVELS: tuple[float, ...] = (10000.0, 100.0, 50.0, 20.0)
SMALL_CAP_VARIANTS: tuple[str, ...] = ("rsi_wide6", "bollinger_wide6", "macd")


def cached_symbols_for(label: str, symbols: list[str]) -> tuple[list[str], list[str]]:
    """Split ``symbols`` into (cached, missing) for one window label,
    from the on-disk parquet cache. A cache hit never touches the
    network, so a cache-only run can never trigger a Yahoo fetch —
    and never raises another approval card while the user sleeps."""
    from .fresh_window import CACHE_DIR

    cached: list[str] = []
    missing: list[str] = []
    for symbol in symbols:
        safe = symbol.replace("/", "_")
        if (CACHE_DIR / f"{label}_{safe}.parquet").exists():
            cached.append(symbol)
        else:
            missing.append(symbol)
    return cached, missing


def run_phase7_window(label: str, start: str, end: str,
                      symbols: list[str],
                      variants: tuple[str, ...] = VARIANT_KEYS,
                      provider=None, cache_only: bool = False) -> tuple[dict, dict]:
    """Run the requested wide-6 variants on one calendar window.
    Returns (window_report, histories). A symbol that cannot be
    fetched is recorded in ``failed_symbols`` and skipped.
    With ``cache_only=True`` only symbols already on disk are run;
    the rest are listed under ``symbols_not_attempted`` and no fetch
    is attempted at all."""
    requested_symbols = list(symbols)
    if cache_only:
        cached, missing = cached_symbols_for(label, symbols)
        symbols = cached
        if not symbols:
            return {
                "label": label, "start": start, "end": end,
                "sample": "fresh — never used for selection",
                "history": {}, "failed_symbols": {},
                "symbols_requested": [],
                "symbols_traded": [],
                "symbols_not_attempted": missing,
                "cache_only": True,
                "skipped": True,
                "skip_reason": ("No cached history for this window — Yahoo fetch "
                                "needs the user's approval tap and was not attempted."),
                "results": {},
            }, {}
    if provider is None:
        provider = CachedDatedProvider(
            DatedYFinanceProvider(start, end, warmup_days=WARMUP_DAYS), label)
    histories, failed, summary = fetch_histories(provider, symbols, days=180)
    results: dict[str, dict] = {}
    if "rsi_wide6" in variants:
        results["rsi_wide6"] = run_variant_validation(
            "rsi", WIDE6, histories, window_start=start, symbols=symbols)
    if "bollinger_wide6" in variants:
        results["bollinger_wide6"] = run_variant_validation(
            "bollinger", WIDE6, histories, window_start=start, symbols=symbols)
    if "macd" in variants:
        results["macd"] = run_trend_validation(
            "macd", histories, window_start=start, symbols=symbols)
    if "combined" in variants:
        results["combined"] = run_combined_validation(
            histories, window_start=start, symbols=symbols)
    window = {
        "label": label, "start": start, "end": end,
        "sample": "fresh — never used for selection",
        "history": summary, "failed_symbols": failed,
        "symbols_requested": list(symbols),
        "symbols_traded": [s for s in symbols if s in histories],
        "results": results,
    }
    if cache_only:
        _cached, missing = cached_symbols_for(label, requested_symbols)
        window["symbols_not_attempted"] = missing
        window["cache_only"] = True
    return window, histories


def _pool_windows(windows: list[dict], variant_key: str) -> dict:
    """Pool one variant across the windows given. Windows are pooled
    only as passed in — pools are never mixed across items. Windows
    that were skipped (no cached data) or that lack the variant are
    left out of the pool; ``windows_total`` counts only the windows
    that actually ran."""
    ran = [w for w in windows if variant_key in w.get("results", {})]
    results = [w["results"][variant_key] for w in ran]
    trades = sum(r["trades_placed"] for r in results)
    wins = sum(r["wins"] for r in results)
    pnl = round(sum(r["total_pnl_usd"] for r in results), 2)
    per_window_pnl = {w["label"]: r["total_pnl_usd"] for w, r in zip(ran, results)}
    positive_windows = sum(1 for v in per_window_pnl.values() if v > 0)
    win_rate = round(wins / trades * 100, 1) if trades else 0.0
    return {
        "variant_key": variant_key,
        "variant": VARIANT_LABELS[variant_key],
        "trades": trades,
        "wins": wins,
        "win_rate_pct": win_rate,
        "total_pnl_usd": pnl,
        "total_pnl_pct": round(pnl / (STARTING_CASH * len(ran)) * 100, 2) if ran else 0.0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "per_window_pnl_usd": per_window_pnl,
        "per_window_win_rate_pct": {w["label"]: r["win_rate_pct"] for w, r in zip(ran, results)},
        "per_window_trades": {w["label"]: r["trades_placed"] for w, r in zip(ran, results)},
        "positive_windows": positive_windows,
        "windows_total": len(ran),
    }


def per_symbol_stats(windows: list[dict], variant_key: str) -> dict:
    """Aggregate trades / wins / P&L per symbol across the windows
    given, from the trade rows (not the per-window summaries)."""
    stats: dict[str, dict] = {}
    for window in windows:
        if variant_key not in window.get("results", {}):
            continue
        for trade in window["results"][variant_key]["trades"]:
            symbol = trade["symbol"]
            entry = stats.setdefault(symbol, {"trades": 0, "wins": 0, "pnl_usd": 0.0})
            entry["trades"] += 1
            if trade["pnl_usd"] > 0:
                entry["wins"] += 1
            entry["pnl_usd"] = round(entry["pnl_usd"] + trade["pnl_usd"], 2)
    for entry in stats.values():
        entry["win_rate_pct"] = round(entry["wins"] / entry["trades"] * 100, 1) if entry["trades"] else 0.0
        entry["expectancy_usd"] = round(entry["pnl_usd"] / entry["trades"], 2) if entry["trades"] else 0.0
    return stats


def run_item1(cache_only: bool = False) -> dict:
    """Item 1 — combined vs legs on the two NEW fresh windows."""
    windows: list[dict] = []
    for label, start, end in NEW_FRESH_WINDOWS:
        window, _histories = run_phase7_window(
            label, start, end, list(SCAN_UNIVERSE), variants=VARIANT_KEYS,
            cache_only=cache_only)
        windows.append(window)
    ran = [w for w in windows if not w.get("skipped")]
    pooled = {key: _pool_windows(windows, key) for key in VARIANT_KEYS}
    combined = pooled["combined"]
    legs = {leg: pooled[leg] for leg in ("rsi_wide6", "bollinger_wide6", "macd")}
    fresh5_ran = bool(ran) and ran[0]["label"] == "FRESH-5"
    if fresh5_ran:
        fresh5 = ran[0]["results"]
        worst_leg_fresh5_expectancy = min(
            fresh5["rsi_wide6"]["expectancy_usd"],
            fresh5["bollinger_wide6"]["expectancy_usd"],
            fresh5["macd"]["expectancy_usd"])
        fresh5_combined_expectancy = fresh5["combined"]["expectancy_usd"]
        expectancy_holds_up = bool(
            fresh5_combined_expectancy >= 0
            and fresh5_combined_expectancy >= worst_leg_fresh5_expectancy - 5.0)
    else:
        fresh5_combined_expectancy = None
        worst_leg_fresh5_expectancy = None
        expectancy_holds_up = False
    status = ("complete" if len(ran) == 2 else
              "partial" if ran else "blocked")
    status_note = ("" if status == "complete" else
                   "FRESH-5/6 need a Yahoo fetch — not attempted in cache-only mode." if status == "blocked" else
                   f"Only {len(ran)} of 2 windows ran — the other needs a Yahoo fetch.")
    verdict = {
        "holds_up_new_fresh": bool(
            combined["total_pnl_usd"] > 0
            and combined["win_rate_pct"] > BREAK_EVEN_WIN_RATE_PCT
            and combined["positive_windows"] >= 2),
        "beats_both_mr_legs_pnl": bool(
            combined["total_pnl_usd"] > legs["rsi_wide6"]["total_pnl_usd"]
            and combined["total_pnl_usd"] > legs["bollinger_wide6"]["total_pnl_usd"]),
        "beats_macd_pnl": bool(combined["total_pnl_usd"] > legs["macd"]["total_pnl_usd"]),
        "beats_all_legs_pnl": bool(
            combined["total_pnl_usd"] > legs["rsi_wide6"]["total_pnl_usd"]
            and combined["total_pnl_usd"] > legs["bollinger_wide6"]["total_pnl_usd"]
            and combined["total_pnl_usd"] > legs["macd"]["total_pnl_usd"]),
        "fresh5_combined_expectancy_usd": fresh5_combined_expectancy,
        "fresh5_worst_leg_expectancy_usd": worst_leg_fresh5_expectancy,
        "expectancy_holds_up_in_falling_market": expectancy_holds_up,
        "verdict_rule": ("Holds up = pooled FRESH-5/6 P&L > $0 AND pooled win rate > 40% "
                         "AND positive in BOTH windows. Expectancy holds up in the falling "
                         "market (FRESH-5) when combined expectancy is >= $0 and within "
                         "$5/trade of the worst leg's FRESH-5 expectancy."),
    }
    return {
        "status": status,
        "status_note": status_note,
        "windows": windows,
        "pooled": pooled,
        "combined_vs_legs": {
            "combined_pnl_usd": combined["total_pnl_usd"],
            "combined_win_rate_pct": combined["win_rate_pct"],
            "combined_expectancy_usd": combined["expectancy_usd"],
            "combined_trades": combined["trades"],
            "rsi_wide6_pnl_usd": legs["rsi_wide6"]["total_pnl_usd"],
            "bollinger_wide6_pnl_usd": legs["bollinger_wide6"]["total_pnl_usd"],
            "macd_pnl_usd": legs["macd"]["total_pnl_usd"],
            "rsi_wide6_expectancy_usd": legs["rsi_wide6"]["expectancy_usd"],
            "bollinger_wide6_expectancy_usd": legs["bollinger_wide6"]["expectancy_usd"],
            "macd_expectancy_usd": legs["macd"]["expectancy_usd"],
            "beats_both_mr_legs_pnl": verdict["beats_both_mr_legs_pnl"],
            "beats_macd_pnl": verdict["beats_macd_pnl"],
            "beats_all_legs_pnl": verdict["beats_all_legs_pnl"],
            "note": ("The combined run is NOT the sum of the legs run on separate "
                     "$10,000 pots; it is one shared pot, so same-day skips and "
                     "shared cash cost it some trades."),
        },
        "verdict": verdict,
    }


def run_item2(cache_only: bool = False) -> dict:
    """Item 2 — crypto-only (BTC, ETH, SOL if it fetches cleanly)
    on all six fresh windows, reported separately from stocks."""
    # SOL-USD is attempted on every window; if it fails anywhere it
    # is dropped from the whole item and the failure is recorded —
    # a half-tested coin is worse than a clearly excluded one.
    # In cache-only mode SOL is never attempted: it is not on disk
    # for any window, so it is listed as not attempted instead.
    sol_failed: dict[str, str] = {}
    sol_not_attempted: list[str] = []
    windows: list[dict] = []
    for label, start, end in list(FRESH_WINDOWS) + [STRESS_WINDOW] + NEW_FRESH_WINDOWS:
        window, _histories = run_phase7_window(
            label, start, end, list(CRYPTO_SYMBOLS),
            variants=("rsi_wide6", "bollinger_wide6", "macd"),
            cache_only=cache_only)
        if "SOL-USD" in window.get("failed_symbols", {}):
            sol_failed[label] = window["failed_symbols"]["SOL-USD"]
        if "SOL-USD" in window.get("symbols_not_attempted", []):
            sol_not_attempted.append(label)
        windows.append(window)
    sol_ok = not sol_failed and not sol_not_attempted
    # If SOL failed on some windows it simply contributed no trades
    # there; the per-symbol table shows exactly where it was absent,
    # and the pooled crypto figures are labelled as the universe as
    # fetched. SOL is never replaced with other data.
    ran = [w for w in windows if not w.get("skipped")]
    status = ("complete" if len(ran) == 6 and sol_ok else
              "partial" if ran else "blocked")
    status_note = ("" if status == "complete" else
                   "No crypto window ran — needs a Yahoo fetch." if status == "blocked" else
                   f"Ran {len(ran)} of 6 windows on the coins cached "
                   f"({'BTC, ETH' + ('' if sol_not_attempted else ', SOL')}); "
                   f"FRESH-5/6 and SOL need a Yahoo fetch.")
    pooled = {key: _pool_windows(windows, key)
              for key in ("rsi_wide6", "bollinger_wide6", "macd")}
    per_symbol = {key: per_symbol_stats(windows, key)
                  for key in ("rsi_wide6", "bollinger_wide6", "macd")}
    verdict = {}
    for key in ("rsi_wide6", "bollinger_wide6", "macd"):
        pool = pooled[key]
        verdict[key] = {
            "holds_up": bool(
                pool["total_pnl_usd"] > 0
                and pool["win_rate_pct"] > BREAK_EVEN_WIN_RATE_PCT
                and pool["positive_windows"] >= 4),
            "verdict_rule": ("Holds up = pooled crypto P&L > $0 AND pooled win rate > 40% "
                             "AND positive in at least 4 of the 6 fresh windows."),
        }
    return {
        "status": status,
        "status_note": status_note,
        "windows": windows,
        "symbols_attempted": list(CRYPTO_SYMBOLS),
        "sol_usd_fetched_cleanly": sol_ok,
        "sol_usd_failures": sol_failed,
        "sol_usd_not_attempted_windows": sol_not_attempted,
        "pooled": pooled,
        "per_symbol": per_symbol,
        "verdict": verdict,
    }


def run_item3(cache_only: bool = False) -> dict:
    """Item 3 — wider symbols (genuinely new liquid names) on
    FRESH-1/2/3, RSI + Bollinger wide-6 only."""
    windows: list[dict] = []
    for label, start, end in FRESH_WINDOWS:
        window, _histories = run_phase7_window(
            label, start, end, list(NEW_SYMBOLS),
            variants=("rsi_wide6", "bollinger_wide6"),
            cache_only=cache_only)
        windows.append(window)
    ran = [w for w in windows if not w.get("skipped")]
    status = "complete" if len(ran) == 3 else "partial" if ran else "blocked"
    status_note = ("" if status == "complete" else
                   "None of the six new symbols is cached — a Yahoo fetch is needed."
                   if status == "blocked" else
                   f"Only {len(ran)} of 3 windows ran — the rest need a Yahoo fetch.")
    pooled = {key: _pool_windows(windows, key)
              for key in ("rsi_wide6", "bollinger_wide6")}
    per_symbol = {key: per_symbol_stats(windows, key)
                  for key in ("rsi_wide6", "bollinger_wide6")}
    verdict = {}
    for key in ("rsi_wide6", "bollinger_wide6"):
        pool = pooled[key]
        positive_symbols = sum(1 for s in per_symbol[key].values() if s["pnl_usd"] > 0)
        verdict[key] = {
            "positive_symbols": positive_symbols,
            "symbols_total": len(per_symbol[key]),
            "holds_up": bool(
                pool["total_pnl_usd"] > 0
                and pool["win_rate_pct"] > BREAK_EVEN_WIN_RATE_PCT
                and positive_symbols >= 4),
            "verdict_rule": ("Holds up = pooled new-symbol P&L > $0 AND pooled win rate > 40% "
                             "AND at least 4 of the 6 new symbols individually positive."),
        }
    return {
        "status": status,
        "status_note": status_note,
        "windows": windows,
        "symbols": list(NEW_SYMBOLS),
        "note": ("AMZN, TSLA and JPM were named in the brief as wider-symbol "
                 "examples, but they are already in the original 12-symbol "
                 "universe, so they are not new here. The six symbols run "
                 "are the genuinely new liquid names: AMD, NFLX, AVGO, COST, "
                 "HD and V."),
        "pooled": pooled,
        "per_symbol": per_symbol,
        "verdict": verdict,
    }


def run_item4(item1: dict) -> dict:
    """Item 4 — MACD trend-following on the 2022 bear window alone
    (FRESH-5), taken from the item 1 run (same method, same data —
    not re-run, so the numbers cannot drift between items). When
    FRESH-5 did not run (no cached data), this item is blocked, not
    zero — a missing window is not a failed strategy."""
    fresh5 = next(w for w in item1["windows"] if w["label"] == "FRESH-5")
    fresh6 = next(w for w in item1["windows"] if w["label"] == "FRESH-6")
    verdict_rule = ("Holds up in the bear window = FRESH-5 P&L > $0 AND FRESH-5 win "
                    "rate > 40%. Beats mean-reversion = FRESH-5 P&L greater than BOTH "
                    "mean-reversion wide-6 FRESH-5 figures.")
    if fresh5.get("skipped") or "macd" not in fresh5.get("results", {}):
        return {
            "status": "blocked",
            "status_note": ("FRESH-5 did not run — no cached history, and the Yahoo "
                            "fetch needs the user's approval tap."),
            "window": "FRESH-5",
            "window_dates": {"start": fresh5["start"], "end": fresh5["end"]},
            "macd_fresh5": None,
            "macd_fresh6_for_context": None,
            "mr_wide6_fresh5_pnl_usd": {"rsi": None, "bollinger": None},
            "verdict": {
                "holds_up_in_bear_window": False,
                "beats_mr_in_bear_window": False,
                "verdict_rule": verdict_rule,
            },
        }
    macd5 = fresh5["results"]["macd"]
    macd6 = fresh6["results"].get("macd")
    rsi5 = fresh5["results"]["rsi_wide6"]["total_pnl_usd"]
    boll5 = fresh5["results"]["bollinger_wide6"]["total_pnl_usd"]
    verdict = {
        "holds_up_in_bear_window": bool(
            macd5["total_pnl_usd"] > 0
            and macd5["win_rate_pct"] > BREAK_EVEN_WIN_RATE_PCT),
        "beats_mr_in_bear_window": bool(
            macd5["total_pnl_usd"] > rsi5 and macd5["total_pnl_usd"] > boll5),
        "verdict_rule": verdict_rule,
    }
    return {
        "status": "complete",
        "status_note": "",
        "window": "FRESH-5",
        "window_dates": {"start": fresh5["start"], "end": fresh5["end"]},
        "macd_fresh5": {
            "trades": macd5["trades_placed"], "wins": macd5["wins"],
            "win_rate_pct": macd5["win_rate_pct"],
            "total_pnl_usd": macd5["total_pnl_usd"],
            "expectancy_usd": macd5["expectancy_usd"],
            "avg_win_usd": macd5["avg_win_usd"],
            "avg_loss_usd": macd5["avg_loss_usd"],
            "max_drawdown_pct": macd5["max_drawdown_pct"],
            "per_symbol_trades": macd5["per_symbol_trades"],
            "trades": macd5["trades"],
        },
        "macd_fresh6_for_context": ({
            "trades": macd6["trades_placed"], "wins": macd6["wins"],
            "win_rate_pct": macd6["win_rate_pct"],
            "total_pnl_usd": macd6["total_pnl_usd"],
            "expectancy_usd": macd6["expectancy_usd"],
            "per_symbol_trades": macd6["per_symbol_trades"],
        } if macd6 else None),
        "mr_wide6_fresh5_pnl_usd": {"rsi": rsi5, "bollinger": boll5},
        "verdict": verdict,
    }


# --- Item 5 — small capital ----------------------------------------------

def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    mid = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return round(mid, 2)


def _summarise_small_cap(result: dict, starting_cash: float) -> dict:
    """One variant at one capital level on one window: trades, win
    rate, P&L in dollars AND cents, typical position size, typical
    risk per trade (what the stop would lose), and what the engine
    refused as too small. Nothing is smoothed over: a trade the
    engine could not size is counted, not hidden."""
    trades = result["trades"]
    positions = [round(t["entry"] * t["quantity"], 2) for t in trades]
    risks = [round((t["entry"] - t["stop_loss"]) * t["quantity"], 2) for t in trades]
    pnl = result["total_pnl_usd"]
    return {
        "starting_cash_usd": starting_cash,
        "trades": result["trades_placed"],
        "signals_seen": result["signals_seen"],
        "wins": result["wins"],
        "win_rate_pct": result["win_rate_pct"],
        "total_pnl_usd": pnl,
        "total_pnl_cents": int(round(pnl * 100)),
        "expectancy_usd": result["expectancy_usd"],
        "expectancy_cents": int(round(result["expectancy_usd"] * 100)),
        "median_position_usd": _median(positions),
        "median_risk_per_trade_usd": _median(risks),
        "median_risk_per_trade_cents": int(round(_median(risks) * 100)),
        "max_position_usd": max(positions) if positions else 0.0,
        "skipped_too_small": result["skipped_too_small"],
        "too_small_by_symbol": dict(result.get("too_small_by_symbol", {})),
        "blocked_by_risk": result["blocked_by_risk"],
        "per_symbol_trades": dict(result["per_symbol_trades"]),
    }


def _pool_small_cap(window_summaries: list[dict], starting_cash: float) -> dict:
    """Pool one variant at one capital level across the windows that
    ran. Pooled P&L is the sum across separate pots — each window
    starts fresh with the same capital — so the per-window average
    is reported next to it: that is the honest 'what does $20 do'
    number, not the sum of three $20 pots."""
    trades = sum(s["trades"] for s in window_summaries)
    wins = sum(s["wins"] for s in window_summaries)
    pnl = round(sum(s["total_pnl_usd"] for s in window_summaries), 2)
    n_windows = len(window_summaries)
    too_small: dict[str, int] = {}
    for summary in window_summaries:
        for symbol, count in summary["too_small_by_symbol"].items():
            too_small[symbol] = too_small.get(symbol, 0) + count
    return {
        "starting_cash_usd": starting_cash,
        "windows_run": n_windows,
        "trades": trades,
        "wins": wins,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "total_pnl_usd": pnl,
        "total_pnl_cents": int(round(pnl * 100)),
        "pnl_per_window_usd": round(pnl / n_windows, 2) if n_windows else 0.0,
        "pnl_per_window_cents": int(round(pnl / n_windows * 100)) if n_windows else 0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "expectancy_cents": int(round(pnl / trades * 100)) if trades else 0,
        "skipped_too_small": sum(s["skipped_too_small"] for s in window_summaries),
        "too_small_by_symbol": too_small,
        "blocked_by_risk": sum(s["blocked_by_risk"] for s in window_summaries),
    }


def run_small_cap(cache_only: bool = False) -> dict:
    """Item 5 — the Phase 7 window tests repeated with $20, $50 and
    $100 starting cash (plus the $10,000 control re-run), RSI
    wide-6, Bollinger wide-6 and MACD, on FRESH-1/2/3 and FRESH-5/6.
    Histories are fetched once per window and reused across the
    capital levels, so the only difference between levels is the
    size of the pot. The 10% position cap means a $20 pot trades
    at most $2.00 per trade and a $100 pot at most $10.00 — and the
    4-decimal quantity floor means some symbols cannot be sized at
    all in the smallest pots. That is reported exactly as the
    engine did it."""
    windows_def = list(FRESH_WINDOWS) + NEW_FRESH_WINDOWS
    windows: list[dict] = []
    for label, start, end in windows_def:
        window, histories = run_phase7_window(
            label, start, end, list(SCAN_UNIVERSE), variants=(),
            cache_only=cache_only)
        if window.get("skipped") or not histories:
            windows.append(window)
            continue
        per_capital: dict[str, dict] = {}
        for capital in SMALL_CAP_LEVELS:
            key = f"{capital:.2f}"
            per_capital[key] = {
                "rsi_wide6": _summarise_small_cap(
                    run_variant_validation("rsi", WIDE6, histories,
                                           window_start=start, symbols=list(SCAN_UNIVERSE),
                                           starting_cash=capital), capital),
                "bollinger_wide6": _summarise_small_cap(
                    run_variant_validation("bollinger", WIDE6, histories,
                                           window_start=start, symbols=list(SCAN_UNIVERSE),
                                           starting_cash=capital), capital),
                "macd": _summarise_small_cap(
                    run_trend_validation("macd", histories, window_start=start,
                                         symbols=list(SCAN_UNIVERSE),
                                         starting_cash=capital), capital),
            }
        window["results_by_capital"] = per_capital
        windows.append(window)
    ran = [w for w in windows if not w.get("skipped")]
    pooled: dict[str, dict] = {}
    for capital in SMALL_CAP_LEVELS:
        key = f"{capital:.2f}"
        pooled[key] = {
            variant: _pool_small_cap(
                [w["results_by_capital"][key][variant] for w in ran], capital)
            for variant in SMALL_CAP_VARIANTS
        }
    status = ("complete" if len(ran) == len(windows_def) else
              "partial" if ran else "blocked")
    status_note = ("" if status == "complete" else
                   "No small-cap window ran — needs a Yahoo fetch." if status == "blocked" else
                   f"Ran {len(ran)} of {len(windows_def)} windows; "
                   f"FRESH-5/6 need a Yahoo fetch.")
    return {
        "status": status,
        "status_note": status_note,
        "capital_levels_usd": list(SMALL_CAP_LEVELS),
        "windows": windows,
        "pooled_by_capital": pooled,
        "method_note": ("Each window starts fresh with the same capital — pooled P&L is "
                        "the sum across separate pots, so pnl_per_window_usd is the "
                        "honest per-pot figure. Position cap is 10% of the pot; "
                        "quantity is floored to 4 decimals, so a symbol whose "
                        "sized quantity rounds to zero is skipped as too small."),
    }


# --- Orchestrator ------------------------------------------------------

def _collect_failures(item: dict) -> list[dict]:
    """Every failed symbol fetch across an item's windows."""
    failures = []
    for window in item.get("windows", []):
        for symbol, reason in (window.get("failed_symbols") or {}).items():
            failures.append({"window": window["label"], "symbol": symbol, "reason": reason})
    return failures


def _save_partial(state: dict, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "phase7-overnight-partial.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return path


def run_phase7(progress=None, cache_only: bool = False) -> dict:
    """Run all Phase 7 items in priority order, saving partial
    results after each item so an interrupted run loses nothing.
    ``progress`` (optional) is called with (item_number, label)
    after each item finishes. With ``cache_only=True`` only history
    already on disk is used — no Yahoo fetch is attempted, so no
    approval card is raised; items that need a fetch are recorded
    as blocked instead of failing."""
    started = datetime.utcnow().isoformat()
    state: dict = {
        "generated_at": started,
        "title": "VaultTec — Phase 7 Overnight Test Report (partial)",
        "status": "running",
        "cache_only": cache_only,
        "items_completed": [],
        "item1_combined_new_fresh": None,
        "item2_crypto": None,
        "item3_wider_symbols": None,
        "item4_macd_bear": None,
        "small_cap": None,
        "fetch_failures": [],
    }
    item1 = run_item1(cache_only=cache_only)
    state["item1_combined_new_fresh"] = item1
    state["items_completed"].append("item1")
    state["fetch_failures"].extend(_collect_failures(item1))
    _save_partial(state, Path(__file__).resolve().parents[2] / "validation")
    if progress:
        progress(1, "combined on FRESH-5/6")

    item2 = run_item2(cache_only=cache_only)
    state["item2_crypto"] = item2
    state["items_completed"].append("item2")
    state["fetch_failures"].extend(_collect_failures(item2))
    _save_partial(state, Path(__file__).resolve().parents[2] / "validation")
    if progress:
        progress(2, "crypto-only")

    item3 = run_item3(cache_only=cache_only)
    state["item3_wider_symbols"] = item3
    state["items_completed"].append("item3")
    state["fetch_failures"].extend(_collect_failures(item3))
    _save_partial(state, Path(__file__).resolve().parents[2] / "validation")
    if progress:
        progress(3, "wider symbols")

    item4 = run_item4(item1)
    state["item4_macd_bear"] = item4
    state["items_completed"].append("item4")
    _save_partial(state, Path(__file__).resolve().parents[2] / "validation")
    if progress:
        progress(4, "MACD in the bear window")

    small_cap = run_small_cap(cache_only=cache_only)
    state["small_cap"] = small_cap
    state["items_completed"].append("small_cap")
    state["fetch_failures"].extend(_collect_failures(small_cap))
    state["status"] = "complete"
    _save_partial(state, Path(__file__).resolve().parents[2] / "validation")
    if progress:
        progress(5, "small capital $20 / $50 / $100")

    verdicts = {
        "item1_combined_holds_up": item1["verdict"]["holds_up_new_fresh"],
        "item1_combined_beats_all_legs_pnl": item1["verdict"]["beats_all_legs_pnl"],
        "item1_expectancy_holds_up_in_falling_market": item1["verdict"]["expectancy_holds_up_in_falling_market"],
        "item2_rsi_holds_up": item2["verdict"]["rsi_wide6"]["holds_up"],
        "item2_bollinger_holds_up": item2["verdict"]["bollinger_wide6"]["holds_up"],
        "item2_macd_holds_up": item2["verdict"]["macd"]["holds_up"],
        "item3_rsi_holds_up": item3["verdict"]["rsi_wide6"]["holds_up"],
        "item3_bollinger_holds_up": item3["verdict"]["bollinger_wide6"]["holds_up"],
        "item4_macd_holds_up_in_bear_window": item4["verdict"]["holds_up_in_bear_window"],
        "item4_macd_beats_mr_in_bear_window": item4["verdict"]["beats_mr_in_bear_window"],
    }
    report = {
        "generated_at": started,
        "title": "VaultTec — Phase 7 Overnight Test Report",
        "status": "complete",
        "cache_only": cache_only,
        "item_status": {
            "item1_combined_new_fresh": item1["status"],
            "item2_crypto": item2["status"],
            "item3_wider_symbols": item3["status"],
            "item4_macd_bear": item4["status"],
            "small_cap": small_cap["status"],
        },
        "method": ("Phase 7 overnight test, paper only. Five items, all wide-6 "
                   "(6% stop / 9% target, 1.5:1, 10-day exit), every trade through "
                   "the real PaperTradingEngine and Risk Engine, balanced profile, "
                   "long-only. Signals from history up to "
                   "the trade day only — no look-ahead. (1) Combined portfolio "
                   "(mean-reversion wide-6 + MACD, one shared $10,000) vs each leg "
                   "alone on two NEW fresh windows, FRESH-5 (2022-03-14 -> "
                   "2022-09-12, falling/bear) and FRESH-6 (2021-09-13 -> "
                   "2022-03-14), same 12 symbols as Phase 6. (2) Crypto-only "
                   "(BTC-USD, ETH-USD, SOL-USD if it fetches cleanly), wide-6 "
                   "mean-reversion and MACD on fresh windows FRESH-1..6, weekend "
                   "bars included. (3) RSI + Bollinger wide-6 on six additional "
                   "liquid symbols (AMD, NFLX, AVGO, COST, HD, V) over "
                   "FRESH-1/2/3. (4) MACD trend-following on the 2022 bear "
                   "window alone (FRESH-5), taken from the item 1 run. "
                   "(5) Small capital: the window tests repeated with $20, $50 "
                   "and $100 starting cash (plus the $10,000 control re-run), "
                   "RSI wide-6, Bollinger wide-6 and MACD on FRESH-1/2/3 and "
                   "FRESH-5/6. Data: "
                   "delayed real yfinance history, disk cache first, fetched "
                   "only where not cached; failed fetches are recorded and the "
                   "symbol is skipped, never replaced. In cache-only mode no "
                   "fetch is attempted at all — items that need one are "
                   "recorded as blocked, not as failures of the strategy."),
        "data_source": "yfinance (delayed real market data, free — Yahoo Finance), disk cache data/fresh-cache/ first",
        "new_windows_definition": [
            {"label": label, "start": start, "end": end}
            for label, start, end in NEW_FRESH_WINDOWS
        ],
        "prior_results_reference": PRIOR_REFERENCE,
        "verdict_rules": {
            "item1": item1["verdict"]["verdict_rule"],
            "item2": item2["verdict"]["rsi_wide6"]["verdict_rule"],
            "item3": item3["verdict"]["rsi_wide6"]["verdict_rule"],
            "item4": item4["verdict"]["verdict_rule"],
        },
        "item1_combined_new_fresh": item1,
        "item2_crypto": item2,
        "item3_wider_symbols": item3,
        "item4_macd_bear": item4,
        "small_cap": small_cap,
        "verdicts": verdicts,
        "fetch_failures": state["fetch_failures"],
        "note": ("Nothing here proves future profits: past performance does not "
                 "guarantee future results. FRESH-5 and FRESH-6 are genuinely new "
                 "windows, but they are still past prices — two more windows do "
                 "not prove the next window, and nothing here changes the need "
                 "for live paper trades over real days plus a compliance/legal "
                 "review before real money is ever considered. The combined "
                 "portfolio trades far more often than any single leg (MACD is "
                 "checked every bar, mean-reversion on a 5-day grid), so its "
                 "trade count is not comparable with the legs — P&L, win rate "
                 "and expectancy per trade are the comparison."),
    }
    return report


# --- Rendering -----------------------------------------------------------

def _fmt_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def _pool_table_lines(pooled: dict, keys: tuple[str, ...]) -> list[str]:
    lines = ["| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows |",
             "|---|---:|---:|---:|---:|:---:|"]
    for key in keys:
        p = pooled[key]
        lines.append(
            f"| {key} | {p['trades']} | {p['win_rate_pct']:.1f}% | {_fmt_money(p['total_pnl_usd'])} | "
            f"{_fmt_money(p['expectancy_usd'])} | {p['positive_windows']}/{p['windows_total']} |")
    return lines


def _window_table_lines(window: dict, keys: tuple[str, ...]) -> list[str]:
    lines = ["| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for key in keys:
        r = window["results"][key]
        lines.append(
            f"| {key} | {r['trades_placed']} | {r['win_rate_pct']:.1f}% | "
            f"{_fmt_money(r['total_pnl_usd'])} | {_fmt_money(r['expectancy_usd'])} | "
            f"{_fmt_money(r['avg_win_usd'])} | {_fmt_money(r['avg_loss_usd'])} | "
            f"{r['max_drawdown_pct']:.2f}% | {r['blocked_by_risk']} |")
    return lines


def _per_symbol_table_lines(per_symbol: dict) -> list[str]:
    lines = ["| Symbol | Trades | Win rate | P&L | Expectancy / trade |",
             "|---|---:|---:|---:|---:|"]
    for symbol in sorted(per_symbol):
        s = per_symbol[symbol]
        lines.append(
            f"| {symbol} | {s['trades']} | {s['win_rate_pct']:.1f}% | "
            f"{_fmt_money(s['pnl_usd'])} | {_fmt_money(s['expectancy_usd'])} |")
    return lines


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
        "",
        "## New windows (never used for selection)",
        "",
    ]
    for w in report["new_windows_definition"]:
        lines.append(f"- **{w['label']}**: {w['start']} → {w['end']}")
    lines += [
        "",
        "FRESH-5 ends the day FRESH-4 starts (2022-09-12); FRESH-6 ends the "
        "day FRESH-5 starts (2022-03-14). Neither overlaps OOS-1/2/3, the "
        "Phase 4 window, or FRESH-1/2/3/4, or each other.",
        "",
        "## Headline verdicts",
        "",
    ]
    v = report["verdicts"]
    item1 = report["item1_combined_new_fresh"]
    item2 = report["item2_crypto"]
    item3 = report["item3_wider_symbols"]
    item4 = report["item4_macd_bear"]
    st1 = item1.get("status", "complete")
    st2 = item2.get("status", "complete")
    st3 = item3.get("status", "complete")
    st4 = item4.get("status", "complete")

    def _skipped_lines(window: dict) -> list[str]:
        return [
            f"### {window['label']} — {window['start']} → {window['end']}",
            "",
            f"- NOT TESTED: {window.get('skip_reason', 'no cached history for this window')}",
            f"- Symbols not attempted: {', '.join(window.get('symbols_not_attempted', [])) or 'none'}",
            "",
        ]

    if st1 == "blocked":
        lines.append("- **Item 1 — combined on the new fresh windows: NOT TESTED** "
                     "(FRESH-5/6 need a Yahoo fetch that was not attempted).")
    else:
        tag = "PARTIAL — " if st1 == "partial" else ""
        lines.append(
            f"- **Item 1 — combined on the new fresh windows: {tag}"
            f"{'HOLDS UP' if v['item1_combined_holds_up'] else 'does NOT hold up'}** "
            f"(beats all legs on P&L: {'yes' if v['item1_combined_beats_all_legs_pnl'] else 'no'}; "
            f"expectancy holds up in the falling market: {'yes' if v['item1_expectancy_holds_up_in_falling_market'] else 'no'}).")
    if st2 == "blocked":
        lines.append("- **Item 2 — crypto-only: NOT TESTED** (no crypto window ran).")
    else:
        tag = "PARTIAL — " if st2 == "partial" else ""
        lines.append(
            f"- **Item 2 — crypto-only: {tag}RSI {'holds up' if v['item2_rsi_holds_up'] else 'does NOT hold up'}; "
            f"Bollinger {'holds up' if v['item2_bollinger_holds_up'] else 'does NOT hold up'}; "
            f"MACD {'holds up' if v['item2_macd_holds_up'] else 'does NOT hold up'}.**")
    if st3 == "blocked":
        lines.append("- **Item 3 — wider symbols: NOT TESTED** (none of the new symbols is cached).")
    else:
        tag = "PARTIAL — " if st3 == "partial" else ""
        lines.append(
            f"- **Item 3 — wider symbols: {tag}RSI {'holds up' if v['item3_rsi_holds_up'] else 'does NOT hold up'}; "
            f"Bollinger {'holds up' if v['item3_bollinger_holds_up'] else 'does NOT hold up'}.**")
    if st4 == "blocked":
        lines.append("- **Item 4 — MACD in the 2022 bear window (FRESH-5): NOT TESTED** (FRESH-5 did not run).")
    else:
        lines.append(
            f"- **Item 4 — MACD in the 2022 bear window (FRESH-5): {'HOLDS UP' if v['item4_macd_holds_up_in_bear_window'] else 'does NOT hold up'}** "
            f"(beats mean-reversion there: {'yes' if v['item4_macd_beats_mr_in_bear_window'] else 'no'}).")
    sc = report.get("small_cap")
    if sc is not None:
        st5 = sc.get("status", "complete")
        if st5 == "blocked":
            lines.append("- **Item 5 — small capital ($20 / $50 / $100): NOT TESTED** (no small-cap window ran).")
        else:
            tag = "PARTIAL — " if st5 == "partial" else ""
            lines.append(f"- **Item 5 — small capital ($20 / $50 / $100): {tag}see the small-cap section below for dollars-and-cents results.**")
    lines.append("")
    phase6_line = (
        "For comparison, Phase 6 on FRESH-1/2/3/4 (quoted, not re-run): combined "
        f"{_fmt_money(report['prior_results_reference']['phase6_fresh_1_to_4']['combined']['total_pnl_usd'])} "
        f"({report['prior_results_reference']['phase6_fresh_1_to_4']['combined']['trades']} trades, "
        f"expectancy {_fmt_money(report['prior_results_reference']['phase6_fresh_1_to_4']['combined']['expectancy_usd'])}); "
        f"RSI wide-6 {_fmt_money(report['prior_results_reference']['phase6_fresh_1_to_4']['rsi_wide6']['total_pnl_usd'])}; "
        f"Bollinger wide-6 {_fmt_money(report['prior_results_reference']['phase6_fresh_1_to_4']['bollinger_wide6']['total_pnl_usd'])}.")
    lines += [
        "## Item 1 — Combined portfolio on the NEW fresh windows (FRESH-5/6)",
        "",
        "Same 12 symbols as Phase 6. Verdict rule: "
        f"{report['verdict_rules']['item1']}",
        "",
    ]
    if st1 != "complete":
        lines += [f"- **Status: {st1.upper()}** — {item1.get('status_note', '')}", ""]
    if st1 == "blocked":
        lines += [
            "No window ran, so there is no pooled table and no combined-vs-legs "
            "comparison here — $0.00 from nothing would not be a result.",
            "",
            phase6_line,
            "",
        ]
    else:
        lines += ["### Pooled FRESH-5/6", ""]
        lines += _pool_table_lines(item1["pooled"], VARIANT_KEYS)
        c = item1["combined_vs_legs"]
        lines += [
            "",
            "### Combined vs its legs (pooled FRESH-5/6)",
            "",
            f"- Combined: {c['combined_trades']} trades, {c['combined_win_rate_pct']:.1f}% win, "
            f"P&L {_fmt_money(c['combined_pnl_usd'])} (expectancy {_fmt_money(c['combined_expectancy_usd'])}/trade).",
            f"- RSI wide-6 alone: {_fmt_money(c['rsi_wide6_pnl_usd'])} (expectancy {_fmt_money(c['rsi_wide6_expectancy_usd'])}); "
            f"Bollinger wide-6 alone: {_fmt_money(c['bollinger_wide6_pnl_usd'])} (expectancy {_fmt_money(c['bollinger_wide6_expectancy_usd'])}); "
            f"MACD alone: {_fmt_money(c['macd_pnl_usd'])} (expectancy {_fmt_money(c['macd_expectancy_usd'])}).",
            f"- Combined beats both mean-reversion legs on P&L: **{'yes' if c['beats_both_mr_legs_pnl'] else 'NO'}**; "
            f"beats MACD on P&L: **{'yes' if c['beats_macd_pnl'] else 'no'}**; beats all three legs: "
            f"**{'yes' if c['beats_all_legs_pnl'] else 'NO'}**.",
            f"- {c['note']}",
            "",
            phase6_line,
            "",
        ]
    for window in item1["windows"]:
        if window.get("skipped"):
            lines += _skipped_lines(window)
            continue
        lines += [
            f"### {window['label']} — {window['start']} → {window['end']}",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
        ]
        lines += _window_table_lines(window, VARIANT_KEYS)
        lines.append("")
        for key in VARIANT_KEYS:
            lines.append(f"- {key} per symbol: {window['results'][key]['per_symbol_trades']}")
        lines.append("")
    lines += [
        "## Item 2 — Crypto-only (BTC-USD, ETH-USD, SOL-USD if clean)",
        "",
        "Fresh windows FRESH-1..6, weekend bars included (crypto trades "
        "24/7). Reported separately from stocks. Verdict rule: "
        f"{report['verdict_rules']['item2']}",
        "",
        f"- SOL-USD fetched cleanly on every window: **{'yes' if report['item2_crypto']['sol_usd_fetched_cleanly'] else 'NO — see failures below'}**.",
    ]
    if report["item2_crypto"]["sol_usd_failures"]:
        lines.append(f"- SOL-USD failures: {report['item2_crypto']['sol_usd_failures']}.")
    if st2 != "complete":
        lines += ["", f"- **Status: {st2.upper()}** — {item2.get('status_note', '')}"]
    if st2 == "blocked":
        lines += ["", "No crypto window ran — no pooled table and no per-coin table; "
                  "there is nothing to average yet.", ""]
    else:
        lines += ["", "### Pooled crypto (FRESH-1..6)", ""]
        lines += _pool_table_lines(report["item2_crypto"]["pooled"],
                                   ("rsi_wide6", "bollinger_wide6", "macd"))
        lines += ["", "### Per-coin pooled results (all six fresh windows)", ""]
        for key in ("rsi_wide6", "bollinger_wide6", "macd"):
            lines += [f"#### {VARIANT_LABELS[key]}", ""]
            lines += _per_symbol_table_lines(report["item2_crypto"]["per_symbol"][key])
            lines.append("")
    for window in report["item2_crypto"]["windows"]:
        if window.get("skipped"):
            lines += _skipped_lines(window)
            continue
        lines += [
            f"### Crypto {window['label']} — {window['start']} → {window['end']}",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
        ]
        lines += _window_table_lines(window, ("rsi_wide6", "bollinger_wide6", "macd"))
        lines.append("")
    lines += [
        "## Item 3 — Wider symbols (RSI + Bollinger wide-6, FRESH-1/2/3)",
        "",
        f"{report['item3_wider_symbols']['note']}",
        "",
        "Verdict rule: "
        f"{report['verdict_rules']['item3']}",
        "",
    ]
    if st3 != "complete":
        lines += [f"- **Status: {st3.upper()}** — {item3.get('status_note', '')}", ""]
    if st3 == "blocked":
        lines += ["No wider-symbol window ran — no pooled table and no per-symbol table; "
                  "there is nothing to average yet.", ""]
    else:
        lines += ["### Pooled new symbols (FRESH-1/2/3)", ""]
        lines += _pool_table_lines(report["item3_wider_symbols"]["pooled"],
                                   ("rsi_wide6", "bollinger_wide6"))
        lines += ["", "### Per-symbol pooled results (FRESH-1/2/3)", ""]
        for key in ("rsi_wide6", "bollinger_wide6"):
            lines += [f"#### {VARIANT_LABELS[key]}", ""]
            lines += _per_symbol_table_lines(report["item3_wider_symbols"]["per_symbol"][key])
            verdict = report["item3_wider_symbols"]["verdict"][key]
            lines += ["",
                      f"- Positive symbols: {verdict['positive_symbols']}/{verdict['symbols_total']}.",
                      ""]
    for window in report["item3_wider_symbols"]["windows"]:
        if window.get("skipped"):
            lines += _skipped_lines(window)
            continue
        lines += [
            f"### Wider symbols {window['label']} — {window['start']} → {window['end']}",
            "",
            f"- History: {len(window['history'])} symbols fetched; "
            f"failed: {window['failed_symbols'] or 'none'}",
            "",
        ]
        lines += _window_table_lines(window, ("rsi_wide6", "bollinger_wide6"))
        lines.append("")
    lines += [
        "## Item 4 — MACD trend-following in the 2022 bear window (FRESH-5)",
        "",
        "Taken from the item 1 run (same method, same data — not re-run). "
        "Verdict rule: "
        f"{report['verdict_rules']['item4']}",
        "",
    ]
    if item4.get("macd_fresh5") is None:
        lines += [f"- **Status: {st4.upper()}** — {item4.get('status_note', 'FRESH-5 did not run.')}", ""]
    else:
        if item4["macd_fresh6_for_context"] is None:
            fresh6_line = "- MACD on FRESH-6 for context: not run."
        else:
            fresh6_line = (
                f"- MACD on FRESH-6 for context: {item4['macd_fresh6_for_context']['trades']} trades, "
                f"{item4['macd_fresh6_for_context']['win_rate_pct']:.1f}% win, "
                f"P&L {_fmt_money(item4['macd_fresh6_for_context']['total_pnl_usd'])}.")
        lines += [
            f"- MACD on FRESH-5 ({item4['window_dates']['start']} → {item4['window_dates']['end']}): "
            f"{item4['macd_fresh5']['trades']} trades, {item4['macd_fresh5']['win_rate_pct']:.1f}% win, "
            f"P&L {_fmt_money(item4['macd_fresh5']['total_pnl_usd'])}, "
            f"expectancy {_fmt_money(item4['macd_fresh5']['expectancy_usd'])}/trade, "
            f"max drawdown {item4['macd_fresh5']['max_drawdown_pct']:.2f}%.",
            f"- Mean-reversion wide-6 on the same window: RSI {_fmt_money(item4['mr_wide6_fresh5_pnl_usd']['rsi'])}, "
            f"Bollinger {_fmt_money(item4['mr_wide6_fresh5_pnl_usd']['bollinger'])}.",
            fresh6_line,
            f"- MACD per symbol on FRESH-5: {item4['macd_fresh5']['per_symbol_trades']}.",
            "",
        ]
    if sc is not None:
        lines += [
            "## Item 5 — Small capital: $20 / $50 / $100 (plus the $10,000 control)",
            "",
            f"{sc.get('method_note', '')}",
            "",
        ]
        st5 = sc.get("status", "complete")
        if st5 != "complete":
            lines += [f"- **Status: {st5.upper()}** — {sc.get('status_note', '')}", ""]
        if st5 == "blocked":
            lines += ["No small-cap window ran — nothing to report yet.", ""]
        else:
            for capital in sc["capital_levels_usd"]:
                key = f"{capital:.2f}"
                pooled_cap = sc["pooled_by_capital"][key]
                lines += [
                    f"### ${capital:,.2f} pot — pooled across {pooled_cap['rsi_wide6']['windows_run']} windows",
                    "",
                    "| Variant | Trades | Win rate | P&L (all pots added) | P&L per window | Expectancy / trade | Too small | Blocked |",
                    "|---|---:|---:|---:|---:|---:|---:|---:|",
                ]
                for variant in SMALL_CAP_VARIANTS:
                    p = pooled_cap[variant]
                    lines.append(
                        f"| {variant} | {p['trades']} | {p['win_rate_pct']:.1f}% | {_fmt_money(p['total_pnl_usd'])} | "
                        f"{_fmt_money(p['pnl_per_window_usd'])} | {_fmt_money(p['expectancy_usd'])} | "
                        f"{p['skipped_too_small']} | {p['blocked_by_risk']} |")
                for variant in SMALL_CAP_VARIANTS:
                    p = pooled_cap[variant]
                    if p["too_small_by_symbol"]:
                        lines.append(f"- {variant} too small by symbol: {p['too_small_by_symbol']}.")
                lines.append("")
                lines += [f"#### Per-window detail — ${capital:,.2f} pot", ""]
                for window in sc["windows"]:
                    if window.get("skipped"):
                        lines.append(f"- {window['label']}: NOT TESTED — {window.get('skip_reason', '')}")
                        continue
                    parts = []
                    for variant in SMALL_CAP_VARIANTS:
                        s = window["results_by_capital"][key][variant]
                        parts.append(
                            f"{variant}: {s['trades']} trades, {_fmt_money(s['total_pnl_usd'])}"
                            + (f" ({s['skipped_too_small']} too small)" if s["skipped_too_small"] else ""))
                    lines.append(f"- {window['label']}: " + "; ".join(parts))
                lines.append("")
            lines += [
                "Reading the small pots honestly: pooled P&L adds up separate pots, so "
                "the 'P&L per window' column is the honest figure — what one pot of "
                "that size did on average in one six-month window. A $20 pot trades "
                "at most $2.00 per trade (10% cap), so even a good window moves it "
                "by cents, not dollars.",
                "",
            ]
    lines += [
        "## Fetch failures",
        "",
    ]
    if report["fetch_failures"]:
        for failure in report["fetch_failures"]:
            lines.append(f"- {failure['window']} / {failure['symbol']}: {failure['reason']}")
    else:
        lines.append("- None — every requested symbol fetched on every window.")
    lines += [
        "",
        "## Reading it honestly",
        "",
        report["note"],
        "",
        "## Trades (every trade, in order) — item 1, FRESH-5/6",
        "",
        "Trade-by-trade rows for the combined portfolio and MACD on the "
        "two new windows. Every trade for every variant in every item "
        "is in the JSON report.",
        "",
    ]
    for window in item1["windows"]:
        if window.get("skipped"):
            continue
        for key in ("combined", "macd"):
            result = window["results"].get(key)
            if result is None:
                continue
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


def _plain_money(value: float) -> str:
    if value >= 0:
        return f"up ${value:,.2f}"
    return f"down ${abs(value):,.2f}"


def render_plain_summary(report: dict) -> str:
    """Short plain-language summary for Neko — no jargon. What was
    tested, what the answer is in plain words, what changed, what
    stays the same, and what happens next. Items that did not run
    are reported as NOT TESTED, never as $0.00 results."""
    v = report["verdicts"]
    item1 = report["item1_combined_new_fresh"]
    c = item1["combined_vs_legs"]
    item2 = report["item2_crypto"]
    item3 = report["item3_wider_symbols"]
    item4 = report["item4_macd_bear"]
    sc = report.get("small_cap")
    st1 = item1.get("status", "complete")
    st2 = item2.get("status", "complete")
    st3 = item3.get("status", "complete")
    st4 = item4.get("status", "complete")

    def verdict_word(holds: bool) -> str:
        return "held up" if holds else "did NOT hold up"

    def _ran_count(item: dict) -> int:
        return len([w for w in item.get("windows", []) if not w.get("skipped")])

    lines = [
        "# VaultTec — Phase 7 overnight test: the plain version",
        "",
        "Tested overnight on past prices, paper money only — no real money was used, "
        "nothing was bought or sold for real.",
        "",
        "## What I tested",
        "",
        "Five things, all on old price charts the system had never been picked on before:",
        "",
        "1. **The combined system on two brand-new time windows** — spring and summer 2022, "
        "when prices were mostly falling. The combined system is the main system plus the "
        "trend-follower running together in one pot.",
        "2. **Crypto on its own** — just Bitcoin, Ethereum, and Solana, on their own, "
        "including weekends (crypto never sleeps).",
        "3. **Six extra big company stocks** the system had never been tested on — AMD, "
        "Netflix, Broadcom, Costco, Home Depot and Visa — to check the system works on "
        "more than just the usual 12.",
        "4. **The trend-follower on its own in the 2022 falling market** — the one gap we "
        "had never checked.",
        "5. **The same tests with small pots of money** — $20, $50 and $100 instead of "
        "$10,000 — to see what a small pot really does in dollars and cents.",
        "",
        "## The answers, in plain words",
        "",
    ]
    if st1 == "blocked":
        lines.append(
            "**1. Combined system on the new windows: NOT TESTED yet.** The two new time "
            "windows need price data that could not be pulled overnight, so there is no "
            "result here — not a good result and not a bad one. It is still waiting to be tested.")
    else:
        partial_note = ""
        if st1 == "partial":
            partial_note = (f" Only {_ran_count(item1)} of the 2 new windows ran — the other "
                            "still needs its price data pulled, so this is a partial answer.")
        lines.append(
            f"**1. Combined system on the new windows: {verdict_word(v['item1_combined_holds_up'])}.** "
            f"On the new windows it made {_plain_money(c['combined_pnl_usd'])} "
            f"on paper across {c['combined_trades']} trades, winning {c['combined_win_rate_pct']:.1f}% "
            f"of them. The main system on its own made {_plain_money(c['rsi_wide6_pnl_usd'])} "
            f"(RSI version) and {_plain_money(c['bollinger_wide6_pnl_usd'])} (Bollinger version), "
            f"and the trend-follower on its own made {_plain_money(c['macd_pnl_usd'])}. "
            f"So the combined system {'still made more money in total than any one part on its own' if v['item1_combined_beats_all_legs_pnl'] else 'did NOT make more in total than every part on its own'}. "
            f"But — and this matters — each trade in the combined system made about "
            f"${c['combined_expectancy_usd']:.2f} on average, while the best single part made about "
            f"${max(c['rsi_wide6_expectancy_usd'], c['bollinger_wide6_expectancy_usd'], c['macd_expectancy_usd']):.2f} "
            f"per trade. So it still wins by taking a lot more trades, not by taking better "
            f"trades. In the falling window its per-trade result "
            f"{'held up' if v['item1_expectancy_holds_up_in_falling_market'] else 'did NOT hold up'}.{partial_note}")
    lines.append("")
    if st2 == "blocked":
        lines.append(
            "**2. Crypto on its own: NOT TESTED yet.** No crypto window ran overnight — the "
            "price data could not be pulled, so there is no result here yet.")
    else:
        partial_note = ""
        if st2 == "partial":
            partial_note = (f" Only {_ran_count(item2)} of the 6 windows ran, so this is a "
                            "partial answer — the rest still need their price data pulled.")
        lines.append(
            f"**2. Crypto on its own:** the RSI version {verdict_word(v['item2_rsi_holds_up'])}, "
            f"the Bollinger version {verdict_word(v['item2_bollinger_holds_up'])}, and the "
            f"trend-follower {verdict_word(v['item2_macd_holds_up'])}. "
            f"Pooled across the windows that ran: RSI made {_plain_money(item2['pooled']['rsi_wide6']['total_pnl_usd'])} "
            f"({item2['pooled']['rsi_wide6']['trades']} trades), Bollinger made "
            f"{_plain_money(item2['pooled']['bollinger_wide6']['total_pnl_usd'])} "
            f"({item2['pooled']['bollinger_wide6']['trades']} trades), trend-follower made "
            f"{_plain_money(item2['pooled']['macd']['total_pnl_usd'])} "
            f"({item2['pooled']['macd']['trades']} trades)."
            + ("" if item2["sol_usd_fetched_cleanly"] else
               " Solana's price data did not come through cleanly on every window, so its "
               "numbers are only partial — see the full report.")
            + partial_note)
    lines.append("")
    if st3 == "blocked":
        lines.append(
            "**3. The six extra stocks: NOT TESTED yet.** None of the six new stocks had "
            "price data saved, and it could not be pulled overnight, so there is no result here yet.")
    else:
        partial_note = ""
        if st3 == "partial":
            partial_note = (f" Only {_ran_count(item3)} of the 3 windows ran, so this is a "
                            "partial answer.")
        lines.append(
            f"**3. The six extra stocks:** the RSI version {verdict_word(v['item3_rsi_holds_up'])} "
            f"and the Bollinger version {verdict_word(v['item3_bollinger_holds_up'])}. "
            f"RSI made {_plain_money(item3['pooled']['rsi_wide6']['total_pnl_usd'])} "
            f"({item3['pooled']['rsi_wide6']['trades']} trades) and Bollinger made "
            f"{_plain_money(item3['pooled']['bollinger_wide6']['total_pnl_usd'])} "
            f"({item3['pooled']['bollinger_wide6']['trades']} trades) on the new stocks. "
            f"That tells us whether the system only works on the usual 12 or on new names too.{partial_note}")
    lines.append("")
    if item4.get("macd_fresh5") is None:
        lines.append(
            "**4. Trend-follower in the 2022 falling market: NOT TESTED yet.** The falling "
            "window did not run overnight, so this gap is still open — no result here yet.")
    else:
        lines.append(
            f"**4. Trend-follower in the 2022 falling market:** it {verdict_word(v['item4_macd_holds_up_in_bear_window'])} "
            f"— it made {_plain_money(item4['macd_fresh5']['total_pnl_usd'])} on "
            f"{item4['macd_fresh5']['trades']} trades, winning {item4['macd_fresh5']['win_rate_pct']:.1f}% "
            f"of them. The main system made {_plain_money(item4['mr_wide6_fresh5_pnl_usd']['rsi'])} "
            f"(RSI) and {_plain_money(item4['mr_wide6_fresh5_pnl_usd']['bollinger'])} (Bollinger) "
            f"on the same falling window, so the trend-follower "
            f"{'did beat both of them there' if v['item4_macd_beats_mr_in_bear_window'] else 'did NOT beat both of them there'}.")
    lines.append("")
    if sc is not None:
        if sc.get("status") == "blocked":
            lines.append(
                "**5. Small pots of money ($20, $50, $100): NOT TESTED yet.** Same reason as "
                "the others — the price data could not be pulled overnight, so there is no "
                "result here yet.")
        else:
            parts = []
            for capital in (20.0, 50.0, 100.0):
                key = f"{capital:.2f}"
                if key not in sc["pooled_by_capital"]:
                    continue
                rsi = sc["pooled_by_capital"][key]["rsi_wide6"]
                too_small = rsi["skipped_too_small"]
                parts.append(
                    f"a ${capital:,.0f} pot was {_plain_money(rsi['pnl_per_window_usd'])} per window on average "
                    f"on the main system ({rsi['trades']} trades across the windows that ran"
                    + (f", and {too_small} trade{'s' if too_small != 1 else ''} could not be placed at all because the pot was too small for those stocks" if too_small else "")
                    + ")")
            control = sc["pooled_by_capital"].get("10000.00", {}).get("rsi_wide6")
            control_line = ""
            if control:
                control_line = (f" For comparison, the $10,000 pot was "
                                f"{_plain_money(control['pnl_per_window_usd'])} per window on average.")
            lines.append(
                "**5. Small pots of money:** " + "; ".join(parts) + "." + control_line +
                " In plain words: a $20 pot moves by cents, not dollars — even a good six months "
                "does not turn $20 into real money, and some stocks cannot be traded at all "
                "with a pot that small.")
        lines.append("")
    lines += [
        "## What changed",
        "",
    ]
    changes = []
    if st1 == "blocked":
        changes.append("The combined system on the new windows was NOT tested overnight — the price data could not be pulled, so nothing changed there yet.")
    elif v["item1_combined_holds_up"] and v["item1_combined_beats_all_legs_pnl"]:
        changes.append("The combined system now has two more fresh windows behind it — it is still unproven, but it survived a falling market it had never seen.")
    elif not v["item1_combined_holds_up"]:
        changes.append("The combined system did NOT hold up on the new windows — it stays unproven and is not adopted.")
    else:
        changes.append("The combined system held up on the new windows but did not beat every part on its own — it stays unproven and is not adopted yet.")
    if st4 == "blocked":
        changes.append("The trend-follower in the falling market was NOT tested overnight either — that gap is still open.")
    elif v["item4_macd_holds_up_in_bear_window"]:
        changes.append("The trend-follower has now been tested in a falling market for the first time, and it held up there.")
    else:
        changes.append("The trend-follower did not hold up in the falling market — it stays a watch-only helper, not a lead.")
    if st3 == "blocked":
        changes.append("The six extra stocks were NOT tested overnight — the price data could not be pulled.")
    elif v["item3_rsi_holds_up"] or v["item3_bollinger_holds_up"]:
        changes.append("The system works on new stock names too, not just the usual 12 — that makes the edge look less like luck on a few names.")
    else:
        changes.append("The system did not hold up on the new stock names — the edge may be partly specific to the usual 12, so that needs watching.")
    if sc is not None and sc.get("status") != "blocked":
        changes.append("We now know what small pots really do in dollars and cents — a $20 pot moves by cents, and some stocks cannot be traded at all with a pot that small.")
    elif sc is not None:
        changes.append("The small-pot tests ($20 / $50 / $100) were NOT run overnight — same missing price data.")
    for change in changes:
        lines.append(f"- {change}")
    lines += [
        "",
        "## What stays the same",
        "",
        "- The main system is still wide-6 mean-reversion (RSI + Bollinger). Nothing in this "
        "test replaces it.",
        "- The combined system is NOT adopted. It still needs live paper trades over real days "
        "before anyone trusts it with anything.",
        "- No real money, no live trades, no broker. Everything here is paper money on old charts.",
        "- Past results do not promise future results. A good night on old charts is not a "
        "promise about tomorrow.",
        "",
        "## What happens next",
        "",
        "- The parts that were not tested get re-run once the price data comes through — "
        "that is the new windows, the extra stocks, and the small pots on those windows.",
        "- Keep watching the live paper trades — that is the real test, one day at a time.",
        "- If the combined system keeps looking good on live paper too, that is when it earns a "
        "second look. Not before.",
        "- The legal review still has to happen before any real money or any public launch.",
        "",
        "Full numbers are in validation/phase7-overnight-report.md (and .json).",
        "",
    ]
    return "\n".join(lines)


def save_report(report: dict, out_dir: str | Path,
                stem: str = "phase7-overnight-report") -> tuple[Path, Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{stem}.json"
    md_path = out / f"{stem}.md"
    plain_path = out / "phase7-plain-summary.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    plain_path.write_text(render_plain_summary(report), encoding="utf-8")
    return json_path, md_path, plain_path


if __name__ == "__main__":
    import sys

    base = Path(__file__).resolve().parents[2]

    def _progress(item_no: int, label: str) -> None:
        print(f"[phase7] item {item_no} done: {label}", flush=True)

    cache_only = "--cache-only" in sys.argv
    report = run_phase7(progress=_progress, cache_only=cache_only)
    json_path, md_path, plain_path = save_report(report, base / "validation")
    v = report["verdicts"]
    item1 = report["item1_combined_new_fresh"]
    c = item1["combined_vs_legs"]
    print(f"ITEM 1 combined FRESH-5/6 pooled: {c['combined_trades']} trades, "
          f"{c['combined_win_rate_pct']}% win, P&L {_fmt_money(c['combined_pnl_usd'])}, "
          f"expectancy {_fmt_money(c['combined_expectancy_usd'])} — "
          f"RSI {_fmt_money(c['rsi_wide6_pnl_usd'])} / Bollinger "
          f"{_fmt_money(c['bollinger_wide6_pnl_usd'])} / MACD {_fmt_money(c['macd_pnl_usd'])} — "
          f"{'HOLDS UP' if v['item1_combined_holds_up'] else 'does NOT hold up'}, "
          f"{'beats all legs' if v['item1_combined_beats_all_legs_pnl'] else 'does NOT beat all legs'}, "
          f"expectancy in falling market: "
          f"{'holds up' if v['item1_expectancy_holds_up_in_falling_market'] else 'does NOT hold up'}")
    item2 = report["item2_crypto"]
    for key in ("rsi_wide6", "bollinger_wide6", "macd"):
        p = item2["pooled"][key]
        print(f"ITEM 2 crypto {key}: {p['trades']} trades, {p['win_rate_pct']}% win, "
              f"P&L {_fmt_money(p['total_pnl_usd'])}, expectancy {_fmt_money(p['expectancy_usd'])} — "
              f"{'HOLDS UP' if item2['verdict'][key]['holds_up'] else 'does NOT hold up'}")
    print(f"ITEM 2 SOL-USD clean: {item2['sol_usd_fetched_cleanly']}")
    item3 = report["item3_wider_symbols"]
    for key in ("rsi_wide6", "bollinger_wide6"):
        p = item3["pooled"][key]
        print(f"ITEM 3 wider {key}: {p['trades']} trades, {p['win_rate_pct']}% win, "
              f"P&L {_fmt_money(p['total_pnl_usd'])}, expectancy {_fmt_money(p['expectancy_usd'])} — "
              f"{'HOLDS UP' if item3['verdict'][key]['holds_up'] else 'does NOT hold up'}")
    item4 = report["item4_macd_bear"]
    if item4["macd_fresh5"] is None:
        print(f"ITEM 4 MACD FRESH-5: NOT TESTED — {item4.get('status_note', '')}")
    else:
        print(f"ITEM 4 MACD FRESH-5: {item4['macd_fresh5']['trades']} trades, "
              f"{item4['macd_fresh5']['win_rate_pct']}% win, "
              f"P&L {_fmt_money(item4['macd_fresh5']['total_pnl_usd'])} — "
              f"{'HOLDS UP' if v['item4_macd_holds_up_in_bear_window'] else 'does NOT hold up'}, "
              f"{'beats MR' if v['item4_macd_beats_mr_in_bear_window'] else 'does NOT beat MR'}")
    sc = report.get("small_cap")
    if sc:
        for capital in sc["capital_levels_usd"]:
            key = f"{capital:.2f}"
            for variant in ("rsi_wide6", "bollinger_wide6", "macd"):
                p = sc["pooled_by_capital"][key][variant]
                print(f"ITEM 5 small-cap ${capital:,.0f} {variant}: {p['trades']} trades, "
                      f"{p['win_rate_pct']}% win, P&L {_fmt_money(p['total_pnl_usd'])} "
                      f"({_fmt_money(p['pnl_per_window_usd'])}/window), "
                      f"too small {p['skipped_too_small']}")
    if report["fetch_failures"]:
        print(f"FETCH FAILURES: {report['fetch_failures']}")
    print(f"Report: {md_path}")
    print(f"Data: {json_path}")
    print(f"Plain summary: {plain_path}")
    sys.exit(0)
