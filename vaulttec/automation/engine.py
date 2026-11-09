"""Automation Engine — Stage 3 (supervised automation, paper only).

Automation proposes and places paper trades ONLY:
- inside the user's profile settings (risk tolerance, max position,
  daily loss limit, allowed markets),
- after the Risk Engine approves them,
- with the user's explicit authorisation (automation_enabled),
- and with a kill-switch that stops everything instantly.

It never bypasses risk controls, never trades beyond the profile,
and every decision is logged with its reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..db.models import Signal, UserProfile


@dataclass
class AutomationEngine:
    profile: UserProfile
    log: list = field(default_factory=list)
    paused: bool = False

    def _record(self, event: str, detail: str) -> None:
        self.log.append({"event": event, "detail": detail,
                         "at": datetime.utcnow().isoformat()})

    @property
    def enabled(self) -> bool:
        """Automation runs only if the user enabled it AND it is not paused."""
        return self.profile.automation_enabled and not self.paused

    def enable(self) -> bool:
        """Enable by the user's explicit choice. No coaching stage,
        no graduation gate — VaultTec is a trading platform, not a school.
        Paper only, and the Risk Engine still approves every trade."""
        self.profile.automation_enabled = True
        self._record("enabled", "Automation enabled by user choice.")
        return True

    def kill_switch(self) -> None:
        """Emergency shutdown — stops all automated trading immediately."""
        self.paused = True
        self.profile.automation_enabled = False
        self._record("kill_switch", "Automation stopped by kill-switch.")

    def resume(self) -> None:
        self.paused = False
        self._record("resumed", "Automation resumed by user.")

    def should_trade(self, signal: Signal) -> tuple[bool, str]:
        """Decide whether an automated paper trade may be proposed for a signal."""
        if not self.enabled:
            return False, "Automation is off or paused."
        if signal.direction == "neutral":
            return False, f"No clear direction for {signal.symbol} — skipping."
        if signal.confidence < 0.50:
            return False, f"Confidence {signal.confidence:.0%} is too low to automate."
        # Allowed markets check: crypto symbols end in -USD in this app.
        is_crypto = signal.symbol.endswith("-USD")
        if is_crypto and "crypto" not in self.profile.allowed_markets:
            return False, f"{signal.symbol} is crypto, which is not in your allowed markets."
        if not is_crypto and "stocks" not in self.profile.allowed_markets:
            return False, f"{signal.symbol} is a stock, which is not in your allowed markets."
        return True, (
            f"Automated paper trade proposed for {signal.symbol} ({signal.direction}, "
            f"confidence {signal.confidence:.0%}) — within your profile settings. "
            f"Evidence: {signal.evidence}"
        )
