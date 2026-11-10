"""Check My Move tests — Ava's verdicts on the trade Neko is about
to make. A good wide-6 setup passes; a chase, a no-stop, an
oversized, a home-run, a short, or a leveraged play is flagged.
Everything here works with no API key — the check is pure logic.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ava import Ava, check_move, load_live_paper_positions, load_private_proposals, render_verdict
from vaulttec.ava.ava import SYSTEM_PROMPT
from vaulttec.ava.move_check import wide6_stop, wide6_target


def _declining_history() -> pd.DataFrame:
    """Steady fall 100 -> 71: RSI 0, the wide-6 RSI trigger fires."""
    closes = [100.0 - i for i in range(30)]
    return pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=30), "close": closes})


def _rising_history() -> pd.DataFrame:
    """Steady rise 70 -> 99: no trigger — buying here is chasing."""
    closes = [70.0 + i for i in range(30)]
    return pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=30), "close": closes})


def _bollinger_history() -> pd.DataFrame:
    """Quiet base, then a drop to the lower band: RSI 43.8, the
    Bollinger trigger fires, the RSI trigger does not."""
    closes = [100.0 if i % 2 == 0 else 101.0 for i in range(20)] + [98.0]
    return pd.DataFrame({
        "date": pd.date_range("2026-10-01", periods=len(closes)), "close": closes})


def _context(**overrides) -> dict:
    ctx = {"portfolio_value": 10000.0, "cash": 10000.0,
           "open_trades": [], "holdings": [], "risk_tolerance": "balanced"}
    ctx.update(overrides)
    return ctx


def _good_buy(entry: float = 71.0) -> dict:
    return {"symbol": "AAPL", "side": "buy", "quantity": 10,
            "entry_price": entry, "stop_loss": wide6_stop(entry),
            "take_profit": wide6_target(entry),
            "setup": "RSI bounced off the bottom, price at the lower band"}


def test_good_wide6_rsi_buy_passes():
    result = check_move(_good_buy(), _context(), history=_declining_history())
    assert result["verdict"] == "good"
    assert result["setup"] == "rsi"
    assert result["risk_usd"] == 42.6
    assert result["paper_only"] is True
    text = render_verdict(result)
    assert "GOOD PLAY" in text
    assert "You decide YES or NO" in text
    assert "never promise" in text.lower()
    assert "guaranteed" not in text.lower()
    assert "will win" not in text.lower()


def test_good_wide6_bollinger_buy_passes():
    move = {"symbol": "AAPL", "side": "buy", "quantity": 5,
            "entry_price": 98.0, "stop_loss": wide6_stop(98.0),
            "take_profit": wide6_target(98.0),
            "setup": "price dropped to the lower band"}
    result = check_move(move, _context(), history=_bollinger_history())
    assert result["verdict"] == "good"
    assert result["setup"] == "bollinger"


def test_chase_is_flagged_not_a_wide6_setup():
    move = {"symbol": "AAPL", "side": "buy", "quantity": 5,
            "entry_price": 99.0, "stop_loss": 93.06, "take_profit": 107.91,
            "setup": "it keeps going up, don't want to miss it"}
    result = check_move(move, _context(), history=_rising_history())
    assert result["verdict"] == "fix"
    assert any("isn't a wide-6 setup" in reason for reason in result["reasons"])
    assert any("chasing" in reason for reason in result["reasons"])
    assert any("Wait for the trigger" in change for change in result["changes"])


def test_no_stop_is_a_bad_play():
    move = _good_buy()
    move["stop_loss"] = None
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "bad"
    assert any("No stop, no trade" in reason for reason in result["reasons"])
    assert "Bad play" in result["headline"]


def test_stop_above_entry_is_a_bad_play():
    move = _good_buy()
    move["stop_loss"] = 75.0
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "bad"


def test_oversized_is_flagged_with_the_max_size():
    move = _good_buy()
    move["quantity"] = 100
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "fix"
    assert any("14.0845" in change for change in result["changes"])
    assert any("exceeds the max position size" in reason for reason in result["reasons"])


def test_home_run_target_is_flagged():
    move = _good_buy()
    move["take_profit"] = 100.0
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "fix"
    assert any("home run" in reason for reason in result["reasons"])
    assert result["suggested_target"] == 77.40


def test_sell_without_holding_is_a_bad_play():
    move = {"symbol": "AAPL", "side": "sell", "quantity": 5,
            "entry_price": 100.0, "stop_loss": 94.0, "take_profit": 91.0}
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "bad"
    assert any("don't short" in reason for reason in result["reasons"])


def _holding_context(current_price: float) -> dict:
    return _context(
        open_trades=[{"symbol": "GOOGL", "side": "buy", "quantity": 10,
                      "price": 100.0, "stop_loss": 94.0, "take_profit": 109.0,
                      "status": "open"}],
        holdings=[{"symbol": "GOOGL", "quantity": 10, "avg_cost": 100.0,
                   "current_price": current_price, "value": current_price * 10}])


def test_sell_bankable_win_is_a_good_play():
    move = {"symbol": "GOOGL", "side": "sell", "quantity": 10,
            "entry_price": 106.0, "stop_loss": 100.0, "take_profit": None}
    result = check_move(move, _holding_context(106.0))
    assert result["verdict"] == "good"
    assert "bank it" in result["headline"].lower()
    assert any("$60.00" in reason for reason in result["reasons"])


def test_sell_past_the_stop_is_cut_it_now():
    move = {"symbol": "GOOGL", "side": "sell", "quantity": 10,
            "entry_price": 93.0, "stop_loss": 88.0, "take_profit": None}
    result = check_move(move, _holding_context(93.0))
    assert result["verdict"] == "good"
    assert any("past your stop" in reason for reason in result["reasons"])


def test_sell_small_loss_before_the_stop_is_flagged():
    move = {"symbol": "GOOGL", "side": "sell", "quantity": 10,
            "entry_price": 98.0, "stop_loss": 92.0, "take_profit": None}
    result = check_move(move, _holding_context(98.0))
    assert result["verdict"] == "fix"
    assert any("fear, not a plan" in reason for reason in result["reasons"])


def test_sell_without_a_current_price_is_flagged():
    ctx = _context(open_trades=[{"symbol": "GOOGL", "side": "buy",
                                 "quantity": 10, "price": 100.0,
                                 "stop_loss": 94.0, "take_profit": 109.0,
                                 "status": "open"}])
    move = {"symbol": "GOOGL", "side": "sell", "quantity": 10,
            "entry_price": 100.0, "stop_loss": 94.0, "take_profit": None}
    result = check_move(move, ctx)
    assert result["verdict"] == "fix"
    assert any("can't see the current price" in reason for reason in result["reasons"])


def test_unknown_setup_caps_the_verdict_at_fix():
    result = check_move(_good_buy(), _context(), history=None)
    assert result["verdict"] == "fix"
    assert any("couldn't check the setup" in reason for reason in result["reasons"])


def test_leverage_in_the_setup_is_a_bad_play():
    move = _good_buy()
    move["setup"] = "going in with leverage to make it count"
    result = check_move(move, _context(), history=_declining_history())
    assert result["verdict"] == "bad"
    assert any("leverage" in reason for reason in result["reasons"])


def test_matching_lesson_is_surfaced():
    lessons = [{"symbol": "AAPL", "lesson": "AAPL lost $25.00. The stop did its job."}]
    result = check_move(_good_buy(), _context(), history=_declining_history(),
                        lessons=lessons)
    assert lessons[0]["lesson"] in result["lessons_applied"]


def test_pending_proposal_for_the_symbol_is_noted():
    proposals = [{"proposal_id": "PROP-1", "symbol": "AAPL",
                  "entry_price": 70.0, "stop_loss": 65.8, "take_profit": 76.3,
                  "status": "pending"}]
    result = check_move(_good_buy(), _context(), history=_declining_history(),
                        pending_proposals=proposals)
    assert result["verdict"] == "good"
    assert any("pending private proposal" in reason for reason in result["reasons"])


def test_loaders_read_real_state_files(tmp_path):
    live_dir = tmp_path / "live_paper"
    live_dir.mkdir()
    (live_dir / "state.json").write_text(json.dumps({
        "open_positions": [{"symbol": "META", "entry_price": 610.15,
                            "quantity": 1.6389, "stop_loss": 573.54,
                            "take_profit": 665.07, "bars_held": 0}],
        "last_close": {"META": 612.0}}), encoding="utf-8")
    props_dir = tmp_path / "vaulttec" / "private_live"
    props_dir.mkdir(parents=True)
    (props_dir / "proposals.json").write_text(json.dumps([
        {"proposal_id": "P1", "symbol": "NVDA", "status": "pending"},
        {"proposal_id": "P2", "symbol": "SPY", "status": "rejected"}]),
        encoding="utf-8")
    positions = load_live_paper_positions(tmp_path)
    assert len(positions) == 1
    assert positions[0]["symbol"] == "META"
    assert positions[0]["current_price"] == 612.0
    proposals = load_private_proposals(tmp_path)
    assert [p["proposal_id"] for p in proposals] == ["P1"]
    assert load_live_paper_positions(tmp_path / "empty") == []
    assert load_private_proposals(tmp_path / "empty") == []


def test_offline_check_move_returns_the_verdict_text(monkeypatch):
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ava = Ava()
    text = ava.check_move(_good_buy(), _context(),
                          history=_declining_history())
    assert "GOOD PLAY" in text
    assert "You decide YES or NO" in text
    assert "offline mode" not in text  # the verdict itself is the answer


def test_snapshot_shaped_context_reads_the_nested_portfolio(monkeypatch):
    """The app passes build_context_snapshot's shape — money nested
    under context["portfolio"], risk tolerance under
    context["user"]. A good move must still pass; the pot must not
    read as $0 (a $0 pot blocks everything)."""
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ctx = {"user": {"name": "Neko", "risk_tolerance": "balanced"},
           "portfolio": {"cash": 7000.0, "value": 10000.0, "pnl": 0.0},
           "holdings": [], "open_trades": [], "signals": []}
    result = check_move(_good_buy(), ctx, history=_declining_history())
    assert result["verdict"] == "good"
    assert result["risk_pct"] == 0.43


def test_system_prompt_has_the_sharper_voice():
    assert "bad play is a bad play" in SYSTEM_PROMPT
    assert "small win" in SYSTEM_PROMPT
    assert "bank" in SYSTEM_PROMPT
    assert "hate losing money" in SYSTEM_PROMPT
    assert "never place" in SYSTEM_PROMPT.lower()
    assert "never promise" in SYSTEM_PROMPT.lower()
