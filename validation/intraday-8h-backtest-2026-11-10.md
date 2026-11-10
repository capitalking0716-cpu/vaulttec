# VaultTec — Intraday 8-Hour Backtest (paper only, $100 pot)

> **PAPER ONLY — virtual money, no live brokerage, no real money. Trading involves substantial risk of loss. This backtest does not promise profits. Past performance does not guarantee future results.**

## What was tested

- System: intraday paper trading, wide-6 mean-reversion (RSI + Bollinger, 6% stop / 9% target, 1.5:1, 10-session time exit, long-only, balanced profile).
- Window: the most recent **8 completed hourly market bars** per symbol, as of 2026-11-10T12:18 (America/New_York).
- Symbols: AAPL, MSFT, NVDA, SPY, AMZN, GOOGL, META, TSLA, JPM, JNJ, BTC-USD, ETH-USD
- Virtual pot: **$100.00** — same size as Ava's $100 pot, at Neko's request. Position size is 10% of the pot per trade (~$10), fractional shares the way Alpaca paper does.

## The 8 bars tested

- AAPL: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- AMZN: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- BTC-USD: 2026-11-09T10:00:00 → 2026-11-10T11:00:00 (8 bars)
- ETH-USD: 2026-11-09T10:00:00 → 2026-11-10T11:00:00 (8 bars)
- GOOGL: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- JNJ: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- JPM: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- META: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- MSFT: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- NVDA: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- SPY: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)
- TSLA: 2026-11-09T10:30:00 → 2026-11-10T10:30:00 (8 bars)

## Result — total

- Trades opened: **4**
- Trades closed: **1** — wins: **0** — losses: **1**
- Total realised profit: **$-0.59 (-0.59% of the $100 pot)**
- Cash left: **$72.00** — portfolio value (cash + holdings at last close): **$99.02**
- Unrealised P&L on open positions: **$-0.40** (paper value, not profit)
- Win rate: 0.0% — average win: $0.00 — average loss: $-0.59 — expectancy: $-0.59 per trade
- Blocked by risk: 0

## Per-symbol (closed trades)

- ETH-USD: 1 trades, 0 wins, P&L $-0.59

## Trades that closed

| Symbol | Entry | Exit | Reason | P&L ($) |
|---|---|---|---|---:|
| ETH-USD | $2,145.08 (2026-11-09) | $2,016.38 (2026-11-10) | stop-loss | -0.59 |

## Still open at the end of the 8 hours — not wins or losses

| Symbol | Entry | Qty | Stop | Target | Last close | Unrealised ($) |
|---|---|---:|---:|---:|---:|---:|
| BTC-USD | $75,431.23 (2026-11-09) | 0.0001 | $70,905.35 | $82,220.05 | $72,811.31 | -0.26 |
| ETH-USD | $2,016.88 (2026-11-10) | 0.0049 | $1,895.87 | $2,198.40 | $2,016.88 | -0.00 |
| NVDA | $171.41 (2026-11-10) | 0.0583 | $161.13 | $186.85 | $169.03 | -0.14 |

## What this does and does not prove

- 8 hours is a very short window. A 6% stop / 9% target almost never triggers inside one session, and the 10-session time exit cannot fire inside 8 bars spanning 2 sessions — so few or zero closed trades is the expected outcome, not a failure of the system.
- The amounts are small by design: on a $100 pot a 9% win on a ~$10 position is about $0.90. Cents, not dollars.
- Wide-6 was validated on daily bars, not hourly ones. Hourly wide-6 is an unvalidated experiment — this number is a data point, not proof of anything.
- A compliance/legal review is still required before any real money is considered. Past performance does not guarantee future results.
