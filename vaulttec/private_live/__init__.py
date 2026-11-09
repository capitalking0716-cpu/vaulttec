"""VaultTec PRIVATE live-trading module — Neko only.

This is NOT the public VaultTec product. It is a separate, private
tool for Neko's own money only: no customers, no other people's
money, no subscriptions, no Challenge Trial, no sales site.

Paper first, always. Live trading is locked OFF by default and
refuses to run unless ALL of these are true:
  1. environment ``VAULTTEC_LIVE_TRADING_ENABLED=true``
  2. environment ``ALPACA_PAPER=false`` (paper is the default)
  3. the file ``private_live/LIVE_CONFIRMATION.txt`` exists and
     contains the exact confirmation text (see ``config.py``)

Every order still goes through the shared Risk Engine
(stop-loss required, position sizing, daily loss limit, max
exposure, no leverage, no options) and, by default, the module
only PROPOSES trades — Neko says YES/NO before anything is
placed. Supervised automation is a separate explicit opt-in.

No profit is promised anywhere. Past paper results do not
guarantee future results. This is Neko's own money at risk.
"""
from __future__ import annotations

STRATEGY_ID = "wide-6-private"
STOP_PCT = 0.06
TAKE_PCT = 0.09  # 9% reward vs 6% risk = 1.5:1, the profile minimum
HORIZON_BARS = 10  # time exit after 10 daily bars held
RISK_REWARD = 1.5

# Small-capital rules (the whole point of this module is starting
# small). Risk per trade is capped at 2% of the account, and no
# single position is more than 10% of the account (balanced
# profile). On a $50 account that is $1.00 of risk per trade and a
# $5.00 position — see README.md for the honest maths on what
# $20–$50 can and cannot do.
MAX_RISK_PER_TRADE_PCT = 0.02
MAX_POSITION_PCT = 0.10

PRIVATE_ONLY_BANNER = (
    "PRIVATE — Neko only. Not the public VaultTec product. "
    "No customers, no other people's money. Trading involves "
    "substantial risk of loss. No profit is promised. Past "
    "performance does not guarantee future results."
)
