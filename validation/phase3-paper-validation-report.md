# VaultTec — Phase 3 Paper-Trading Validation Report

Generated: 2026-11-09T02:35:41.009478 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report proves the paper-trading machinery works — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Walk-forward over deterministic offline sample history (180 days per symbol, 5-day windows, 10-day exit horizon). Signals used history up to the trade day only — no look-ahead.
- Data: sample (offline demo data — a random walk, NOT real market data)
- Risk profile: balanced — starting virtual cash $10,000.00
- Every trade: stop-loss at entry -3%, take-profit at entry +4.5% (1.5:1 risk/reward), exit at stop, target, or after 10 days.
- Short and neutral signals were skipped and counted, not traded — the paper engine in this build is long-only.

## Results

- **Trades placed: 40** (target 40, brief asks for 30–50) — target met: yes
- Wins: 24 — losses: 16 — win rate: **60.0%**
- Total paper P&L: **$490.49 (+4.90% of starting cash)**
- Average win: $32.51 — average loss: $-18.11
- Exits: {'stop-loss': 6, 'take-profit': 13, 'time exit (10 days)': 21}
- Windows checked: 63 — skipped (neutral): 9, skipped (short): 14, skipped (already in position): 0
- Blocked by the Risk Engine: 0 {}
- Trades per symbol: {'AAPL': 3, 'NVDA': 6, 'SPY': 5, 'GOOGL': 2, 'META': 5, 'TSLA': 3, 'JPM': 3, 'JNJ': 5, 'BTC-USD': 2, 'ETH-USD': 2, 'AMZN': 2, 'MSFT': 2}

## What this does and does not prove

Validation of the machinery on sample data, not proof of future profits. Sample history is a random walk, so the win rate here says more about the sample data than about the strategy. A real verdict needs the same run on real market history and the 30–50 live paper trades in Phase 3 of the brief. Past performance does not guarantee future results.

## Trades (every trade, in order)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $232.92 | $225.93 | stop-loss | 4 | -30.01 |
| 2 | NVDA | $124.72 | $130.33 | take-profit | 7 | +44.85 |
| 3 | SPY | $546.58 | $571.19 | take-profit | 8 | +45.09 |
| 4 | GOOGL | $167.05 | $168.91 | time exit (10 days) | 10 | +11.20 |
| 5 | META | $599.59 | $596.04 | time exit (10 days) | 10 | -5.96 |
| 6 | TSLA | $267.26 | $264.26 | time exit (10 days) | 10 | -11.30 |
| 7 | JPM | $264.62 | $256.68 | stop-loss | 4 | -30.17 |
| 8 | JNJ | $161.18 | $164.22 | time exit (10 days) | 10 | +18.91 |
| 9 | BTC-USD | $96,897.89 | $95,567.92 | time exit (10 days) | 10 | -13.70 |
| 10 | ETH-USD | $3,475.43 | $3,371.17 | stop-loss | 8 | -30.08 |
| 11 | AAPL | $224.51 | $225.82 | time exit (10 days) | 10 | +5.83 |
| 12 | NVDA | $127.27 | $131.23 | time exit (10 days) | 10 | +31.13 |
| 13 | SPY | $555.49 | $580.48 | take-profit | 9 | +45.15 |
| 14 | AMZN | $218.49 | $211.94 | stop-loss | 4 | -30.22 |
| 15 | META | $601.05 | $612.74 | time exit (10 days) | 10 | +19.55 |
| 16 | TSLA | $267.51 | $266.54 | time exit (10 days) | 10 | -3.65 |
| 17 | JPM | $258.53 | $259.54 | time exit (10 days) | 10 | +3.93 |
| 18 | JNJ | $162.23 | $169.54 | take-profit | 10 | +45.38 |
| 19 | BTC-USD | $95,069.83 | $92,814.96 | time exit (10 days) | 10 | -23.90 |
| 20 | ETH-USD | $3,435.32 | $3,332.26 | stop-loss | 5 | -30.27 |
| 21 | NVDA | $127.73 | $133.48 | take-profit | 6 | +45.29 |
| 22 | SPY | $575.95 | $577.74 | time exit (10 days) | 10 | +3.14 |
| 23 | META | $596.04 | $622.86 | take-profit | 6 | +45.49 |
| 24 | TSLA | $264.26 | $270.98 | time exit (10 days) | 10 | +25.82 |
| 25 | JNJ | $164.22 | $171.62 | take-profit | 6 | +45.88 |
| 26 | NVDA | $131.23 | $137.14 | take-profit | 4 | +46.06 |
| 27 | SPY | $588.48 | $583.40 | time exit (10 days) | 10 | -8.87 |
| 28 | GOOGL | $171.24 | $166.10 | stop-loss | 6 | -30.81 |
| 29 | META | $612.74 | $630.99 | time exit (10 days) | 10 | +30.48 |
| 30 | JNJ | $171.43 | $179.15 | take-profit | 6 | +46.22 |
| 31 | AAPL | $228.48 | $226.61 | time exit (10 days) | 10 | -8.44 |
| 32 | MSFT | $392.36 | $410.02 | take-profit | 3 | +46.37 |
| 33 | NVDA | $136.86 | $135.90 | time exit (10 days) | 10 | -7.26 |
| 34 | SPY | $577.74 | $603.74 | take-profit | 7 | +46.54 |
| 35 | AMZN | $218.51 | $228.35 | take-profit | 10 | +46.78 |
| 36 | META | $615.30 | $603.78 | time exit (10 days) | 10 | -19.54 |
| 37 | JPM | $262.98 | $267.94 | time exit (10 days) | 10 | +19.64 |
| 38 | JNJ | $178.58 | $181.06 | time exit (10 days) | 10 | +14.49 |
| 39 | MSFT | $410.96 | $429.46 | take-profit | 5 | +47.04 |
| 40 | NVDA | $139.05 | $138.31 | time exit (10 days) | 10 | -5.59 |
