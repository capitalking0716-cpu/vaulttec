# VaultTec PRIVATE — Neko only

**This is not the public VaultTec product.** This module is a
private tool for Neko's own money only. No customers. No other
people's money. No subscriptions, no Challenge Trial, no sales
site. It does not touch the public code paths except to reuse the
shared Risk Engine and the mean-reversion trigger.

## What it is

- The same wide-6 rules that were validated on past prices:
  RSI < 30 or price at/below the Bollinger lower band, long-only,
  **6% stop-loss / 9% take-profit (1.5:1)**, 10-day time exit.
- Connected to **Alpaca** (paper account first, live only when
  Neko explicitly unlocks it — see below).
- **Approval first:** by default it only *proposes* trades. Neko
  says YES/NO before anything is placed. Supervised automation
  is a separate, explicit opt-in.
- Every order is a **bracket order** at the broker: the stop-loss
  and take-profit live at Alpaca, so the trade is protected even
  if VaultTec's computer is off.
- Every order goes through the shared **Risk Engine**: stop-loss
  required, position sizing, daily loss limit, max exposure, no
  leverage, no options. A blocked trade is logged, never placed,
  never silently shrunk to fit.
- Kill-switch: create `private_live/STOP` and nothing trades
  until it is deleted.

## The honest maths on $20–$50

This is the part that matters, because Neko's goal for this
module is to fund the attorney/legal costs for the public launch.

- With $50, the position cap (10% of the account) allows a
  **$5.00 position** per trade. The 6% stop means the most you
  lose on that trade is **$0.30**. The 9% target means the most
  you gain is **$0.45**.
- With $20, it is a **$2.00 position**, **$0.12** risked,
  **$0.18** targeted.
- The backtests (Phase 4d, fresh windows) made about **+$1,226
  (RSI) and +$1,043 (Bollinger) on a $10,000 virtual account**
  over 180 days — roughly +10–12% in six months. At that same
  rate, $50 makes about **$5–$6 in six months**. That is the
  honest scale: $20–$50 is a *test amount*, not a funding plan.
- To make real attorney money from trading, the account has to be
  much bigger — or the strategy has to be much better than the
  tests show so far. The tests so far are **promising, not
  proven**: the live paper run is only on Day 1 (3 trades open,
  0 closed, $0.00 realised as of 2026-11-09).

So: use this module to **learn the system with real money at
test size, and to prove the mechanics work** (orders fill, stops
fire, the log is honest). Do not count on it to pay legal fees
in the near term. If it grows, scale the account deliberately —
never on the basis of backtests alone.

## What it is NOT

- Not the public product, not for customers, not a promise of
  profit. Past performance does not guarantee future results.
- Not live by default. Live trading is locked OFF and needs
  three separate locks opened (see RUNBOOK.md). Paper mode is
  the default and needs no confirmation.
- Not a way around the attorney review for the *public* product.
  This private module is Neko trading his own money; selling
  VaultTec to other people still needs the clinic/attorney review
  first.
- Crypto: Alpaca paper supports BTC/USD and ETH/USD. If Alpaca
  rejects a crypto order (availability, fractional rules), the
  runner logs it and skips it — it never substitutes another
  symbol.

## Files

| File | What it is |
|---|---|
| `config.py` | Keys from `.env` only; the three-lock live gate |
| `broker.py` | Alpaca REST connector (stdlib only) + DryRunBroker |
| `strategy.py` | Wide-6 trigger reuse + small-capital sizing |
| `runner.py` | Daily scan / approve / status / kill CLI |
| `RUNBOOK.md` | Exact steps: Alpaca paper account → keys → run → live |
| `state.json` | Durable state (account, positions, proposals) |
| `proposals.json` | Pending proposals awaiting Neko's YES/NO |
| `trades.jsonl` | Append-only log of every proposal, order, exit |
| `report.md` | Regenerated summary after every run |
| `STOP` | Kill-switch file — create it to stop everything |
| `LIVE_CONFIRMATION.txt` | Live lock #3 — only Neko creates this, by hand |
| `automation-enabled.json` | Automation opt-in — only Neko creates this, by hand |
