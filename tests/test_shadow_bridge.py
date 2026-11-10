"""Shadow bridge test — context snapshot, question round-trip, empty states."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.db.models import PaperTrade, UserProfile
from vaulttec.paper_trading import PaperTradingEngine
from vaulttec.portfolio import Portfolio
from vaulttec.risk import RiskEngine
from vaulttec.shadow_bridge import (
    build_context_snapshot, load_notes, load_questions, save_question,
)


def test_snapshot_and_question_roundtrip(tmp_path, monkeypatch):
    import vaulttec.shadow_bridge as bridge

    monkeypatch.setattr(bridge, "bridge_dir", lambda: tmp_path)
    profile = UserProfile(name="Neko", goal="Grow steadily")
    portfolio = Portfolio(cash=9000.0)
    risk = RiskEngine()
    engine = PaperTradingEngine(portfolio, risk)
    prices = {"AAPL": 230.0}
    snap = build_context_snapshot(profile, portfolio, engine, [], prices,
                                  9000.0, 9000.0, 0.0)
    assert snap["user"]["name"] == "Neko"
    assert snap["portfolio"]["cash"] == 9000.0
    assert load_questions() == []
    assert load_notes() == ""
    path = save_question("Should I close AAPL?", snap)
    assert path.exists()
    rows = load_questions()
    assert len(rows) == 1
    assert rows[0]["question"] == "Should I close AAPL?"
    assert rows[0]["context"]["portfolio"]["cash"] == 9000.0


def test_snapshot_includes_open_trades():
    profile = UserProfile(name="Neko")
    portfolio = Portfolio(cash=10000.0)
    risk = RiskEngine()
    engine = PaperTradingEngine(portfolio, risk)
    engine.place_order("AAPL", "buy", 1, 200.0, 190.0, 220.0, reason="test", source="test")
    snap = build_context_snapshot(profile, portfolio, engine, [], {"AAPL": 210.0},
                                  portfolio.cash, 10010.0, 10.0)
    assert len(snap["open_trades"]) == 1
    assert snap["open_trades"][0]["symbol"] == "AAPL"
