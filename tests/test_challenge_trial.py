"""Challenge Trial tests — pure logic, no Streamlit, no network.

Paper only: the $20 is the user's own starting capital, VaultTec
takes nothing from it, there is no payment logic, and live trading
is never enabled by this module. Trading platform, not a school:
pass = 30 paper trades only, no course, no Academy.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.challenge import (
    CHALLENGE_REQUIRED_TRADES,
    CHALLENGE_STARTING_CAPITAL,
    CHALLENGE_STARTING_CAPITAL_LABEL,
    NO_REASONS,
    ChallengeTrial,
    build_proposal,
    explain_proposal_plain,
    wide6_stop_target,
)


def _trial_with_trades(n_wins, n_losses):
    trial = ChallengeTrial()
    for _ in range(n_wins):
        trial.record_trade("AAPL", outcome="win", pnl=45.0)
    for _ in range(n_losses):
        trial.record_trade("AAPL", outcome="loss", pnl=-30.0)
    return trial


def test_starting_capital_is_the_users_money_not_a_fee():
    trial = ChallengeTrial()
    assert trial.starting_capital == 20.0
    assert CHALLENGE_STARTING_CAPITAL == 20.0
    assert trial.vaulttec_takes_from_starting_capital_usd == 0.0
    assert "$20" in CHALLENGE_STARTING_CAPITAL_LABEL
    assert "VaultTec takes nothing" in CHALLENGE_STARTING_CAPITAL_LABEL
    summary = trial.summary()
    assert summary["starting_capital_usd"] == 20.0
    assert summary["vaulttec_takes_from_starting_capital_usd"] == 0.0
    assert summary["paper_only"] is True
    assert summary["live_trading_available"] is False
    assert "NOT yet available" in summary["live_trading_note"]


def test_losing_trades_count_toward_the_30_and_pass():
    # 30 losing trades pass — finishing is the pass, not profit,
    # and there is no course gate any more.
    trial = _trial_with_trades(0, 30)
    assert trial.trades_done == 30
    assert trial.trades_remaining == 0
    assert trial.yes_no_accuracy()["losses"] == 30
    assert trial.is_complete is True
    assert "Challenge complete" in trial.graduation_message()
    assert "NOT yet available" in trial.graduation_message()


def test_thirty_trades_win_or_lose_passes_with_no_course():
    trial = _trial_with_trades(15, 15)
    assert trial.trades_done == 30
    assert trial.is_complete is True
    assert "Challenge complete" in trial.graduation_message()


def test_graduation_gate_is_30_trades_only():
    trial = ChallengeTrial()
    for _ in range(29):
        trial.record_trade("AAPL", outcome="win", pnl=10.0)
    assert trial.is_complete is False
    assert trial.whats_left == ["1 more paper trade(s) to reach 30"]
    trial.record_trade("AAPL", outcome="loss", pnl=-10.0)
    assert trial.is_complete is True
    assert trial.whats_left == []


def test_no_course_attributes_remain():
    # Academy / course was removed: no course state, no level API.
    trial = ChallengeTrial()
    assert not hasattr(trial, "completed_levels")
    assert not hasattr(trial, "complete_level")
    assert not hasattr(trial, "is_course_done")
    assert not hasattr(trial, "course_progress_pct")
    summary = trial.summary()
    assert "is_course_done" not in summary
    assert "course_progress_pct" not in summary
    assert "required_levels_done" not in summary


def test_yes_no_decisions_are_logged_and_no_places_no_trade():
    trial = ChallengeTrial()
    yes = trial.record_decision(
        "AAPL", "long", 0.65, "RSI oversold", 100.0, 94.0, 109.0, 1.0,
        "yes", "Agreed with the AI's reasoning")
    assert yes.decision == "yes"
    assert trial.trades_done == 0  # a decision alone is not a trade
    no = trial.record_decision(
        "MSFT", "long", 0.55, "Weak evidence", 200.0, 188.0, 218.0, 1.0,
        "no", NO_REASONS[0])
    assert no.decision == "no"
    assert no.reason == NO_REASONS[0]
    assert trial.trades_done == 0  # a NO never places a trade
    acc = trial.yes_no_accuracy()
    assert acc["yes_decisions"] == 1
    assert acc["no_decisions"] == 1
    assert acc["accuracy_pct"] is None  # nothing resolved yet


def test_no_without_a_reason_gets_a_default_reason():
    trial = ChallengeTrial()
    record = trial.record_decision(
        "AAPL", "long", 0.5, "evidence", 100.0, 94.0, 109.0, 1.0, "no", "")
    assert record.reason == "No reason given"
    with pytest.raises(ValueError):
        trial.record_decision(
            "AAPL", "long", 0.5, "evidence", 100.0, 94.0, 109.0, 1.0, "maybe", "")


def test_yes_no_accuracy_counts_only_resolved_trades():
    trial = ChallengeTrial()
    trial.record_trade("AAPL", outcome="win", pnl=45.0)
    trial.record_trade("MSFT", outcome="loss", pnl=-30.0)
    trial.record_trade("NVDA", outcome="open", pnl=0.0)
    acc = trial.yes_no_accuracy()
    assert acc["resolved_trades"] == 2
    assert acc["wins"] == 1 and acc["losses"] == 1
    assert acc["accuracy_pct"] == 50.0


def test_close_trade_updates_the_linked_decision():
    trial = ChallengeTrial()
    decision = trial.record_decision(
        "AAPL", "long", 0.65, "RSI oversold", 100.0, 94.0, 109.0, 1.0, "yes")
    trial.record_trade("AAPL", outcome="open", price=100.0, stop_loss=94.0,
                       take_profit=109.0, quantity=1.0, decision_index=0)
    closed = trial.close_trade(0, "win", 45.0)
    assert closed.outcome == "win" and closed.pnl == 45.0
    assert decision.outcome == "win" and decision.pnl == 45.0
    with pytest.raises(ValueError):
        trial.close_trade(0, "open", 0.0)
    with pytest.raises(ValueError):
        trial.record_trade("AAPL", outcome="maybe")


def test_wide6_stop_target_is_6_and_9_percent():
    stop, target = wide6_stop_target(100.0)
    assert stop == 94.0 and target == 109.0
    stop, target = wide6_stop_target(284.78)
    assert stop == 267.69
    assert (target - 284.78) / (284.78 - stop) >= 1.5
    with pytest.raises(ValueError):
        wide6_stop_target(0.0)


def test_build_proposal_carries_evidence_and_risk():
    proposal = build_proposal(
        "AAPL", "long", 0.65, "RSI is 28 — recently oversold.", 100.0, 2.0)
    assert proposal["stop_loss"] == 94.0
    assert proposal["take_profit"] == 109.0
    assert proposal["risk_usd"] == 12.0
    assert proposal["reward_usd"] == 18.0
    assert proposal["risk_reward"] == 1.5
    assert proposal["paper_only"] is True
    text = explain_proposal_plain(proposal)
    assert "RSI is 28" in text
    assert "can't win every time" in text
    assert "PAPER trade" in text
    with pytest.raises(ValueError):
        build_proposal("AAPL", "long", 1.5, "evidence", 100.0)


def test_progress_is_trades_only():
    trial = ChallengeTrial()
    assert trial.progress_pct == 0
    for _ in range(15):
        trial.record_trade("AAPL", outcome="win", pnl=1.0)
    assert trial.progress_pct == 50  # half the trades, no course part
    for _ in range(15):
        trial.record_trade("AAPL", outcome="win", pnl=1.0)
    assert trial.progress_pct == 100
    assert trial.is_complete is True
