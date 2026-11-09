"""Persistent profile memory for the VaultTec app.

The profile used to live only in Streamlit session state, so every time
the app was closed and reopened it forgot who the user is and asked
again. That is dangerous for a trading app: a reset profile means reset
risk limits, and a user could trade under the wrong limits without
noticing.

Now the profile is saved to a local JSON file (``data/profile.json``)
on every change and loaded on startup. The file is local-only — it is
inside ``data/``, which is gitignored and never pushed to GitHub — so
the identity stays on this machine and is never shared.

No secrets are stored here: no passwords, no API keys, no brokerage
credentials. Those stay in Streamlit Secrets / environment variables.
Only identity and risk settings: name, goal, risk tolerance, position
limits, loss limits, allowed markets.
"""
from __future__ import annotations

import json
from pathlib import Path

from vaulttec.db.models import UserProfile

PROFILE_FIELDS = (
    "name",
    "goal",
    "risk_tolerance",
    "virtual_capital",
    "max_position_pct",
    "daily_loss_limit_pct",
    "allowed_markets",
    "automation_enabled",
)


def default_profile_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "profile.json"


def load_profile(path: Path | str | None = None) -> UserProfile:
    """Load the saved profile, or a fresh default when none is saved."""
    path = Path(path) if path is not None else default_profile_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return UserProfile()
    if not isinstance(raw, dict):
        return UserProfile()
    kept = {k: raw[k] for k in PROFILE_FIELDS if k in raw}
    # Guard the types the app depends on: a bad saved value must never
    # crash startup or silently widen a risk limit.
    try:
        kept["virtual_capital"] = float(kept.get("virtual_capital", 10_000.00))
        kept["max_position_pct"] = float(kept.get("max_position_pct", 0.10))
        kept["daily_loss_limit_pct"] = float(kept.get("daily_loss_limit_pct", 0.02))
    except (TypeError, ValueError):
        return UserProfile()
    if not isinstance(kept.get("allowed_markets", ["stocks"]), list):
        kept["allowed_markets"] = ["stocks"]
    kept["allowed_markets"] = [
        m for m in kept["allowed_markets"] if m in ("stocks", "crypto")
    ] or ["stocks"]
    if kept.get("risk_tolerance") not in ("conservative", "balanced", "growth"):
        kept["risk_tolerance"] = "balanced"
    return UserProfile(**kept)


def save_profile(profile: UserProfile, path: Path | str | None = None) -> Path:
    """Save the profile to disk. Returns the path written."""
    path = Path(path) if path is not None else default_profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {k: getattr(profile, k) for k in PROFILE_FIELDS}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def profile_snapshot(profile: UserProfile) -> dict:
    """A comparable snapshot of the saved fields, for change detection."""
    return {k: getattr(profile, k) for k in PROFILE_FIELDS}
