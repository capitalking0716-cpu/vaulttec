"""Ava's paper trading — she practices OUR strategy with fake money.

Paper only, always. Ava implements the validated strategy — wide-6
mean-reversion (RSI + Bollinger, 6% stop / 9% target, 1.5:1, 10-day
exit) with MACD trend-following as the complement, one shared pot —
from the scanner signals under those exact rules. She does NOT
invent her own strategy and never freelances entries: the entry
rule is the same combined-run rule (mean-reversion on a 5-day grid,
MACD on every bar, at most one trade per symbol per day), and each
trade is annotated with the scanner's own signal (confidence +
evidence) from the same history.

She never places a live trade and never touches the live locks:
the trader refuses to run if VAULTTEC_LIVE_TRADING_ENABLED is true
or ALPACA_PAPER is false.

Every trade goes through the real PaperTradingEngine + Risk Engine.
One evidence record per trade is written to data/ava-evidence.jsonl
(local only, never pushed): symbol, signal + confidence, entry,
stop, target, position size, risk in dollars, her plain-language
reasoning, timestamp, and the outcome once the trade closes.
Blocked trades are logged with the reason. On every close she
learns one lesson via lessons.learn_from_trade.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from ..analytics.exit_test import WINDOW_STEP_DAYS, _exit_trade_exit
from ..analytics.mean_reversion import (
    STRATEGIES,
    mean_reversion_trigger,
    trade_start_index,
)
from ..analytics.signals import generate_signal
from ..analytics.trend_and_stress import trend_trigger
from ..analytics.win_rate import WIDE6
from ..config.settings import RISK_PROFILES
from ..db.models import UserProfile
from ..market.indicators import trend as trend_direction
from ..paper_trading import PaperTradingEngine
from ..portfolio.manager import Portfolio
from ..risk import RiskEngine
from .lessons import learn_from_trade


def assert_paper_only() -> None:
    """Refuse to run unless this is paper trading. Live is never
    Ava's business — if either live lock is flipped, she stops."""
    live_enabled = os.environ.get("VAULTTEC_LIVE_TRADING_ENABLED", "").strip().lower() == "true"
    paper_off = os.environ.get("ALPACA_PAPER", "true").strip().lower() == "false"
    if live_enabled or paper_off:
        raise RuntimeError(
            "Ava paper trading refused: live trading is enabled "
            "(VAULTTEC_LIVE_TRADING_ENABLED=true or ALPACA_PAPER=false). "
            "Ava trades paper only and never touches the live locks.")


def evidence_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "ava-evidence.jsonl"


def load_evidence(limit: int = 20) -> list[dict]:
    """Most recent evidence records, newest first. Empty when none."""
    path = evidence_path()
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:][::-1]


