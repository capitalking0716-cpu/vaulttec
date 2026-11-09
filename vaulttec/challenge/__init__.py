"""Challenge Trial — trading platform, not a school. Paper only.

$20 is the user's own starting capital; VaultTec takes nothing from
it. Pass = 30 paper trades in 1 month (win or lose). No course, no
Academy — the course gate was removed 2026-11-09. AI proposes, the
user decides YES or NO. Live trading is NOT built — it needs a
compliance/legal check first. No payments, no broker, no real money.
"""
from .challenge import (
    CHALLENGE_MIN_RISK_REWARD,
    CHALLENGE_REQUIRED_TRADES,
    CHALLENGE_STARTING_CAPITAL,
    CHALLENGE_STARTING_CAPITAL_LABEL,
    CHALLENGE_STOP_PCT,
    CHALLENGE_SUBSCRIPTIONS,
    CHALLENGE_TARGET_PCT,
    LIVE_NOT_AVAILABLE,
    NO_REASONS,
    ChallengeDecision,
    ChallengeTrade,
    ChallengeTrial,
    build_proposal,
    explain_proposal_plain,
    wide6_stop_target,
)

__all__ = [
    "CHALLENGE_MIN_RISK_REWARD",
    "CHALLENGE_REQUIRED_TRADES",
    "CHALLENGE_STARTING_CAPITAL",
    "CHALLENGE_STARTING_CAPITAL_LABEL",
    "CHALLENGE_STOP_PCT",
    "CHALLENGE_SUBSCRIPTIONS",
    "CHALLENGE_TARGET_PCT",
    "LIVE_NOT_AVAILABLE",
    "NO_REASONS",
    "ChallengeDecision",
    "ChallengeTrade",
    "ChallengeTrial",
    "build_proposal",
    "explain_proposal_plain",
    "wide6_stop_target",
]
