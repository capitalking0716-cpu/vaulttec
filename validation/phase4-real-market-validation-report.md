# VaultTec — Phase 4 Real-Market Validation Report

Generated: 2026-11-09T05:03:07.692718 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report proves the paper-trading machinery works — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Walk-forward over delayed real market history from yfinance (180 days requested per symbol, 5-day windows, 10-day exit horizon). Signals used history up to the trade day only — no look-ahead.
- Data: yfinance (delayed real market data, free — Yahoo Finance)
- History: 12 symbols fetched (180 days requested); failed to fetch: none
- Risk profile: balanced — starting virtual cash $10,000.00
- Every trade: stop-loss at entry -3%, take-profit at entry +4.5% (1.5:1 risk/reward), exit at stop, target, or after 10 days.
- Short and neutral signals were skipped and counted, not traded — the paper engine in this build is long-only.

## Results

- **Trades placed: 40** (target 40, brief asks for 30–50) — target met: yes
- Wins: 16 — losses: 24 — win rate: **40.0%**
- Total paper P&L: **$-92.40 (-0.92% of starting cash)**
- Average win: $37.50 — average loss: $-28.85
- Exits: {'take-profit': 12, 'stop-loss': 23, 'time exit (10 days)': 5}
- Windows checked: 81 — skipped (neutral): 7, skipped (short): 34, skipped (already in position): 0
- Blocked by the Risk Engine: 0 {}
- Trades per symbol: {'AAPL': 4, 'NVDA': 3, 'SPY': 4, 'AMZN': 3, 'GOOGL': 3, 'TSLA': 3, 'BTC-USD': 5, 'ETH-USD': 5, 'JNJ': 4, 'MSFT': 2, 'JPM': 4}
- History per symbol (rows, first → last date, last close): AAPL: 180 rows, 2026-02-23 → 2026-11-06, $342.37; MSFT: 180 rows, 2026-02-23 → 2026-11-06, $530.61; NVDA: 180 rows, 2026-02-23 → 2026-11-06, $186.64; SPY: 180 rows, 2026-02-23 → 2026-11-06, $735.29; AMZN: 180 rows, 2026-02-23 → 2026-11-06, $259.30; GOOGL: 180 rows, 2026-02-23 → 2026-11-06, $284.78; META: 180 rows, 2026-02-23 → 2026-11-06, $610.15; TSLA: 180 rows, 2026-02-23 → 2026-11-06, $358.22; JPM: 180 rows, 2026-02-23 → 2026-11-06, $334.49; JNJ: 180 rows, 2026-02-23 → 2026-11-06, $276.22; BTC-USD: 179 rows, 2026-05-14 → 2026-11-09, $74,550.74; ETH-USD: 179 rows, 2026-05-14 → 2026-11-09, $2,134.18

## Backtest suite (same history, all four strategies)

Each strategy ran on every symbol's full fetched history. Historical only — past performance does not guarantee future results.

- SMA crossover: mean total return +1.46%, mean win rate 45.1%, mean max drawdown -7.77%, symbols with trades 12, total trades 36
- MACD crossover: mean total return +8.38%, mean win rate 35.9%, mean max drawdown -9.56%, symbols with trades 12, total trades 81
- RSI mean-reversion: mean total return +12.44%, mean win rate 83.3%, mean max drawdown -2.18%, symbols with trades 12, total trades 20
- Bollinger mean-reversion: mean total return +17.71%, mean win rate 81.2%, mean max drawdown -0.82%, symbols with trades 12, total trades 24

Per-symbol backtest results are in the JSON report.

## What this does and does not prove

Validation on delayed real market history — a genuine out-of-sample test of the signal + risk machinery on prices that actually happened, not a random walk. It still does not prove future profits: one 180-day window, one signal method, long-only, and past performance does not guarantee future results. A real verdict also needs live paper trades over real days, and a compliance/legal review, before any real money is considered.

