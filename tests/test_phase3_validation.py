"""Phase 3 validation tests — the walk-forward run itself, on a small
target so the test stays fast. The full 40-trade run lives in
validation/phase3-paper-validation-report.md (generated, not hand-written)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.analytics.validation import run_validation, save_report


def test_small_validation_run_is_deterministic_and_complete():
    first = run_validation(target_trades=5)
    second = run_validation(target_trades=5)
    assert first["trades"] == second["trades"]  # same sample data, same result
    assert first["trades_placed"] == 5
    assert first["wins"] + first["losses"] == 5
    assert first["target_met"] is False  # 5 is below the brief's 30-trade minimum
    assert first["data_source"].startswith("sample")


def test_validation_trades_have_real_exits_and_ratios():
    report = run_validation(target_trades=5)
    for t in report["trades"]:
        assert t["exit_reason"] in ("stop-loss", "take-profit", "time exit (10 days)")
        assert 1 <= t["days_held"] <= 10
        # Take-profit is always at least 1.5x the risk after rounding.
        risk = t["entry"] - t["stop_loss"]
        reward = t["take_profit"] - t["entry"]
        assert reward / risk >= 1.5
        assert t["stop_loss"] < t["entry"] < t["take_profit"]
    assert report["total_pnl_usd"] == round(sum(t["pnl_usd"] for t in report["trades"]), 2)


def test_validation_report_saves_and_round_trips(tmp_path):
    report = run_validation(target_trades=5)
    json_path, md_path = save_report(report, tmp_path)
    saved = json.loads(json_path.read_text())
    assert saved["trades_placed"] == 5
    text = md_path.read_text()
    assert "Phase 3 Paper-Trading Validation Report" in text
    assert "does not promise profits" in text
    assert "| 1 |" in text  # the per-trade table is present
