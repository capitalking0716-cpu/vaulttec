"""Weekly paper summary tests — stub data only, no network.

The generator reads the two paper runs' durable state and the
evidence/lessons logs. Tests build real state with the stub
providers (system live-paper run + Ava daily run over the same
dip), then check the week's numbers, the side-by-side table, the
per-day breakdown, and that the old historical-window evidence
(FRESH-1/2/3 simulations) is excluded from the week's numbers.
"""
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import vaulttec.ava.lessons as lessons_mod
from test_ava_daily_trading import _next_bar_frame
from test_live_paper_trading import RUN_DATE, StubProvider, _dip_history
from vaulttec.ava.daily_trading import run_ava_daily
from vaulttec.live_paper_trading import run_live_day
from vaulttec.weekly_summary import generate_weekly_summary, week_bounds

MONDAY = RUN_DATE  # Mon 2026-11-09
TUESDAY = date(2026, 11, 10)
FRIDAY = date(2026, 11, 13)


def _clean_env(monkeypatch):
    monkeypatch.delenv("VAULTTEC_LIVE_TRADING_ENABLED", raising=False)
    monkeypatch.delenv("ALPACA_PAPER", raising=False)


def _build_week(tmp_path, monkeypatch):
    """Run both paper runners Mon + Tue (open on a dip, stop out on
    the next bar) and return the paths the summary reads."""
    _clean_env(monkeypatch)
    monkeypatch.setattr(lessons_mod, "lessons_path",
                        lambda: tmp_path / "ava-lessons.jsonl")
    system_dir = tmp_path / "live_paper"
    ava_dir = tmp_path / "ava-daily"
    evidence_file = tmp_path / "ava-evidence.jsonl"
    dip = _dip_history()
    provider = StubProvider({"AAPL": dip})
    run_live_day(run_date=MONDAY, provider=provider,
                 live_dir=system_dir, symbols=["AAPL"])
    run_ava_daily(run_date=MONDAY, provider=provider,
                  ava_dir=ava_dir, evidence_file=evidence_file,
                  symbols=["AAPL"])
    state = json.loads((ava_dir / "state.json").read_text(encoding="utf-8"))
    stop = state["open_positions"][0]["stop_loss"]
    crash = _next_bar_frame(dip, "2026-11-09", 86.06, 86.5, stop - 1.0, stop - 0.5)
    provider.frames["AAPL"] = crash
    run_live_day(run_date=TUESDAY, provider=provider,
                 live_dir=system_dir, symbols=["AAPL"])
    run_ava_daily(run_date=TUESDAY, provider=provider,
                  ava_dir=ava_dir, evidence_file=evidence_file,
                  symbols=["AAPL"])
    # One fake historical-window record (no "run" key) and one
    # lesson from before the week — both must be excluded.
    with evidence_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "when": "2026-11-10T03:03:10", "window": "FRESH-1",
            "symbol": "AAPL", "signal": "rsi", "status": "placed",
            "entry": 173.21, "stop": 162.82, "target": 188.8,
            "position_size": 0.0577, "pnl_usd": 1.23, "won": True}) + "\n")
    lessons_path = tmp_path / "ava-lessons.jsonl"
    with lessons_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "when": "2026-11-08T10:00:00", "symbol": "AAPL",
            "side": "buy", "entry": 86.06, "pnl": 1.00, "won": True,
            "source": "ava-paper", "lesson": "old lesson"}) + "\n")
    return {
        "system_dir": system_dir,
        "ava_dir": ava_dir,
        "evidence_file": evidence_file,
        "lessons_file": lessons_path,
        "out": tmp_path / "weekly-paper-report-2026-11-13.md",
    }


def test_week_bounds_are_monday_to_friday():
    monday, friday = week_bounds(FRIDAY)
    assert monday == date(2026, 11, 9) and friday == FRIDAY
    monday2, friday2 = week_bounds(date(2026, 11, 11))  # Wednesday
    assert (monday2, friday2) == (monday, friday)
    monday3, friday3 = week_bounds()
    assert monday3.weekday() == 0 and friday3.weekday() == 4
    assert (friday3 - monday3).days == 4


def test_weekly_summary_counts_both_runs_side_by_side(tmp_path, monkeypatch):
    paths = _build_week(tmp_path, monkeypatch)
    result = generate_weekly_summary(
        week_end=FRIDAY, project_root=tmp_path, out_path=paths["out"],
        live_state_path=paths["system_dir"] / "state.json",
        ava_state_path=paths["ava_dir"] / "state.json",
        evidence_file=paths["evidence_file"],
        lessons_file=paths["lessons_file"])
    assert result["week_monday"] == "2026-11-09"
    assert result["week_friday"] == "2026-11-13"
    assert Path(result["output_path"]).exists()
    # System side: one trade opened Monday, closed Tuesday at a loss.
    sys_ = result["system"]
    assert sys_["started"] is True
    assert sys_["opened_week"] == 1
    assert sys_["closed_week"] == 1
    assert sys_["wins_week"] == 0
    assert sys_["pnl_week_usd"] < 0
    # Ava side: same week, same shape, $100 pot — and the old
    # FRESH-1 record was NOT counted.
    ava = result["ava"]
    assert ava["started"] is True
    assert ava["opened_week"] == 1  # not 2: the FRESH-1 record excluded
    assert ava["closed_week"] == 1
    assert ava["wins_week"] == 0
    assert ava["pnl_week_usd"] < 0
    # Lessons: one learned on Tuesday's close; the Nov 8 lesson excluded.
    assert ava["lessons_week"] == 1
    text = result["text"]
    assert "2026-11-09 to 2026-11-13" in text
    assert "PAPER ONLY" in text
    assert "System" in text and "Ava" in text
    assert "Side by side" in text
    assert "Day by day" in text
    # Per-day rows: Mon + Tue ran, Wed–Fri did not.
    assert "Mon 2026-11-09" in text and "Tue 2026-11-10" in text
    assert "Wed 2026-11-11" in text and "no run recorded" in text
    assert "Past performance does not guarantee future results" in text


def test_weekly_summary_with_ava_not_started_yet(tmp_path, monkeypatch):
    _clean_env(monkeypatch)
    system_dir = tmp_path / "live_paper"
    provider = StubProvider({"AAPL": _dip_history()})
    run_live_day(run_date=MONDAY, provider=provider,
                 live_dir=system_dir, symbols=["AAPL"])
    result = generate_weekly_summary(
        week_end=FRIDAY, project_root=tmp_path,
        out_path=tmp_path / "weekly.md",
        live_state_path=system_dir / "state.json",
        ava_state_path=tmp_path / "no-such-ava-state.json",
        evidence_file=tmp_path / "no-such-evidence.jsonl",
        lessons_file=tmp_path / "no-such-lessons.jsonl")
    assert result["ava"]["started"] is False
    assert result["system"]["started"] is True
    assert "hasn't started her daily run yet" in result["text"]


def test_weekly_summary_with_nothing_started(tmp_path):
    result = generate_weekly_summary(
        week_end=FRIDAY, project_root=tmp_path,
        out_path=tmp_path / "weekly.md",
        live_state_path=tmp_path / "no-system.json",
        ava_state_path=tmp_path / "no-ava.json",
        evidence_file=tmp_path / "no-evidence.jsonl",
        lessons_file=tmp_path / "no-lessons.jsonl")
    assert result["system"]["started"] is False
    assert result["ava"]["started"] is False
    assert "Neither paper run has started yet" in result["text"]
