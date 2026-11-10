"""Ava test — her own persona, her lessons, her offline answers.

Ava is her own AI, and she replaces the old Vault
assistant in the app. She never places trades, never promises
profits, and learns one lesson per closed trade.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ava import Ava, learn_from_trade, load_lessons, review_closed_trades
from vaulttec.ava.ava import SYSTEM_PROMPT
from vaulttec.ava import llm
from vaulttec.db.models import PaperTrade
from vaulttec.paper_trading import PaperTradingEngine
from vaulttec.portfolio import Portfolio
from vaulttec.risk import RiskEngine


def test_ava_is_her_own_ai():
    assert Ava.name == "Ava"
    assert "Ava" in SYSTEM_PROMPT
    assert "not a copy of anyone else" in SYSTEM_PROMPT
    assert "hate losing money" in SYSTEM_PROMPT
    assert "never place" in SYSTEM_PROMPT.lower()
    assert "never promise" in SYSTEM_PROMPT.lower()
    assert not hasattr(Ava, "place_order")
    assert not hasattr(Ava, "place_trade")


def test_llm_offline_without_key(monkeypatch):
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm.llm_configured() is False
    assert llm.chat("system", "hi") is None


def test_lessons_learned_from_closed_trades(tmp_path, monkeypatch):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    win = PaperTrade("AAPL", "buy", 2, 200.0, 190.0, 220.0, "test",
                     status="closed", pnl=40.0)
    loss = PaperTrade("GOOGL", "buy", 1, 280.0, 260.0, 310.0, "test",
                      status="closed", pnl=-25.0)
    open_trade = PaperTrade("META", "buy", 1, 600.0, 570.0, 660.0, "test",
                            status="open")
    assert learn_from_trade(open_trade) is None
    assert learn_from_trade(win) is not None
    assert learn_from_trade(loss) is not None
    rows = load_lessons()
    assert len(rows) == 2
    assert rows[0]["symbol"] == "GOOGL"  # newest first
    assert rows[0]["won"] is False
    assert "stop did its job" in rows[0]["lesson"]


def test_review_closed_trades_only_once(tmp_path, monkeypatch):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    engine = PaperTradingEngine(Portfolio(cash=10000.0), RiskEngine())
    engine.place_order("AAPL", "buy", 1, 200.0, 190.0, 220.0,
                       reason="test", source="test")
    engine.close_position("AAPL", 220.0, exit_reason="target")
    first = review_closed_trades(engine)
    assert len(first) == 1
    second = review_closed_trades(engine)
    assert second == []


def test_ava_offline_answer_uses_real_numbers(monkeypatch, tmp_path):
    import vaulttec.ava.lessons as lessons_mod

    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    monkeypatch.delenv("AVA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ava = Ava()
    ctx = {"portfolio": {"cash": 7000.0, "value": 10000.0, "pnl": 0.0},
           "open_trades": [{"symbol": "GOOGL", "quantity": 1, "price": 610.15,
                            "stop_loss": 573.54, "take_profit": 665.07}],
           "signals": [{"symbol": "META", "direction": "long", "confidence": 0.8}]}
    answer = ava.ask("Should I close GOOGL?", ctx)
    assert "offline mode" in answer
    assert "GOOGL" in answer
    assert "never place trades" in answer
    assert "META" in answer
