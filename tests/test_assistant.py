"""Phase 2 assistant tests — briefings, explanations, no invented answers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.ai_assistant import Assistant, NoLLMProvider
from vaulttec.analytics import generate_signal
from vaulttec.market import analyse_indicators
from vaulttec.market.data import SampleDataProvider


def _assistant():
    return Assistant()


def test_no_llm_by_default():
    a = _assistant()
    assert isinstance(a.llm, NoLLMProvider)
    try:
        a.llm.complete("hello")
        raise AssertionError("NoLLMProvider should raise")
    except RuntimeError as exc:
        assert "No LLM provider" in str(exc)


def test_daily_briefing_lists_opportunities_and_disclosure():
    a = _assistant()
    scan = [{"symbol": "AAPL", "direction": "long", "confidence": 0.65,
             "checks_agreeing": 3, "evidence": "trend up"}]
    text = a.daily_briefing(scan, 10_500.0, 120.0)
    assert "AAPL" in text and "long" in text
    assert "guarantee" in text.lower()


def test_daily_briefing_honest_when_nothing_clears_bar():
    a = _assistant()
    text = a.daily_briefing([], 10_000.0, 0.0)
    assert "No symbol" in text


def test_explain_strategy_covers_the_list():
    a = _assistant()
    expected_terms = {
        "SMA crossover": "moving average",
        "MACD crossover": "momentum",
        "stop-loss": "stop-loss",
        "position sizing": "position",
        "diversification": "concentration",
        "risk/reward": "1.5:1",
    }
    for name, term in expected_terms.items():
        text = a.explain_strategy(name)
        assert len(text) > 50
        assert term in text.lower()
        # No strategy explanation may promise profits.
        assert "guaranteed profit" not in text.lower()


def test_explain_market_uses_real_indicator_values():
    a = _assistant()
    history = SampleDataProvider().get_history("AAPL", days=120)
    ind = analyse_indicators(history)
    text = a.explain_market("AAPL", ind)
    assert "AAPL" in text and "not a forecast" in text


def test_answer_routes_portfolio_strategy_and_profit_questions():
    a = _assistant()
    assert "promise" in a.answer("will I make money?").lower()
    assert "stop-loss" in a.answer("what is a stop-loss?").lower()
    assert "SMA" in a.answer("explain the SMA crossover strategy")
    portfolio = a.answer("what is my portfolio worth?",
                         context={"portfolio_value": 10_500.0, "cash": 500.0,
                                  "holdings": [], "exposure": 10_000.0})
    assert "$10,500.00" in portfolio


def test_answer_never_invents_a_price():
    a = _assistant()
    text = a.answer("what will AAPL do tomorrow?")
    assert "don't know" in text.lower() or "can help" in text.lower()
