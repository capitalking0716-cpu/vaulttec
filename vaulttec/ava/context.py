"""App context snapshot for Ava — the app's current state as plain data.

Ava's brief, chat and trade check all answer from this snapshot, so
it is built once per Results view and passed in. It is plain data
only: no trading, no sending, no secrets, no live anything.

This used to live in the Shadow bridge module. Shadow (the tab and
the bridge) is gone — Ava is the in-app AI now — but Ava still needs
the same snapshot of the app, so the builder moved here with her.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime


def _field(obj, name, default=None):
    """Read a field off a dataclass, object or dict, without crashing."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _signal_to_dict(signal) -> dict:
    if isinstance(signal, dict):
        return {
            "symbol": str(signal.get("symbol", "")).upper(),
            "direction": signal.get("direction", "neutral"),
            "confidence": _f(signal.get("confidence", 0)),
            "evidence": signal.get("evidence", ""),
        }
    if is_dataclass(signal):
        data = asdict(signal)
        return {
            "symbol": str(data.get("symbol", "")).upper(),
            "direction": data.get("direction", "neutral"),
            "confidence": _f(data.get("confidence", 0)),
            "evidence": data.get("evidence", ""),
        }
    return {
        "symbol": str(_field(signal, "symbol", "")).upper(),
        "direction": _field(signal, "direction", "neutral"),
        "confidence": _f(_field(signal, "confidence", 0)),
        "evidence": _field(signal, "evidence", ""),
    }


def build_context_snapshot(profile, portfolio, engine, signals, prices,
                           cash: float, value: float, pnl: float) -> dict:
    """Plain snapshot of the app's current state, for Ava.

    Shape — the consumers read exactly this:
    - ``user``: the profile (name, goal, risk tolerance, limits).
    - ``portfolio``: ``cash`` / ``value`` / ``pnl`` (paper dollars).
    - ``holdings``: one dict per holding, with the current price.
    - ``open_trades``: open paper trades only, with entry/stop/target.
    - ``signals``: today's signals as plain dicts.
    - ``generated_at``: when the snapshot was built.
    """
    holdings = []
    raw_holdings = _field(portfolio, "holdings", {}) or {}
    items = raw_holdings.items() if isinstance(raw_holdings, dict) else []
    for symbol, holding in items:
        avg_cost = _f(_field(holding, "avg_cost", 0))
        current = _f((prices or {}).get(symbol, avg_cost), avg_cost)
        holdings.append({
            "symbol": str(symbol).upper(),
            "quantity": _f(_field(holding, "quantity", 0)),
            "avg_cost": avg_cost,
            "current_price": current,
        })

    open_trades = []
    for trade in _field(engine, "trades", []) or []:
        if str(_field(trade, "status", "open")) != "open":
            continue
        open_trades.append({
            "symbol": str(_field(trade, "symbol", "")).upper(),
            "side": _field(trade, "side", "buy"),
            "quantity": _f(_field(trade, "quantity", 0)),
            "price": _f(_field(trade, "price", 0)),
            "stop_loss": _f(_field(trade, "stop_loss", 0)),
            "take_profit": _f(_field(trade, "take_profit", 0)),
            "reason": _field(trade, "reason", ""),
            "source": _field(trade, "source", "manual"),
            "status": _field(trade, "status", "open"),
            "created_at": _field(trade, "created_at", ""),
        })

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "user": {
            "name": _field(profile, "name", ""),
            "goal": _field(profile, "goal", ""),
            "risk_tolerance": _field(profile, "risk_tolerance", "balanced"),
            "virtual_capital": _f(_field(profile, "virtual_capital", 0)),
            "max_position_pct": _f(_field(profile, "max_position_pct", 0)),
            "daily_loss_limit_pct": _f(_field(profile, "daily_loss_limit_pct", 0)),
            "allowed_markets": _field(profile, "allowed_markets", []) or [],
            "automation_enabled": bool(_field(profile, "automation_enabled", False)),
        },
        "portfolio": {
            "cash": _f(cash),
            "value": _f(value),
            "pnl": _f(pnl),
        },
        "holdings": holdings,
        "open_trades": open_trades,
        "signals": [_signal_to_dict(s) for s in (signals or [])],
    }