class AvaPaperTrader:
    """Ava paper-trading OUR strategy on one shared pot.

    Same method as the Phase 6 combined run, same exits, same Risk
    Engine, balanced profile — plus Ava's reasoning, one evidence
    record per trade, and one lesson per close."""

    def __init__(self, starting_cash: float = 100.0,
                 risk_profile: str = "balanced",
                 evidence_file: str | Path | None = None):
        assert_paper_only()
        self.starting_cash = starting_cash
        self.risk_profile = risk_profile
        self._evidence_path = Path(evidence_file) if evidence_file is not None else evidence_path()
        limits = RISK_PROFILES[risk_profile]
        self.profile = UserProfile(
            risk_tolerance=risk_profile,
            max_position_pct=limits["max_position_pct"],
            daily_loss_limit_pct=limits["daily_loss_limit_pct"],
            allowed_markets=["stocks", "crypto"])
        self.risk = RiskEngine(
            max_position_pct=limits["max_position_pct"],
            max_concentration_pct=limits["max_concentration_pct"],
            max_exposure_pct=limits["max_exposure_pct"],
            daily_loss_limit_pct=limits["daily_loss_limit_pct"],
            min_risk_reward=limits["min_risk_reward"])
        self.portfolio = Portfolio(cash=starting_cash)
        self.engine = PaperTradingEngine(self.portfolio, self.risk)
        self.evidence: list[dict] = []
        self.lessons: list[dict] = []
        self.counts: Counter = Counter()
        self.counts["too_small_by_symbol"] = Counter()
        self.counts["blocked_reasons"] = Counter()
        self.counts["per_symbol"] = Counter()
        self.counts["per_source"] = Counter()

    def _write_evidence(self, record: dict) -> None:
        self.evidence.append(record)
        path = self._evidence_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    def _reasoning(self, *, symbol: str, source: str, entry: float,
                   stop: float, take: float, quantity: float,
                   risk_usd: float, scanner, trend_now: str) -> str:
        """Risk first, in plain language: the case against the trade,
        then the case for it. Every number is real — nothing invented."""
        position_usd = round(entry * quantity, 2)
        reward_usd = round((take - entry) * quantity, 2)
        risk_pct = round(risk_usd / self.portfolio.value({symbol: entry}) * 100, 2) \
            if self.portfolio.value({symbol: entry}) else 0.0
        against = (
            f"Against first: if this hits the stop I lose ${risk_usd:.2f} "
            f"({risk_pct:.1f}% of the pot) on a ${position_usd:.2f} position, "
            f"and the short-term trend is {trend_now} — a bounce is possible, "
            "never promised, and a stop that gets hit is the stop doing its job."
        )
        for_case = (
            f"For: the {source} signal fired under our wide-6 rules "
            f"(scanner confidence {scanner.confidence:.0%}: {scanner.evidence}); "
            f"stop ${stop:.2f} and target ${take:.2f} are set, so a win pays "
            f"about ${reward_usd:.2f}. Small size, planned loss, no chasing."
        )
        return f"{against} {for_case}"

    def run_window(self, label: str, histories: dict, window_start: str | None = None,
                   symbols: list[str] | None = None) -> dict:
        """Run OUR strategy on one window's histories. Same loop as
        the Phase 6 combined run — RSI + Bollinger wide-6 on a 5-day
        grid, MACD on every bar, one shared pot, at most one trade
        per symbol per day. Returns the window summary."""
        assert_paper_only()
        before = {
            "signals_seen": self.counts["signals_seen"],
            "blocked_by_risk": self.counts["blocked_by_risk"],
            "skipped_too_small": self.counts["skipped_too_small"],
            "too_small_by_symbol": dict(self.counts["too_small_by_symbol"]),
            "lessons": len(self.lessons),
            "evidence": len(self.evidence),
        }
        symbols = [s for s in (symbols or list(histories)) if s in histories]
        trade_rows: list[dict] = []
        equity = [self.starting_cash]
        for symbol in symbols:
            history = histories[symbol].reset_index(drop=True)
            start_idx = (trade_start_index(history, window_start)
                         if window_start else 60)
            for start in range(start_idx, len(history) - WIDE6.horizon_days, 1):
                self.counts["windows_checked"] += 1
                window_history = history.iloc[: start + 1].reset_index(drop=True)
                candidates: list[str] = []
                if (start - start_idx) % WINDOW_STEP_DAYS == 0:
                    for strategy in STRATEGIES:
                        if mean_reversion_trigger(strategy, window_history):
                            self.counts["signals_seen"] += 1
                            candidates.append(strategy)
                if trend_trigger("macd", window_history):
                    self.counts["signals_seen"] += 1
                    candidates.append("macd")
                if not candidates:
                    continue
                if symbol in self.portfolio.holdings:
                    self.counts["skipped_already_in_position"] += 1
                    continue
                placed = False
                for source_strategy in candidates:
                    if placed:
                        self.counts["skipped_same_day_double"] += 1
                        continue
                    entry = float(history.iloc[start]["close"])
                    stop = round(entry * (1 - WIDE6.stop_pct), 2)
                    take = math.ceil((entry + 1.5 * (entry - stop)) * 100) / 100
                    raw_qty = self.risk.position_size(
                        self.portfolio.value({symbol: entry}), entry)
                    quantity = math.floor(raw_qty * 10000) / 10000
                    if quantity <= 0:
                        self.counts["skipped_too_small"] += 1
                        self.counts["too_small_by_symbol"][symbol] += 1
                        self._write_evidence({
                            "when": datetime.utcnow().isoformat(),
                            "window": label,
                            "symbol": symbol,
                            "signal": source_strategy,
                            "status": "blocked",
                            "block_reason": (
                                f"Too small: a {self.starting_cash:.0f}-dollar pot "
                                f"sizes to 0.0000 of {symbol} at ${entry:,.2f} "
                                "(10% position cap, quantity floored to 4 decimals) — "
                                "the trade could not be sized, so it was not placed."),
                            "entry": entry,
                        })
                        continue
                    scanner = generate_signal(symbol, window_history)
                    risk_usd = round((entry - stop) * quantity, 2)
                    trend_now = trend_direction(window_history["close"])
                    reasoning = self._reasoning(
                        symbol=symbol, source=source_strategy, entry=entry,
                        stop=stop, take=take, quantity=quantity,
                        risk_usd=risk_usd, scanner=scanner, trend_now=trend_now)
                    self.engine.realised_pnl = 0.0
                    trade = self.engine.place_order(
                        symbol, "buy", quantity, entry, stop, take,
                        reason=f"{source_strategy} trigger, Ava paper wide-6",
                        source="ava-paper")
                    if trade is None:
                        reasons = list(self.engine.blocked[-1]["reasons"])
                        self.counts["blocked_by_risk"] += 1
                        for reason in reasons:
                            self.counts["blocked_reasons"][
                                re.sub(r"\$[\d,]+\.\d{2}", "$X", reason)] += 1
                        self._write_evidence({
                            "when": datetime.utcnow().isoformat(),
                            "window": label,
                            "symbol": symbol,
                            "signal": source_strategy,
                            "confidence": round(scanner.confidence, 3),
                            "status": "blocked",
                            "block_reason": "; ".join(reasons),
                            "entry": entry,
                            "stop": stop,
                            "target": take,
                            "position_size_usd": round(entry * quantity, 2),
                            "risk_usd": risk_usd,
                            "reasoning": reasoning,
                        })
                        continue
                    exit_price, exit_reason, days_held = _exit_trade_exit(
                        history, start, entry, stop, take, WIDE6.horizon_days,
                        "rsi", False)
                    pnl = self.engine.close_position(symbol, exit_price, exit_reason)
                    pnl = 0.0 if pnl is None else round(pnl, 2)
                    equity.append(round(self.portfolio.cash, 2))
                    row = {
                        "symbol": symbol, "source_strategy": source_strategy,
                        "entry": entry, "exit": exit_price,
                        "quantity": quantity, "stop_loss": stop, "take_profit": take,
                        "exit_reason": exit_reason, "days_held": days_held,
                        "pnl_usd": pnl,
                    }
                    trade_rows.append(row)
                    self.counts["per_symbol"][symbol] += 1
                    self.counts["per_source"][source_strategy] += 1
                    placed = True
                    self._write_evidence({
                        "when": datetime.utcnow().isoformat(),
                        "window": label,
                        "symbol": symbol,
                        "signal": source_strategy,
                        "confidence": round(scanner.confidence, 3),
                        "scanner_evidence": scanner.evidence,
                        "status": "placed",
                        "entry": entry,
                        "stop": stop,
                        "target": take,
                        "position_size": quantity,
                        "position_size_usd": round(entry * quantity, 2),
                        "risk_usd": risk_usd,
                        "reasoning": reasoning,
                        "exit": exit_price,
                        "exit_reason": exit_reason,
                        "days_held": days_held,
                        "pnl_usd": pnl,
                        "won": pnl > 0,
                    })
                    closed = self.engine.trades[-1]
                    lesson = learn_from_trade(closed)
                    if lesson:
                        self.lessons.append(lesson)
        wins = [t for t in trade_rows if t["pnl_usd"] > 0]
        total_pnl = round(sum(t["pnl_usd"] for t in trade_rows), 2)
        trades = len(trade_rows)
        too_small_delta = {
            s: self.counts["too_small_by_symbol"][s] - before["too_small_by_symbol"].get(s, 0)
            for s in self.counts["too_small_by_symbol"]
            if self.counts["too_small_by_symbol"][s] - before["too_small_by_symbol"].get(s, 0) > 0
        }
        return {
            "window": label,
            "starting_cash_usd": self.starting_cash,
            "strategy": "Ava paper — OUR wide-6 (RSI + Bollinger) + MACD, one shared pot",
            "trades_placed": trades,
            "signals_seen": self.counts["signals_seen"] - before["signals_seen"],
            "wins": len(wins),
            "losses": trades - len(wins),
            "win_rate_pct": round(len(wins) / trades * 100, 1) if trades else 0.0,
            "total_pnl_usd": total_pnl,
            "total_pnl_cents": int(round(total_pnl * 100)),
            "expectancy_usd": round(total_pnl / trades, 2) if trades else 0.0,
            "blocked_by_risk": self.counts["blocked_by_risk"] - before["blocked_by_risk"],
            "skipped_too_small": self.counts["skipped_too_small"] - before["skipped_too_small"],
            "too_small_by_symbol": too_small_delta,
            "lessons_learned": len(self.lessons) - before["lessons"],
            "evidence_records": len(self.evidence) - before["evidence"],
            "trades": trade_rows,
        }


