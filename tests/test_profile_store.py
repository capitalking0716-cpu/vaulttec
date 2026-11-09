"""Profile memory test — the app must remember who the user is and
what risk limits they set, across restarts. A reset profile on a
trading app is a safety bug: limits would silently reset too."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vaulttec.db.models import UserProfile
from vaulttec.profile_store import load_profile, profile_snapshot, save_profile


def test_profile_round_trip_remembers_identity_and_limits(tmp_path):
    path = tmp_path / "profile.json"
    profile = UserProfile(
        name="Neko Robinson",
        goal="Grow steadily",
        risk_tolerance="growth",
        max_position_pct=0.15,
        daily_loss_limit_pct=0.03,
        allowed_markets=["stocks", "crypto"],
    )
    save_profile(profile, path)
    loaded = load_profile(path)
    assert loaded.name == "Neko Robinson"
    assert loaded.goal == "Grow steadily"
    assert loaded.risk_tolerance == "growth"
    assert loaded.max_position_pct == 0.15
    assert loaded.daily_loss_limit_pct == 0.03
    assert loaded.allowed_markets == ["stocks", "crypto"]


def test_missing_profile_returns_defaults(tmp_path):
    loaded = load_profile(tmp_path / "nope.json")
    assert loaded.name == "Trader"
    assert loaded.risk_tolerance == "balanced"


def test_corrupt_profile_returns_defaults_not_crash(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_profile(path).name == "Trader"


def test_no_secrets_are_saved(tmp_path):
    path = tmp_path / "profile.json"
    save_profile(UserProfile(name="Neko"), path)
    text = path.read_text(encoding="utf-8")
    assert "ALPACA" not in text and "password" not in text.lower()
    assert profile_snapshot(UserProfile(name="Neko"))["name"] == "Neko"