## Trades (every trade, in order)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $298.71 | $312.16 | take-profit | 5 | +45.02 |
| 2 | NVDA | $220.11 | $213.50 | stop-loss | 4 | -30.15 |
| 3 | SPY | $730.03 | $750.44 | time exit (10 days) | 10 | +28.00 |
| 4 | AMZN | $259.34 | $271.01 | take-profit | 5 | +45.19 |
| 5 | GOOGL | $387.18 | $375.56 | stop-loss | 8 | -30.28 |
| 6 | TSLA | $404.11 | $422.29 | take-profit | 2 | +45.25 |
| 7 | BTC-USD | $62,239.12 | $65,039.88 | take-profit | 1 | +45.37 |
| 8 | ETH-USD | $1,773.50 | $1,853.31 | take-profit | 1 | +45.67 |
| 9 | AAPL | $310.58 | $301.26 | stop-loss | 8 | -30.60 |
| 10 | NVDA | $212.12 | $221.67 | take-profit | 3 | +45.78 |
| 11 | SPY | $746.68 | $724.28 | stop-loss | 9 | -30.62 |
| 12 | AMZN | $271.85 | $263.69 | stop-loss | 3 | -30.55 |
| 13 | GOOGL | $388.35 | $376.70 | stop-loss | 3 | -30.44 |
| 14 | TSLA | $440.36 | $427.15 | stop-loss | 3 | -30.35 |
| 15 | JNJ | $230.15 | $223.25 | stop-loss | 3 | -30.26 |
| 16 | BTC-USD | $64,796.60 | $62,852.70 | stop-loss | 10 | -30.13 |
| 17 | ETH-USD | $1,861.39 | $1,945.16 | take-profit | 3 | +45.12 |
| 18 | AAPL | $309.99 | $300.69 | stop-loss | 4 | -30.23 |
| 19 | MSFT | $426.54 | $413.74 | stop-loss | 2 | -30.13 |
| 20 | NVDA | $214.26 | $207.83 | stop-loss | 2 | -30.05 |
| 21 | SPY | $750.44 | $727.93 | stop-loss | 4 | -29.94 |
| 22 | AMZN | $250.02 | $242.52 | stop-loss | 4 | -29.85 |
| 23 | GOOGL | $358.55 | $347.79 | stop-loss | 6 | -29.76 |
| 24 | TSLA | $423.70 | $410.99 | stop-loss | 2 | -29.67 |
| 25 | BTC-USD | $65,044.81 | $63,093.47 | stop-loss | 5 | -29.47 |
| 26 | ETH-USD | $1,877.10 | $1,961.57 | take-profit | 3 | +44.25 |
| 27 | AAPL | $291.33 | $282.59 | stop-loss | 10 | -29.63 |
| 28 | MSFT | $396.61 | $384.71 | stop-loss | 1 | -29.55 |
| 29 | SPY | $721.77 | $732.48 | time exit (10 days) | 10 | +14.56 |
| 30 | JPM | $306.23 | $320.01 | take-profit | 3 | +44.26 |
| 31 | JNJ | $237.32 | $230.20 | stop-loss | 4 | -29.63 |
| 32 | BTC-USD | $63,871.36 | $64,880.19 | time exit (10 days) | 10 | +15.54 |
| 33 | ETH-USD | $1,919.95 | $1,862.35 | stop-loss | 3 | -29.58 |
| 34 | JPM | $330.32 | $331.32 | time exit (10 days) | 10 | +2.99 |
| 35 | JNJ | $233.05 | $243.54 | take-profit | 5 | +44.27 |
| 36 | ETH-USD | $1,882.52 | $1,878.14 | time exit (10 days) | 10 | -2.30 |
| 37 | JPM | $331.96 | $322.00 | stop-loss | 4 | -29.64 |
| 38 | JNJ | $243.68 | $254.65 | take-profit | 2 | +44.34 |
| 39 | BTC-USD | $64,880.19 | $62,933.79 | stop-loss | 6 | -29.59 |
| 40 | JPM | $331.32 | $346.23 | take-profit | 8 | +44.39 |
