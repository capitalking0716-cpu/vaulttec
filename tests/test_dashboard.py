"""Dashboard simplify tests — the Dashboard shows available trades only.

The metric cards, Win Rate, assets and portfolio charts moved to Results;
the candlestick chart and trading tools moved to Trade. These tests lock
in the available-trades rule (wide-6, existing signal pipeline) and the
new layout, so the Dashboard cannot quietly grow its old clutter back.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.dashboard import build_available_trades, passes_wide6
from vaulttec.db.models import Signal
from vaulttec.market.data import Quote
from vaulttec.risk import RiskEngine

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _signal(symbol="NVDA", direction="long", confidence=0.65):
    return Signal(symbol=symbol, direction=direction,
                  confidence=confidence, evidence="test evidence")


def _rsi_check():
    return {"name": "rsi", "side": "bullish", "weight": 1,
            "evidence": "RSI is 28 — recently oversold, so a bounce is possible (not promised)."}


def _bollinger_check():
    return {"name": "bollinger", "side": "bullish", "weight": 1,
            "evidence": "Price is near the lower Bollinger Band — it has fallen a lot recently."}


def _trend_check():
    return {"name": "trend", "side": "bullish", "weight": 2,
            "evidence": "Short-term trend is up (10-day average above 30-day)."}


def _quote(symbol="NVDA", price=100.0):
    return Quote(symbol=symbol, price=price, change_pct=1.0, volume=1000)


# --- passes_wide6 ------------------------------------------------------------

def test_long_with_rsi_trigger_passes():
    assert passes_wide6(_signal(), [_rsi_check(), _trend_check()])


def test_long_with_bollinger_trigger_passes():
    assert passes_wide6(_signal(), [_bollinger_check(), _trend_check()])


def test_short_never_passes_even_with_trigger():
    # A short is never an available trade — VaultTec does not short.
    bearish_rsi = {"name": "rsi", "side": "bearish", "weight": 1,
                   "evidence": "RSI is 72 — recently overbought."}
    assert not passes_wide6(_signal(direction="short"), [bearish_rsi])


def test_neutral_never_passes():
    assert not passes_wide6(_signal(direction="neutral", confidence=0.40),
                            [_rsi_check()])


def test_long_without_mean_reversion_trigger_does_not_pass():
    # A trend long with no RSI/Bollinger dip is not a wide-6 trade.
    assert not passes_wide6(_signal(), [_trend_check()])


def test_long_below_the_scanner_confidence_floor_does_not_pass():
    assert not passes_wide6(_signal(confidence=0.50),
                            [_rsi_check(), _trend_check()])


# --- build_available_trades ---------------------------------------------------

def test_build_available_trade_numbers_are_wide6():
    trades = build_available_trades(
        [_signal()], {"NVDA": [_rsi_check(), _trend_check()]},
        {"NVDA": _quote()}, 10000.0, RiskEngine())
    assert len(trades) == 1
    t = trades[0]
    assert t["symbol"] == "NVDA"
    assert t["direction"] == "BUY"
    assert t["confidence"] == 0.65
    assert t["entry"] == 100.0
    assert t["stop_loss"] == 94.0        # 6% stop
    assert t["take_profit"] == 109.0     # 9% target
    assert t["risk_reward"] == "1.5:1"
    assert t["shares"] == 10.0           # 10% of a $10,000 pot at $100
    assert t["risk_usd"] == 60.0         # 6% of the $1,000 position
    assert t["reward_usd"] == 90.0       # 9% of the $1,000 position
    assert "RSI is 28" in t["setup"]


def test_build_available_trades_sorted_strongest_first():
    trades = build_available_trades(
        [_signal("AAPL", confidence=0.60), _signal("NVDA", confidence=0.75)],
        {"AAPL": [_rsi_check()], "NVDA": [_bollinger_check()]},
        {"AAPL": _quote("AAPL", 200.0), "NVDA": _quote("NVDA", 100.0)},
        10000.0, RiskEngine())
    assert [t["symbol"] for t in trades] == ["NVDA", "AAPL"]


def test_build_available_trades_skips_symbols_already_held():
    trades = build_available_trades(
        [_signal()], {"NVDA": [_rsi_check()]},
        {"NVDA": _quote()}, 10000.0, RiskEngine(),
        held_symbols={"NVDA"})
    assert trades == []


def test_build_available_trades_skips_non_passing_and_unpriceable():
    trades = build_available_trades(
        [_signal("AAPL", direction="short"),
         _signal("MSFT", direction="neutral", confidence=0.40),
         _signal("NVDA"),
         _signal("TSLA")],
        {"AAPL": [_rsi_check()], "MSFT": [_rsi_check()],
         "NVDA": [_rsi_check()],
         "TSLA": [_rsi_check()]},
        {"AAPL": _quote("AAPL", 200.0), "MSFT": _quote("MSFT", 300.0),
         "NVDA": _quote("NVDA", 100.0), "TSLA": _quote("TSLA", 0.0)},
        10000.0, RiskEngine())
    # Only NVDA passes: AAPL is a short, MSFT is neutral, TSLA has no price.
    assert [t["symbol"] for t in trades] == ["NVDA"]


def test_build_available_trades_empty_when_nothing_passes():
    assert build_available_trades(
        [_signal(direction="neutral", confidence=0.40)],
        {"NVDA": [_rsi_check()]}, {"NVDA": _quote()},
        10000.0, RiskEngine()) == []


# --- Layout: the Dashboard is trades-only, the moved pieces live on --------

def _tab_block(src: str, start: str, end: str) -> str:
    return src[src.index(start):src.index(end, src.index(start))]


def test_dashboard_tab_is_trades_only():
    src = APP_PATH.read_text()
    dash = _tab_block(src, "with tab_dashboard:", "with tab_scanner:")
    assert "Available trades" in dash
    assert "build_available_trades" in dash
    assert "No available trades right now" in dash
    for gone in ('st.subheader("💰 Your Assets")',
                 'st.subheader("🛠️ Trading Tools")',
                 "sparkline_chart", "candlestick_chart", "indicator_chart",
                 "_metric_card(", "allocation_chart", "pnl_by_symbol_chart",
                 "Market Overview", "Market Intelligence"):
        assert gone not in dash, f"Dashboard still shows {gone}"


def test_moved_pieces_live_in_results():
    src = APP_PATH.read_text()
    res = _tab_block(src, "with tab_results:", "with tab_live_paper:")
    for piece in ("_metric_card(", "Win Rate",
                  'st.subheader("💰 Your Assets")',
                  "allocation_chart", "pnl_by_symbol_chart"):
        assert piece in res, f"Results lost {piece}"


def test_moved_pieces_live_in_trade():
    src = APP_PATH.read_text()
    trade = _tab_block(src, "with tab_trade:", "with tab_results:")
    assert "candlestick_chart" in trade
    assert "indicator_chart" in trade
    assert 'st.subheader("🛠️ Trading Tools")' in trade


# --- Chats stay: Neko's rule — the simplification moves display stuff
# only. Ava's always-on chat and Check My Move are not moved, not
# trimmed, not hidden. -------------------------------------------------

def test_ava_chat_stays_in_results():
    src = APP_PATH.read_text()
    res = _tab_block(src, "with tab_results:", "with tab_live_paper:")
    for piece in ('st.header("💜 Ava — your trading AI")',
                  "st.session_state.ava.brief(",
                  '"ava_chat" not in st.session_state',
                  "st.chat_message(",
                  'st.chat_input("Talk to Ava..."',
                  "st.session_state.ava.ask(",
                  "st.rerun()"):
        assert piece in res, f"Results lost Ava chat piece: {piece}"
    assert "🎬 Watch Ava" in res
    assert "Review my closed trades" in res


def test_check_my_move_stays_in_results():
    src = APP_PATH.read_text()
    res = _tab_block(src, "with tab_results:", "with tab_live_paper:")
    for piece in ('st.form("ava_check_move"',
                  "Ask Ava — is this a good play?",
                  'st.session_state["ava_move_check"]',
                  "Small wins — what to bank, what to cut"):
        assert piece in res, f"Results lost Check My Move piece: {piece}"


def test_no_shadow_remains():
    # Neko: Shadow is gone completely — Ava is the in-app AI now.
    # No Shadow tab, no shadow_bridge import, no Shadow UI anywhere.
    src = APP_PATH.read_text()
    assert "shadow_bridge" not in src
    assert "tab_shadow" not in src
    assert '"Shadow"' not in src
    assert "🌑 Shadow" not in src
    assert "Ask Shadow" not in src
    assert "Notes from Shadow" not in src
    assert "Save this question for Shadow" not in src
    assert "shadow-questions" not in src
    assert "shadow-notes" not in src
    # Tabs are six now: Dashboard, Scanner, Trade, Results, Live Paper,
    # Private.
    tabs_lines = [ln for ln in src.splitlines() if "st.tabs(" in ln]
    assert len(tabs_lines) == 1
    for name in ("Dashboard", "Scanner", "Trade", "Results",
                 "Live Paper", "Private"):
        assert f'"{name}"' in tabs_lines[0], f"tab lost: {name}"


def test_dashboard_has_no_chat_to_remove():
    # The Dashboard never held a chat — the only Ava thing there was a
    # card pointing at Results, which is where her chat lives.
    src = APP_PATH.read_text()
    dash = _tab_block(src, "with tab_dashboard:", "with tab_scanner:")
    assert "st.chat_input(" not in dash
    assert "st.chat_message(" not in dash
    assert "ava_check_move" not in dash
