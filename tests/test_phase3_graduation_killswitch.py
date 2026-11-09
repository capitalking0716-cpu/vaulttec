"""Phase 3 graduation-gate test — the full coaching → graduation →
supervised automation → kill-switch journey, end to end, in paper mode.
Nothing here touches a broker or real money."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.automation import AutomationEngine
from vaulttec.coach import COACHING_CHECKLIST, Coach
from vaulttec.db.models import Signal, UserProfile


def _graduated_coach() -> Coach:
    coach = Coach()
    for item in COACHING_CHECKLIST:
        coach.complete(item["id"])
    for _ in range(5):
        coach.record_coached_trade()
    return coach


def _profile() -> UserProfile:
    return UserProfile(coaching_stage="graduated", allowed_markets=["stocks"])


def _long_signal() -> Signal:
    return Signal(symbol="AAPL", direction="long", confidence=0.6,
                  evidence="test evidence")


def test_graduation_needs_checklist_trades_and_explicit_confirmation():
    coach = Coach()
    assert not coach.can_graduate()
    assert not coach.graduate(user_confirmed=True)  # nothing done yet
    coach = _graduated_coach()
    assert coach.can_graduate()
    assert coach.progress_pct == 100
    assert not coach.graduate(user_confirmed=False)  # no silent graduation
    assert not coach.graduated
    assert coach.graduate(user_confirmed=True)
    assert coach.graduated


def test_automation_cannot_enable_before_graduation():
    profile = UserProfile(coaching_stage="coached")
    auto = AutomationEngine(profile)
    assert not auto.enable(graduated=False)
    assert not profile.automation_enabled
    assert auto.log[-1]["event"] == "enable_blocked"


def test_automation_works_after_graduation_then_kill_switch_stops_it():
    profile = _profile()
    auto = AutomationEngine(profile)
    assert auto.enable(graduated=True)
    assert auto.enabled
    ok, _ = auto.should_trade(_long_signal())
    assert ok
    # Emergency shutdown: instant, logged, and it stays off.
    auto.kill_switch()
    assert not auto.enabled
    assert profile.automation_enabled is False
    assert auto.paused is True
    assert auto.log[-1]["event"] == "kill_switch"
    ok, reason = auto.should_trade(_long_signal())
    assert not ok
    assert "off or paused" in reason
    # Resuming does NOT silently re-enable trading — the user must
    # enable it again explicitly after graduation.
    auto.resume()
    assert not auto.enabled
    assert auto.enable(graduated=True)
    assert auto.enabled


def test_automation_refuses_wrong_market_low_confidence_and_neutral():
    profile = _profile()
    auto = AutomationEngine(profile)
    auto.enable(graduated=True)
    assert not auto.should_trade(Signal("BTC-USD", "long", 0.8, "crypto not allowed"))[0]
    assert not auto.should_trade(Signal("AAPL", "long", 0.4, "too unsure"))[0]
    assert not auto.should_trade(Signal("AAPL", "neutral", 0.4, "no call"))[0]


def test_full_journey_end_to_end():
    coach = _graduated_coach()
    assert coach.graduate(user_confirmed=True)
    profile = _profile()
    auto = AutomationEngine(profile)
    assert auto.enable(graduated=coach.graduated)
    ok, reason = auto.should_trade(_long_signal())
    assert ok and "within your profile settings" in reason
    auto.kill_switch()
    assert not auto.should_trade(_long_signal())[0]
