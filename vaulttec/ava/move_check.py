"""Check My Move — Ava looks at the trade Neko is about to make
*before* he makes it, and tells him straight whether it is a good
play, a bad play, or a play to fix first.

Ava argues against a trade before she argues for it. She checks the
move against, in order:

1. The wide-6 rules — is this actually a wide-6 setup (RSI < 30 or
   price at the Bollinger lower band), or is he chasing a move that
   already happened?
2. The risk limits — stop-loss present and on the right side,
   position size inside the profile cap, concentration and total
   exposure inside the limits, risk/reward at least 1.5:1, daily
   loss limit not already hit.
3. His current open paper positions (live_paper state + the app's
   open trades) — is he doubling down on a name he already holds?
4. The private panel proposals (pending) — is there already a
   proposal for this symbol?
5. Her lessons from closed trades — a mistake made once gets raised
   before the same setup is traded again.
6. The small-win rule — a tight 9% target beats holding out for a
   home run; a stop wider than 6% is a fix, not a feature.

She advises only. She NEVER places a trade, never promises a profit,
no leverage, no options, paper first. The verdict is plain language:
"good" (make it, if you want it), "fix" (change this first, then it
is a trade), "bad" (do not make this play). Neko decides YES or NO
on everything.

Everything here works with no API key — it is pure logic on real
app data. When the brain is online the same verdict goes through
the LLM for flavour; the verdict itself never changes.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import pandas as pd

from ..config.settings import RISK_PROFILES
from ..live_paper_trading import STOP_PCT, TAKE_PCT, _live_trigger
from ..market.indicators import bollinger_bands, rsi
from ..risk import RiskEngine

# Words in Neko's own description of the setup that mean a trade we
# never take. Whole-word match only, so "I have no other option"
# does not trip it — "options" does.
FORBIDDEN_WORDS = ("leverage", "leveraged", "margin", "options",
                   "puts", "calls")

# A target this far above the entry is holding out for a home run,
# not banking a small win. Wide-6 targets 9%.
HOME_RUN_PCT = 0.15

# A gain at least this far toward the 9% target counts as a small
# win worth banking when Neko asks about selling.
SMALL_WIN_PCT = 0.045


def wide6_stop(entry: float) -> float:
    """The wide-6 stop for an entry: 6% below it."""
    return round(entry * (1 - STOP_PCT), 2)


def wide6_target(entry: float) -> float:
    """The wide-6 target for an entry: 9% above it, rounded up to
    the cent so the 1.5:1 minimum always holds."""
    stop = wide6_stop(entry)
    return math.ceil((entry + 1.5 * (entry - stop)) * 100) / 100


def load_live_paper_positions(project_root: str | Path) -> list[dict]:
    """Open paper positions from live_paper/state.json (the durable
    daily paper pot). Read-only. Returns [] when the file is missing
    or unreadable — no positions are invented."""
    path = Path(project_root) / "live_paper" / "state.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — missing/bad state: no positions
        return []
    last_close = state.get("last_close", {}) or {}
    positions = []
    for pos in state.get("open_positions", []) or []:
        positions.append({
            "symbol": pos.get("symbol"),
            "entry_price": float(pos.get("entry_price", 0) or 0),
            "quantity": float(pos.get("quantity", 0) or 0),
            "stop_loss": float(pos.get("stop_loss", 0) or 0),
            "take_profit": float(pos.get("take_profit", 0) or 0),
            "bars_held": int(pos.get("bars_held", 0) or 0),
            "strategy": pos.get("strategy", "wide-6"),
            "current_price": float(last_close.get(pos.get("symbol"), 0) or 0) or None,
            "source": "live_paper",
        })
    return positions


def load_private_proposals(project_root: str | Path) -> list[dict]:
    """Pending proposals from the private panel (Neko only,
    paper-first, approval-first). Read-only. Returns [] when the
    file is missing or unreadable."""
    path = Path(project_root) / "vaulttec" / "private_live" / "proposals.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — missing/bad file: no proposals
        return []
    return [r for r in (rows or []) if r.get("status") == "pending"]


def _setup_readings(history: pd.DataFrame | None) -> dict:
    """What the recent daily bars say about a wide-6 setup. Returns
    the numbers Ava quotes, and which strategy (if any) fires on the
    last completed bar. ``unknown`` when there is no usable history
    — a fetch failure is reported, never replaced with sample data."""
    if history is None or len(history) < 21 or "close" not in history.columns:
        return {"status": "unknown", "rsi": None, "lower_band": None,
                "close": None, "fired": None}
    closes = history["close"].reset_index(drop=True)
    rsi_value = rsi(closes).iloc[-1]
    bands = bollinger_bands(closes)
    lower = bands["lower"].iloc[-1]
    close = float(closes.iloc[-1])
    fired = None
    for strategy in ("rsi", "bollinger"):
        try:
            if _live_trigger(strategy, history):
                fired = strategy
                break
        except Exception:  # noqa: BLE001 — a bad history must not crash the check
            continue
    return {
        "status": "known",
        "rsi": None if pd.isna(rsi_value) else round(float(rsi_value), 1),
        "lower_band": None if pd.isna(lower) else round(float(lower), 2),
        "close": close,
        "fired": fired,
    }


def _matching_lessons(lessons: list[dict] | None, symbol: str) -> list[dict]:
    """Lessons from closed trades on this symbol, newest first."""
    if not lessons:
        return []
    return [lesson for lesson in lessons
            if str(lesson.get("symbol", "")).upper() == symbol.upper()][:2]


def check_move(move: dict, context: dict, history: pd.DataFrame | None = None,
               lessons: list[dict] | None = None,
               live_positions: list[dict] | None = None,
               pending_proposals: list[dict] | None = None) -> dict:
    """Check the move Neko is about to make. Returns a verdict dict
    with ``verdict`` ("good" | "fix" | "bad"), a plain-language
    headline, the reasons, what to change, and the wide-6 numbers.

    ``move``: symbol, side ("buy"/"sell"), quantity, entry_price,
    stop_loss (None when he has none), take_profit (None when he
    has none), setup (free text, optional).
    ``context``: portfolio_value, cash, open_trades (from the app
    snapshot), holdings (with current_price), risk_tolerance.
    ``history``: recent daily bars for the symbol (last completed
    bars only). None when prices could not be fetched — the setup
    is then "unknown" and the verdict is capped at "fix".
    """
    symbol = str(move.get("symbol", "")).strip().upper()
    side = str(move.get("side", "buy")).strip().lower()
    quantity = float(move.get("quantity") or 0)
    entry = float(move.get("entry_price") or 0)
    stop = move.get("stop_loss")
    stop = float(stop) if stop else None
    target = move.get("take_profit")
    target = float(target) if target else None
    setup_text = str(move.get("setup", "") or "")

    portfolio_value = float(context.get("portfolio_value", 0) or 0)
    if portfolio_value <= 0:
        # The app snapshot nests the money under context["portfolio"].
        nested = context.get("portfolio", {}) or {}
        portfolio_value = (float(nested.get("value", 0) or 0)
                           or float(nested.get("cash", 0) or 0))
    if portfolio_value <= 0:
        portfolio_value = float(context.get("cash", 0) or 0)
    held_positions = []
    for trade in context.get("open_trades", []) or []:
        held_positions.append({
            "symbol": str(trade.get("symbol", "")).upper(),
            "entry_price": float(trade.get("price", 0) or 0),
            "quantity": float(trade.get("quantity", 0) or 0),
            "stop_loss": float(trade.get("stop_loss", 0) or 0),
            "take_profit": float(trade.get("take_profit", 0) or 0),
            "source": "app",
        })
    for pos in (live_positions or []):
        if not any(p["symbol"] == pos["symbol"] for p in held_positions):
            held_positions.append(pos)
    current_prices = {}
    for holding in context.get("holdings", []) or []:
        price = float(holding.get("current_price", 0) or 0)
        if price > 0:
            current_prices[str(holding.get("symbol", "")).upper()] = price
    for pos in (live_positions or []):
        if pos.get("current_price"):
            current_prices.setdefault(pos["symbol"], float(pos["current_price"]))

    limits = RISK_PROFILES.get(
        str(context.get("risk_tolerance")
            or (context.get("user", {}) or {}).get("risk_tolerance")
            or "balanced"),
        RISK_PROFILES["balanced"])
    risk = RiskEngine(
        max_position_pct=limits["max_position_pct"],
        max_concentration_pct=limits["max_concentration_pct"],
        max_exposure_pct=limits["max_exposure_pct"],
        daily_loss_limit_pct=limits["daily_loss_limit_pct"],
        min_risk_reward=limits["min_risk_reward"])

    reasons: list[str] = []
    changes: list[str] = []
    verdict = "good"
    setup_status = "unknown"
    fired_strategy = None

    def flag_bad(reason: str, change: str = ""):
        nonlocal verdict
        verdict = "bad"
        reasons.append(reason)
        if change:
            changes.append(change)

    def flag_fix(reason: str, change: str = ""):
        nonlocal verdict
        if verdict == "good":
            verdict = "fix"
        reasons.append(reason)
        if change:
            changes.append(change)

    # --- The move has to be describable at all ----------------------------
    if not symbol:
        return _verdict("bad", "Which symbol? I need a symbol before I can check anything.",
                        ["No symbol given."], [], move, context, None, None, [], stop, target)
    if side not in ("buy", "sell"):
        return _verdict("bad", "Buy or sell — pick one. I can't check a move without a side.",
                        ["Side must be 'buy' or 'sell'."], [], move, context, None, None, [], stop, target)
    if entry <= 0 or quantity <= 0:
        return _verdict("bad", "I need a real entry price and a real share count — neither can be zero.",
                        ["Entry price and quantity must both be positive."],
                        ["Put in the price you'd actually buy at, and how many shares."],
                        move, context, None, None, [], stop, target)

    # --- Forbidden trades: leverage and options are never our game --------
    words = set(re.findall(r"[a-z]+", setup_text.lower()))
    hit = words & set(FORBIDDEN_WORDS)
    if hit:
        flag_bad(
            f"You mentioned {', '.join(sorted(hit))} — we don't trade those. "
            "No leverage, no options, ever.",
            "Drop the leverage and the options. Shares only, small size, planned stop.")

    # --- Sells: an exit, not a new trade ----------------------------------
    held = next((p for p in held_positions if p["symbol"] == symbol), None)
    if side == "sell":
        if held is None:
            flag_bad(
                f"You don't hold {symbol} — selling it would be shorting, and "
                "we don't short. Long-only is the rule.",
                f"Don't sell {symbol} unless you hold it. If you want in, that's a buy, not a sell.")
        else:
            current = current_prices.get(symbol)
            if current is None:
                flag_fix(
                    f"I can't see the current price for {symbol} right now, so I "
                    "can't tell whether selling now banks a win or cuts a loss. "
                    "Don't sell blind.",
                    f"Get a current price for {symbol} first, then check the move again.")
            else:
                gain_pct = (current - held["entry_price"]) / held["entry_price"] if held["entry_price"] else 0
                gain_usd = (current - held["entry_price"]) * held["quantity"]
                target_gain = (held["take_profit"] - held["entry_price"]) if held["take_profit"] else 0
                if current <= held["stop_loss"]:
                    reasons.append(
                        f"{symbol} is at ${current:,.2f}, past your stop of "
                        f"${held['stop_loss']:,.2f}. Cut it now — the stop already said so, "
                        "and waiting only makes the loss bigger.")
                    changes.append(f"Sell {symbol} now, at ${current:,.2f}. Don't wait for a bounce.")
                elif target_gain > 0 and gain_usd >= 0.5 * target_gain * held["quantity"]:
                    reasons.append(
                        f"You're up ${gain_usd:,.2f} ({gain_pct:+.1%}) on {symbol} — that's a "
                        "small win in hand. Bank it. A banked win beats a target that never comes.")
                    changes.append(f"Sell {symbol} and bank the ${gain_usd:,.2f}.")
                elif gain_usd > 0:
                    flag_fix(
                        f"You're up ${gain_usd:,.2f} on {symbol} — a win, just a thin one. "
                        "If you're out, be out for a reason, not nerves.",
                        "Decide why you're selling. If it's just nerves, hold to the plan — "
                        "stop and target are already set.")
                else:
                    flag_fix(
                        f"You're down ${abs(gain_usd):,.2f} on {symbol} and your stop "
                        f"(${held['stop_loss']:,.2f}) hasn't hit yet. Cutting now is fear, "
                        "not a plan — the stop exists so you don't have to decide in the red.",
                        "Hold to your stop, or cut deliberately and own the loss. Don't drift.")
        return _finish(verdict, move, context, reasons, changes, "unknown", None,
                       _matching_lessons(lessons, symbol), held_positions,
                       stop, target, entry, quantity)

    # --- Buys: stop first — no stop, no trade ------------------------------
    if stop is None:
        flag_bad(
            "No stop, no trade. That's my first rule and it doesn't bend — "
            "a trade without a stop is a hope, not a plan.",
            f"Set the stop at ${wide6_stop(entry):,.2f} (6% below your entry) before you buy.")
    elif stop >= entry:
        flag_bad(
            f"Your stop (${stop:,.2f}) is above your entry (${entry:,.2f}) — "
            "that stop would fire the moment you buy.",
            f"Move the stop below your entry — wide-6 says ${wide6_stop(entry):,.2f}.")
    if target is not None and target <= entry:
        flag_fix(
            f"Your target (${target:,.2f}) is below your entry — that pays you "
            "for losing. A target has to be above the price you buy at.",
            f"Move the target above your entry — wide-6 says ${wide6_target(entry):,.2f}.")

    # --- Risk limits, through the same engine the paper trades use --------
    current_exposure = sum(
        p["quantity"] * current_prices.get(p["symbol"], p["entry_price"])
        for p in held_positions)
    holding_value = 0.0
    if held is not None:
        holding_value = held["quantity"] * current_prices.get(symbol, held["entry_price"])
    daily_pnl_pct = float(context.get("daily_pnl_pct", 0) or 0)
    check = risk.check_order(
        symbol=symbol, price=entry, quantity=quantity, stop_loss=stop,
        take_profit=target, portfolio_value=portfolio_value,
        current_exposure=current_exposure, holding_value=holding_value,
        daily_pnl_pct=daily_pnl_pct, side="buy")
    for reason in check.reasons:
        if reason.startswith("No stop-loss"):
            continue  # already flagged above, in my own words
        flag_fix(reason, _change_for_reason(reason, check, entry, quantity))

    # --- The setup: is this actually a wide-6 trade, or a chase? ----------
    readings = _setup_readings(history)
    setup_status = readings["status"]
    fired_strategy = readings["fired"]
    if readings["status"] == "unknown":
        flag_fix(
            "I couldn't check the setup — no recent prices for "
            f"{symbol} loaded, so I can't tell whether the RSI or the "
            "Bollinger trigger is actually firing. I'm judging the risk "
            "only, and I won't bless a trade I can't see.",
            "Wait for prices to load, then check again. Don't buy blind.")
    else:
        rsi_value = readings["rsi"]
        if fired_strategy == "rsi":
            reasons.append(
                f"The setup is real: RSI is {rsi_value} — under 30, oversold, "
                "the bounce we trade. That's a wide-6 entry.")
        elif fired_strategy == "bollinger":
            reasons.append(
                f"The setup is real: price is at the Bollinger lower band "
                f"(${readings['lower_band']:,.2f}) — the bounce we trade. "
                "That's a wide-6 entry.")
        else:
            rsi_text = f"RSI {rsi_value}" if rsi_value is not None else "RSI not defined yet"
            flag_fix(
                f"This isn't a wide-6 setup. {rsi_text}, and the price "
                f"(${readings['close']:,.2f}) is not at the lower band "
                f"(${readings['lower_band']:,.2f}) — you'd be buying after the move, "
                "chasing it, not catching the bounce.",
                "Wait for the trigger: RSI under 30, or price at the lower band. "
                "If it never comes, the trade never comes.")

    # --- Already holding this name? -----------------------------------------
    if held is not None:
        reasons.append(
            f"You already hold {symbol} — ${holding_value:,.2f} in it. "
            "This buy doubles down on the same name. Make sure that's a "
            "decision, not a habit.")

    # --- Pending private proposal for the same symbol -----------------------
    for prop in (pending_proposals or []):
        if str(prop.get("symbol", "")).upper() == symbol:
            reasons.append(
                f"There's already a pending private proposal for {symbol} "
                f"({prop.get('proposal_id', 'no id')}): entry "
                f"${float(prop.get('entry_price', 0)):,.2f}, stop "
                f"${float(prop.get('stop_loss', 0)):,.2f}, target "
                f"${float(prop.get('take_profit', 0)):,.2f}. Decide on that one "
                "first — don't stack a second plan on the same name.")

    # --- The small-win rule: tight target, tight stop ----------------------
    if target is not None and target > entry * (1 + HOME_RUN_PCT):
        flag_fix(
            f"Your target is ${target:,.2f} — {((target / entry) - 1):+.0%} above your entry. "
            "That's holding out for a home run. Our game is banking the small win: "
            f"9% (${wide6_target(entry):,.2f}) and moving on.",
            f"Bring the target down to ${wide6_target(entry):,.2f}. Bank the small win.")
    if stop is not None and stop < entry * (1 - STOP_PCT) - 0.01:
        flag_fix(
            f"Your stop (${stop:,.2f}) is wider than the wide-6 stop "
            f"(${wide6_stop(entry):,.2f}) — that makes the planned loss bigger "
            "than it needs to be.",
            f"Tighten the stop to ${wide6_stop(entry):,.2f}.")
    if target is None and verdict != "bad":
        changes.append(f"Set the target at ${wide6_target(entry):,.2f} (9% — the small win).")
        reasons.append(
            f"No target set — wide-6 says ${wide6_target(entry):,.2f}. "
            "A trade with no target is a trade with no plan to bank the win.")

    matched = _matching_lessons(lessons, symbol)
    return _finish(verdict, move, context, reasons, changes, setup_status,
                   fired_strategy, matched, held_positions,
                   stop, target, entry, quantity)


def _change_for_reason(reason: str, check, entry: float, quantity: float) -> str:
    """A concrete fix for a risk-engine reason, in plain language."""
    if "Risk/reward" in reason:
        return (f"Fix the ratio: stop ${check.suggested_stop_loss:,.2f}, "
                f"target ${check.suggested_take_profit:,.2f} — that gets you 1.5:1.")
    if "Position" in reason:
        return (f"Shrink it to {check.max_quantity:.4f} shares or fewer "
                f"(${check.max_quantity * entry:,.2f} at your entry).")
    if "concentration" in reason:
        return "Too much in one name already — sell some of the holding first, or skip this buy."
    if "exposure" in reason:
        return "The pot is too full — close or skip something else before adding more."
    if "Daily loss limit" in reason:
        return "Stop for today. Come back tomorrow with a clear head."
    return ""


def _finish(verdict, move, context, reasons, changes, setup_status,
           fired_strategy, lessons_applied, open_positions,
           stop, target, entry, quantity) -> dict:
    """Assemble the verdict dict, with the wide-6 numbers attached."""
    is_sell = str(move.get("side", "buy")).strip().lower() == "sell"
    risk_usd = None
    if not is_sell and stop is not None and entry:
        risk_usd = round(abs(entry - stop) * quantity, 2)
    portfolio_value = float(context.get("portfolio_value", 0) or 0)
    if portfolio_value <= 0:
        nested = context.get("portfolio", {}) or {}
        portfolio_value = (float(nested.get("value", 0) or 0)
                           or float(nested.get("cash", 0) or 0))
    if portfolio_value <= 0:
        portfolio_value = float(context.get("cash", 0) or 0)
    risk_pct = round(risk_usd / portfolio_value * 100, 2) if risk_usd and portfolio_value else None
    if verdict == "good":
        headline = _good_headline(move)
    elif verdict == "bad":
        headline = _bad_headline(move)
    else:
        headline = _fix_headline(move)
    return {
        "verdict": verdict,
        "headline": headline,
        "symbol": str(move.get("symbol", "")).strip().upper(),
        "side": str(move.get("side", "buy")).strip().lower(),
        "setup": fired_strategy or setup_status,
        "reasons": reasons,
        "changes": [c for c in changes if c],
        "lessons_applied": [lesson["lesson"] for lesson in lessons_applied],
        # A sell is an exit — the wide-6 entry numbers do not apply to it.
        "suggested_stop": None if is_sell else (wide6_stop(entry) if entry else None),
        "suggested_target": None if is_sell else (wide6_target(entry) if entry else None),
        "risk_usd": risk_usd,
        "risk_pct": risk_pct,
        "open_positions": len(open_positions),
        "paper_only": True,
    }


def _verdict(verdict, headline, reasons, changes, move, context,
             setup_status, fired_strategy, lessons_applied,
             stop, target) -> dict:
    """Verdict for a move that could not even be described."""
    return {
        "verdict": verdict,
        "headline": headline,
        "symbol": str(move.get("symbol", "")).strip().upper(),
        "side": str(move.get("side", "buy")).strip().lower(),
        "setup": fired_strategy or setup_status or "unknown",
        "reasons": reasons,
        "changes": changes,
        "lessons_applied": [lesson["lesson"] for lesson in (lessons_applied or [])],
        "suggested_stop": wide6_stop(float(move.get("entry_price") or 0)) if move.get("entry_price") else None,
        "suggested_target": wide6_target(float(move.get("entry_price") or 0)) if move.get("entry_price") else None,
        "risk_usd": None,
        "risk_pct": None,
        "open_positions": len(context.get("open_trades", []) or []),
        "paper_only": True,
    }


def _good_headline(move: dict) -> str:
    side = str(move.get("side", "buy")).strip().lower()
    symbol = str(move.get("symbol", "")).strip().upper()
    if side == "sell":
        return f"Good play — bank it. Selling {symbol} takes a win off the table, and a banked win is a win."
    return (f"Good play. {symbol} fits the wide-6 rules, the stop is set, the size is small, "
            "and the plan banks a small win. You decide YES or NO — I never place trades.")


def _bad_headline(move: dict) -> str:
    symbol = str(move.get("symbol", "")).strip().upper()
    return (f"Bad play — don't make this one, {symbol}. The reasons are below, and "
            "they're not close calls. Fix the plan first, or skip the trade.")


def _fix_headline(move: dict) -> str:
    symbol = str(move.get("symbol", "")).strip().upper()
    return (f"Fix this first, {symbol}, and it can be a trade. The changes below are "
            "the difference between a plan and a hope.")


def render_verdict(result: dict) -> str:
    """The verdict as Ava would say it — headline, reasons, fixes,
    lessons, and the one line that never changes."""
    badge = {"good": "🟢 GOOD PLAY", "fix": "🟡 FIX THIS FIRST",
             "bad": "🔴 BAD PLAY"}.get(result["verdict"], "🟡 FIX THIS FIRST")
    lines = [f"{badge} — {result['symbol']} ({result['side']})",
             "",
             result["headline"],
             ""]
    if result["reasons"]:
        lines.append("Why:")
        for reason in result["reasons"]:
            lines.append(f"- {reason}")
        lines.append("")
    if result["changes"]:
        lines.append("What to change:")
        for change in result["changes"]:
            lines.append(f"- {change}")
        lines.append("")
    if result["suggested_stop"] is not None:
        risk_text = (f" — that risks ${result['risk_usd']:,.2f}"
                     if result.get("risk_usd") is not None else "")
        lines.append(f"Wide-6 numbers: stop ${result['suggested_stop']:,.2f}, "
                     f"target ${result['suggested_target']:,.2f}{risk_text}.")
        lines.append("")
    if result["lessons_applied"]:
        lines.append("What I've learned that applies here:")
        for lesson in result["lessons_applied"]:
            lines.append(f"- {lesson}")
        lines.append("")
    lines.append("Paper only. You decide YES or NO — I never place trades, "
                "and I never promise a profit.")
    return "\n".join(lines)