def run_ava_paper_simulation(windows: list[tuple[str, str, dict]],
                             starting_cash: float = 100.0,
                             evidence_path: str | Path | None = None) -> dict:
    """Run Ava's paper trading across windows. Each window starts
    fresh with the same cash (separate pots — same as the Phase 7
    small-cap method), so her results compare directly with the
    $100 small-cap runs. Returns pooled results plus per-window
    summaries, her evidence records, and her lessons."""
    assert_paper_only()
    per_window: list[dict] = []
    all_evidence: list[dict] = []
    all_lessons: list[dict] = []
    for label, start, histories in windows:
        trader = AvaPaperTrader(starting_cash=starting_cash,
                                evidence_file=evidence_path)
        summary = trader.run_window(label, histories, window_start=start)
        per_window.append(summary)
        all_evidence.extend(trader.evidence)
        all_lessons.extend(trader.lessons)
    trades = sum(s["trades_placed"] for s in per_window)
    wins = sum(s["wins"] for s in per_window)
    pnl = round(sum(s["total_pnl_usd"] for s in per_window), 2)
    return {
        "starting_cash_usd": starting_cash,
        "windows_run": [s["window"] for s in per_window],
        "trades_placed": trades,
        "wins": wins,
        "losses": trades - wins,
        "win_rate_pct": round(wins / trades * 100, 1) if trades else 0.0,
        "total_pnl_usd": pnl,
        "total_pnl_cents": int(round(pnl * 100)),
        "pnl_per_window_usd": round(pnl / len(per_window), 2) if per_window else 0.0,
        "expectancy_usd": round(pnl / trades, 2) if trades else 0.0,
        "blocked_by_risk": sum(s["blocked_by_risk"] for s in per_window),
        "skipped_too_small": sum(s["skipped_too_small"] for s in per_window),
        "lessons_learned": len(all_lessons),
        "evidence_records": len(all_evidence),
        "per_window": per_window,
        "lessons": all_lessons,
    }
