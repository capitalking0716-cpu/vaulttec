"""Phase 3 backtest suite tests — four strategies, one comparison,
every result carrying a drawdown and a historical-only note."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.backtest import (
    backtest_bollinger_bands, backtest_macd_crossover, backtest_rsi,
    backtest_sma_crossover, max_drawdown_pct, run_backtest_suite,
)
from vaulttec.market.data import SampleDataProvider

PROVIDER = SampleDataProvider()


def _history(symbol="SPY", days=180):
    return PROVIDER.get_history(symbol, days=days)


def test_max_drawdown_is_worst_peak_to_trough():
    assert max_drawdown_pct([1.0, 1.1, 0.9, 1.0]) == -18.18
    assert max_drawdown_pct([1.0, 1.2, 1.3]) == 0.0
    assert max_drawdown_pct([]) == 0.0


def test_rsi_backtest_has_full_result_shape():
    result = backtest_rsi(_history())
    assert result["strategy"].startswith("RSI")
    assert set(result) >= {"total_return_pct", "trades", "win_rate_pct",
                           "max_drawdown_pct", "note"}
    assert result["max_drawdown_pct"] <= 0
    assert 0 <= result["win_rate_pct"] <= 100
    assert "does not guarantee" in result["note"]


def test_bollinger_backtest_has_full_result_shape():
    result = backtest_bollinger_bands(_history())
    assert result["strategy"].startswith("Bollinger")
    assert result["max_drawdown_pct"] <= 0
    assert 0 <= result["win_rate_pct"] <= 100


def test_existing_backtests_now_carry_drawdown():
    for fn in (backtest_sma_crossover, backtest_macd_crossover):
        result = fn(_history())
        assert "max_drawdown_pct" in result
        assert result["max_drawdown_pct"] <= 0
        assert "strategy" in result


def test_suite_runs_four_strategies_on_the_same_history():
    history = _history()
    suite = run_backtest_suite(history)
    assert len(suite["strategies"]) == 4
    names = [s["strategy"] for s in suite["strategies"]]
    assert names == ["SMA crossover", "MACD crossover", "RSI mean-reversion",
                     "Bollinger mean-reversion"]
    for s in suite["strategies"]:
        assert s["trades"] >= 0
        assert "does not guarantee" in s["note"]
    assert suite["best_by_return"] in names or suite["best_by_return"] is None
    assert "recommendation" in suite["note"]


def test_suite_handles_flat_data_without_hiding_any_strategy():
    # Flat prices: no trend, no momentum. The suite must still report
    # all four strategies (a strategy with zero trades is a result,
    # not an error) — and never crash or invent a return.
    flat = pd.DataFrame({"close": [100.0] * 120})
    suite = run_backtest_suite(flat)
    assert len(suite["strategies"]) == 4
    for s in suite["strategies"]:
        assert s["trades"] >= 0
        assert s["total_return_pct"] == 0.0 or s["trades"] > 0
    # A strategy that never traded must say so in its own numbers.
    assert all(s["win_rate_pct"] == 0.0 for s in suite["strategies"] if s["trades"] == 0)
