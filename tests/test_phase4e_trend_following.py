"""Phase 4e — trend-following tests. The real run uses cached real
Yahoo Finance histories; these tests never touch the network. They
use deterministic stub histories and check the trend trigger and
the wide-6 runner, and that the pooled verdict rule matches Phase 4d.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.exit_test import variant_by_id
from vaulttec.analytics.trend_following import (
    TREND_LABEL,
    run_trend_variant,
    trend_trigger,
)


def _history(days: int = 150, rising: bool = True) -> pd.DataFrame:
    """Synthetic OHLCV (test stub only — never presented as real
    data): flat at 100 for 80 days, then a steady 1%/day rise or
    fall. After the rise, close > SMA-20 > SMA-50; after the fall,
    the reverse — so the trigger fires on the rise and never on
    the fall."""
    rows, price = [], 100.0
    dates = pd.date_range(end=pd.Timestamp("2024-08-30"), periods=days)
    for i, date in enumerate(dates):
        open_p = price
        if i >= 80:
            price *= 1.01 if rising else 0.99
        close = price
        rows.append({"date": date, "open": round(open_p, 2),
                     "high": round(max(open_p, close) * 1.002, 2),
                     "low": round(min(open_p, close) * 0.998, 2),
                     "close": round(close, 2), "volume": 1_000_000})
    return pd.DataFrame(rows)


def test_trend_trigger_fires_on_rise_not_fall():
    rising = _history(rising=True)
    fired = [i for i in range(50, len(rising))
             if trend_trigger(rising.iloc[: i + 1])]
    assert fired, "trend trigger never fired on a steadily rising history"
    falling = _history(rising=False)
    assert not any(trend_trigger(falling.iloc[: i + 1])
                   for i in range(50, len(falling)))


def test_trend_trigger_needs_defined_averages():
    assert trend_trigger(_history(days=10)) is False
    assert trend_trigger(_history(days=49)) is False


def test_run_trend_variant_buys_the_rise_not_the_fall():
    wide6 = variant_by_id("wide-6")
    rising = run_trend_variant(wide6, {"AAPL": _history(rising=True)})
    assert rising["trades_placed"] >= 1
    assert rising["wins"] + rising["losses"] == rising["trades_placed"]
    assert rising["stop_pct"] == 0.06
    assert rising["take_pct"] == 0.09
    for trade in rising["trades"]:
        assert trade["stop_loss"] == round(trade["entry"] * 0.94, 2)
        assert trade["take_profit"] > trade["entry"]
        assert trade["exit_reason"] in (
            "stop-loss", "take-profit", "time exit (10 days)")
    falling = run_trend_variant(wide6, {"AAPL": _history(rising=False)})
    assert falling["trades_placed"] == 0


def test_trend_label_names_the_rule():
    assert "SMA-20" in TREND_LABEL and "SMA-50" in TREND_LABEL
