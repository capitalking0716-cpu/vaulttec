"""Phase 2 history tests — historical analysis + signal accuracy tracking."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics import (
    accuracy_summary, analyse_history, backtest_macd_crossover,
    get_signal_history, record_signal,
)
from vaulttec.db.models import Signal
from vaulttec.market.data import SampleDataProvider


def _history(n=120):
    return SampleDataProvider().get_history("AAPL", days=n)


def test_analyse_history_describes_the_past():
    out = analyse_history(_history())
    assert out["days"] == 120
    assert out["volatility_pct"] > 0
    assert out["max_drawdown_pct"] <= 0
    assert "does not predict" in out["summary"]
    assert out["trend"] in ("up", "down", "flat")


def test_analyse_history_needs_little_data():
    import pandas as pd

    out = analyse_history(pd.DataFrame({"close": [100.0, 101.0]}))
    assert "Not enough history" in out["summary"]


def test_macd_backtest_returns_honest_numbers():
    bt = backtest_macd_crossover(_history())
    assert bt["trades"] >= 0
    assert 0 <= bt["win_rate_pct"] <= 100
    assert "Past performance" in bt["note"]


def test_signal_history_records_and_reports_not_enough_data(tmp_path):
    db = tmp_path / "test.db"
    record_signal(db, Signal(symbol="AAPL", direction="long", confidence=0.6,
                             evidence="test"), price_at_signal=100.0)
    history = get_signal_history(db)
    assert len(history) == 1
    assert history[0]["outcome"] is None
    acc = accuracy_summary(db)
    assert acc["accuracy_pct"] is None
    assert "not enough data" in acc["note"].lower()


def test_accuracy_only_after_ten_outcomes(tmp_path):
    db = tmp_path / "test.db"
    from vaulttec.analytics.signal_history import resolve_outcomes

    for i in range(12):
        record_signal(db, Signal(symbol="AAPL", direction="long", confidence=0.6,
                                 evidence="test",
                                 created_at="2026-01-01T00:00:00"),
                      price_at_signal=100.0)
    # Price lookup: always higher 5 days later -> all wins.
    resolved = resolve_outcomes(db, lambda symbol, date: 110.0)
    assert resolved == 12
    acc = accuracy_summary(db)
    assert acc["accuracy_pct"] == 100.0
    assert acc["total"] == 12
