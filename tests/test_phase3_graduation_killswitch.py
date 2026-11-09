"""Phase 3 automation test — user choice → supervised automation →
kill-switch, end to end, in paper mode. No coaching stage, no
graduation gate: VaultTec is a trading platform, not a school.
Nothing here touches a broker or real money."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.automation import AutomationEngine
from vaulttec.db.models import Signal, UserProfile


def _profile() -> UserProfile:
    return UserProfile(allowed_markets=["stocks"])


def _long_signal() -> Signal:
    return Signal(symbol="AAPL", direction="long", confidence=0.6,
                  evidence="test evidence")


def test_profile_has_no_coaching_stage():
    profile = _profile()
    assert not hasattr(profile, "coaching_stage")
    assert not hasattr(profile, "coached_trades_done")


def test_automation_enables_by_user_choice_only():
    profile = _profile()
    auto = AutomationEngine(profile)
    assert not auto.enabled
    assert auto.enable()
    assert auto.enabled
    assert profile.automation_enabled


def test_automation_works_then_kill_switch_stops_it():
    profile = _profile()
    auto = AutomationEngine(profile)
    assert auto.enable()
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
    # enable it again explicitly.
    auto.resume()
    assert not auto.enabled
    assert auto.enable()
    assert auto.enabled


def test_automation_refuses_wrong_market_low_confidence_and_neutral():
    profile = _profile()
    auto = AutomationEngine(profile)
    auto.enable()
    assert not auto.should_trade(Signal("BTC-USD", "long", 0.8, "crypto not allowed"))[0]
    assert not auto.should_trade(Signal("AAPL", "long", 0.4, "too unsure"))[0]
    assert not auto.should_trade(Signal("AAPL", "neutral", 0.4, "no call"))[0]


def test_full_journey_end_to_end():
    profile = _profile()
    auto = AutomationEngine(profile)
    assert auto.enable()
    ok, reason = auto.should_trade(_long_signal())
    assert ok and "within your profile settings" in reason
    auto.kill_switch()
    assert not auto.should_trade(_long_signal())[0]
