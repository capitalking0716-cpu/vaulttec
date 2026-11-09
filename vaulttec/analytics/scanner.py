"""Market scanner (Phase 2) — opportunity scanning across a watchlist.

Scans stocks + crypto, ranks every symbol by signal strength, and
returns the ranking with the evidence behind each rank. The scanner
never says "buy this" — it says "here is what the checks found,
strongest first, with the evidence". Ranking score = confidence
adjusted by how many checks agreed, so a high-confidence signal
backed by one check ranks below a slightly lower-confidence signal
backed by five. Neutral signals are listed last, not hidden, so the
user sees what was checked and found nothing.
"""
from __future__ import annotations

from ..market.data import SCAN_UNIVERSE, fetch_history
from .signals import generate_signal, signal_checks


def scan_symbol(symbol: str, days: int = 90, provider_name: str = "sample") -> dict:
    """Scan one symbol and return its signal, checks, score, and source."""
    history, source = fetch_history(symbol, days=days, provider_name=provider_name)
    signal = generate_signal(symbol, history)
    checks = signal_checks(symbol, history)
    agreeing = sum(c["weight"] for c in checks
                   if (signal.direction == "long" and c["side"] == "bullish")
                   or (signal.direction == "short" and c["side"] == "bearish"))
    # Score: confidence (0-0.85) plus agreement (up to 0.15) — a signal
    # backed by many checks outranks one backed by few.
    score = round(signal.confidence + min(agreeing * 0.02, 0.15), 3) if signal.direction != "neutral" else round(signal.confidence, 3)
    return {
        "symbol": symbol,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "score": score,
        "checks_agreeing": agreeing,
        "checks_total": len(checks),
        "evidence": signal.evidence,
        "source": source,  # "sample" or "yfinance" — shown honestly in the UI
        "history": history,
        "signal": signal,
    }


def scan_watchlist(symbols: list[str] | None = None, days: int = 90,
                   provider_name: str = "sample") -> list[dict]:
    """Scan a watchlist (default: the full scan universe) and return
    results ranked strongest first, neutrals last."""
    symbols = symbols or list(SCAN_UNIVERSE)
    results = [scan_symbol(s, days=days, provider_name=provider_name) for s in symbols]
    results.sort(key=lambda r: (r["direction"] != "neutral", r["score"]), reverse=True)
    return results


def top_opportunities(symbols: list[str] | None = None, limit: int = 5,
                      min_confidence: float = 0.55,
                      provider_name: str = "sample") -> list[dict]:
    """The strongest non-neutral opportunities, above a confidence floor.
    Returns at most ``limit`` — an empty list is a valid, honest answer
    ('nothing cleared the bar today')."""
    return [r for r in scan_watchlist(symbols, provider_name=provider_name)
            if r["direction"] != "neutral" and r["confidence"] >= min_confidence][:limit]
