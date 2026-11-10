"""Charts test — every chart builds without error on sample history,
in VaultTec colours, and empty states return None instead of crashing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.charts import (
    allocation_chart, candlestick_chart, cumulative_pnl_chart,
    indicator_chart, pnl_by_symbol_chart, scanner_confidence_chart,
    strategy_comparison_chart,
)
from vaulttec.db.models import PaperTrade
from vaulttec.market import get_provider


def _history():
    return get_provider("sample").get_history("AAPL", days=120)


def test_candlestick_and_indicator_charts():
    h = _history()
    fig = candlestick_chart(h, "AAPL")
    assert len(fig.data) >= 5  # candles + EMA 20/50 + Bollinger + volume
    assert fig.layout.paper_bgcolor == "#0b0b0d"
    fig2 = indicator_chart(h, "AAPL")
    assert len(fig2.data) >= 4  # RSI + MACD + signal + histogram


def test_allocation_and_pnl_charts():
    fig = allocation_chart(7000.0, {"AAPL": 2000.0, "GOOGL": 1000.0})
    assert fig.data[0].hole == 0.55
    trades = [
        PaperTrade("AAPL", "buy", 2, 200.0, 190.0, 220.0, "test", status="closed", pnl=40.0),
        PaperTrade("GOOGL", "buy", 1, 280.0, 260.0, 310.0, "test", status="open"),
    ]
    assert pnl_by_symbol_chart(trades, {"AAPL": 210.0, "GOOGL": 270.0}) is not None
    cum = cumulative_pnl_chart(trades)
    assert cum is not None
    assert cum.data[0].y[-1] == 40.0
    assert cumulative_pnl_chart([]) is None


def test_scanner_and_strategy_charts():
    rows = [
        {"symbol": "AAPL", "direction": "long", "confidence": 0.8},
        {"symbol": "GOOGL", "direction": "long", "confidence": 0.6},
    ]
    assert scanner_confidence_chart(rows) is not None
    assert scanner_confidence_chart([]) is None
    strategies = [
        {"strategy": "RSI", "total_return_pct": 12.4},
        {"strategy": "MACD", "total_return_pct": -3.1},
    ]
    fig = strategy_comparison_chart(strategies)
    assert list(fig.data[0].y) == [12.4, -3.1]


def test_sparkline_is_small_and_axis_free():
    from vaulttec.charts import sparkline_chart

    fig = sparkline_chart([1.0, 2.0, 1.5, 3.0])
    assert fig.layout.height == 48
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False
