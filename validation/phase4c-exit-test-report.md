# VaultTec — Phase 4c Exit Test Report

Generated: 2026-11-09T05:27:34.450311 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests exit rules on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Exit test on the SAME three out-of-sample windows as Phase 4b (OOS-1, OOS-2, OOS-3) plus the Phase 4 window re-run and labelled in-sample: delayed real market history from yfinance (free), 70 days of warm-up history before each window so the SMA-50 filter is defined on day one, 12 symbols, 5-day walk-forward steps, signals from history up to the trade day only — no look-ahead. Every trade goes through the real PaperTradingEngine and Risk Engine, balanced profile, $10,000 virtual cash, long-only. Every variant keeps a stop-loss; the stop is never removed.
- Data: yfinance (delayed real market data, free — Yahoo Finance)
- Downtrend filter: Skip the buy when BOTH hold on the trade day (history up to that day only): (a) the close is below its 50-day simple moving average, and (b) that 50-day average is falling — today's SMA-50 is below the SMA-50 of 10 bars ago. If the SMA-50 is not yet defined, the filter does NOT block.
- Combined-variant selection: Per strategy, the base variant with the highest pooled out-of-sample total paper P&L among wide-5, wide-6, time-5d and signal-exit, run with the downtrend filter added. Post-hoc — chosen after seeing the base results on these same windows.
- Verdict rules: A variant 'survives OOS-2' when its OOS-2 paper P&L is >= $0. A variant is 'worth keeping' when its pooled out-of-sample P&L is > $0 AND it survives OOS-2. At 1.5:1 risk/reward the break-even win rate is exactly 40%.

## Exit variants tested

- **baseline** — Baseline — 3% stop / 4.5% target / 10 days: 3% stop / 4.5% target / 10-day exit, filter off, signal exit off. Phase 4b Variant A control, re-run as a sanity check.
- **wide-5** — Wider stop — 5% stop / 7.5% target / 10 days: 5% stop / 7.5% target / 10-day exit, filter off, signal exit off. Wider stop so normal daily wobbles do not stop the trade out; target widens to keep 1.5:1.
- **wide-6** — Wider stop — 6% stop / 9% target / 10 days: 6% stop / 9.0% target / 10-day exit, filter off, signal exit off. Even wider stop; target widens to keep 1.5:1.
- **filter** — Downtrend filter — 3% stop / 4.5% target / 10 days + filter: 3% stop / 4.5% target / 10-day exit, filter on, signal exit off. Same exits as baseline, but oversold buys are skipped while the downtrend filter says the market is falling.
- **time-5d** — Time-based exit — 3% stop / 4.5% target / 5 days: 3% stop / 4.5% target / 5-day exit, filter off, signal exit off. Half the holding time: if the bounce has not happened in 5 days, exit instead of waiting 10.
- **signal-exit** — Signal exit — 3% stop, no fixed target, exit on reversal / 10 days: 3% stop / no fixed target / 10-day exit, filter off, signal exit on. Stop still protects every trade; otherwise hold until the entry signal reverses (RSI > 70 / close >= upper band) or 10 days pass. No fixed target — the Risk Engine is passed no target.
- **combined-wide-5-filter** — Combined — Wider stop — 5% stop / 7.5% target / 10 days + downtrend filter: 5% stop / 7.5% target / 10-day exit, filter on, signal exit off. Wider stop so normal daily wobbles do not stop the trade out; target widens to keep 1.5:1. PLUS the downtrend filter: oversold buys are skipped while the market is in a downtrend. Post-hoc: the base variant was chosen after seeing the base results on these same windows, so this result needs a fresh window to confirm.
- **combined-wide-5-filter** — Combined — Wider stop — 5% stop / 7.5% target / 10 days + downtrend filter: 5% stop / 7.5% target / 10-day exit, filter on, signal exit off. Wider stop so normal daily wobbles do not stop the trade out; target widens to keep 1.5:1. PLUS the downtrend filter: oversold buys are skipped while the market is in a downtrend. Post-hoc: the base variant was chosen after seeing the base results on these same windows, so this result needs a fresh window to confirm.

## Pooled out-of-sample verdict — 3 windows, per strategy

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy / trade | OOS-2 P&L | Survives OOS-2 | Worth keeping |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| baseline | 67 | 47.8% | $341.61 | $5.10 | $-398.34 | NO | no |
| wide-5 | 67 | 59.7% | $1,517.23 | $22.65 | $-41.05 | NO | no |
| wide-6 | 67 | 59.7% | $1,441.19 | $21.51 | $63.26 | yes | yes |
| filter | 32 | 53.1% | $267.68 | $8.37 | $-208.42 | NO | no |
| time-5d | 70 | 50.0% | $417.33 | $5.96 | $-348.71 | NO | no |
| signal-exit | 67 | 41.8% | $843.58 | $12.59 | $-439.76 | NO | no |
| combined-wide-5-filter | 32 | 56.2% | $532.13 | $16.63 | $-332.97 | NO | no |

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy / trade | OOS-2 P&L | Survives OOS-2 | Worth keeping |
|---|---:|---:|---:|---:|---:|:---:|:---:|
| baseline | 40 | 42.5% | $27.76 | $0.69 | $-238.19 | NO | no |
| wide-5 | 40 | 65.0% | $888.92 | $22.22 | $352.19 | yes | yes |
| wide-6 | 40 | 65.0% | $880.48 | $22.01 | $482.00 | yes | yes |
| filter | 17 | 58.8% | $191.95 | $11.29 | $14.55 | yes | yes |
| time-5d | 42 | 40.5% | $-115.00 | $-2.74 | $-238.19 | NO | no |
| signal-exit | 40 | 35.0% | $-103.42 | $-2.59 | $-289.37 | NO | no |
| combined-wide-5-filter | 17 | 70.6% | $376.36 | $22.14 | $24.26 | yes | yes |

## Verdict

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Best variant by pooled out-of-sample P&L: **wide-5** ($1,517.23).
- Variants surviving OOS-2 (the falling window): ['wide-6'].
- Variants worth keeping (pooled P&L > $0 AND survives OOS-2): ['wide-6'].
- Combined variant: combined-wide-5-filter — Highest pooled out-of-sample total paper P&L among ['wide-5', 'wide-6', 'time-5d', 'signal-exit'] for RSI mean-reversion (buy RSI < 30, sell RSI > 70) ($1,517.23). Post-hoc selection on these same windows — needs a fresh window to confirm.

### Bollinger mean-reversion (buy lower band, sell upper band)

- Best variant by pooled out-of-sample P&L: **wide-5** ($888.92).
- Variants surviving OOS-2 (the falling window): ['wide-5', 'wide-6', 'filter', 'combined-wide-5-filter'].
- Variants worth keeping (pooled P&L > $0 AND survives OOS-2): ['wide-5', 'wide-6', 'filter', 'combined-wide-5-filter'].
- Combined variant: combined-wide-5-filter — Highest pooled out-of-sample total paper P&L among ['wide-5', 'wide-6', 'time-5d', 'signal-exit'] for Bollinger mean-reversion (buy lower band, sell upper band) ($888.92). Post-hoc selection on these same windows — needs a fresh window to confirm.

## Reading it honestly

A wider stop lets the trade survive normal wobbles, but it also lets a real fall run further before the stop catches it — the average loss grows with the stop, so the win rate has to rise enough to pay for bigger losses. A downtrend filter throws away trades, including some that would have bounced, and it only helps if the falling windows are where the losses actually came from. A 5-day exit cuts losing trades short, but it also cuts winning bounces short. A signal exit has no fixed target, so a few big winners can carry it — or a few big losers can sink it — and its expectancy, not its win rate, is the number that matters. None of these variants removes the stop-loss: the stop is what keeps one bad trade from wiping out the account, and the no-stop backtest numbers from Phase 4b overstate what a tradeable strategy earns for exactly that reason. One quirk worth knowing: this codebase's RSI is undefined after 14 straight up-days, so a reversal that is a straight 14-day rise never registers as RSI > 70 and the signal-exit variant then closes on the 10-day time exit instead.

## OOS-1 — 2025-08-27 → 2026-02-23 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 25 | 56.0% | $267.20 | $10.69 | $43.09 | $-30.56 | -0.74% | {'stop-loss': 11, 'take-profit': 13, 'time exit (10 days)': 1} | 0 | 0 |
| wide-5 | 25 | 60.0% | $536.30 | $21.45 | $67.57 | $-47.73 | -1.25% | {'stop-loss': 9, 'take-profit': 10, 'time exit (10 days)': 6} | 0 | 0 |
| wide-6 | 25 | 56.0% | $304.61 | $12.18 | $66.23 | $-56.61 | -2.14% | {'stop-loss': 10, 'take-profit': 6, 'time exit (10 days)': 9} | 0 | 0 |
| filter | 8 | 62.5% | $135.67 | $16.96 | $45.12 | $-29.98 | -0.60% | {'stop-loss': 3, 'take-profit': 5} | 0 | 17 |
| time-5d | 27 | 51.9% | $265.15 | $9.82 | $44.53 | $-27.56 | -0.90% | {'time exit (5 days)': 3, 'stop-loss': 11, 'take-profit': 13} | 0 | 0 |
| signal-exit | 25 | 48.0% | $666.77 | $26.67 | $89.37 | $-31.20 | -1.48% | {'stop-loss': 13, 'time exit (10 days)': 7, 'signal exit (reversal)': 5} | 0 | 0 |
| combined-wide-5-filter | 8 | 62.5% | $205.04 | $25.63 | $62.77 | $-36.28 | -1.00% | {'stop-loss': 2, 'time exit (10 days)': 4, 'take-profit': 2} | 0 | 17 |

- baseline per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- wide-5 per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- wide-6 per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- filter per symbol: {'AAPL': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- time-5d per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 5}
- signal-exit per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- combined-wide-5-filter per symbol: {'AAPL': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 15 | 46.7% | $74.28 | $4.95 | $45.08 | $-30.16 | -1.19% | {'stop-loss': 8, 'take-profit': 7} | 0 | 0 |
| wide-5 | 15 | 66.7% | $273.42 | $18.23 | $51.29 | $-47.90 | -0.90% | {'stop-loss': 4, 'time exit (10 days)': 8, 'take-profit': 3} | 0 | 0 |
| wide-6 | 15 | 60.0% | $105.22 | $7.01 | $49.13 | $-56.16 | -1.55% | {'stop-loss': 5, 'time exit (10 days)': 9, 'take-profit': 1} | 0 | 0 |
| filter | 8 | 50.0% | $59.64 | $7.46 | $44.91 | $-30.00 | -0.60% | {'stop-loss': 4, 'take-profit': 4} | 0 | 7 |
| time-5d | 17 | 41.2% | $-49.17 | $-2.89 | $30.08 | $-25.97 | -2.09% | {'time exit (5 days)': 6, 'take-profit': 3, 'stop-loss': 8} | 0 | 0 |
| signal-exit | 15 | 40.0% | $-8.65 | $-0.58 | $43.58 | $-30.01 | -1.19% | {'stop-loss': 9, 'time exit (10 days)': 5, 'signal exit (reversal)': 1} | 0 | 0 |
| combined-wide-5-filter | 8 | 75.0% | $203.49 | $25.44 | $48.18 | $-42.78 | -0.86% | {'stop-loss': 1, 'time exit (10 days)': 6, 'take-profit': 1} | 0 | 7 |

- baseline per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- wide-5 per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- wide-6 per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- filter per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 1, 'AMZN': 1, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- time-5d per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- signal-exit per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- combined-wide-5-filter per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 1, 'AMZN': 1, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}

## OOS-2 — 2025-02-28 → 2025-08-27 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 21 | 14.3% | $-398.34 | $-18.97 | $43.68 | $-29.41 | -4.69% | {'take-profit': 3, 'stop-loss': 18} | 0 | 0 |
| wide-5 | 21 | 38.1% | $-41.05 | $-1.95 | $67.47 | $-44.68 | -2.57% | {'time exit (10 days)': 3, 'stop-loss': 11, 'take-profit': 7} | 0 | 0 |
| wide-6 | 21 | 42.9% | $63.26 | $3.01 | $73.18 | $-49.61 | -3.39% | {'time exit (10 days)': 5, 'stop-loss': 9, 'take-profit': 7} | 0 | 0 |
| filter | 12 | 16.7% | $-208.42 | $-17.37 | $44.46 | $-29.73 | -2.96% | {'take-profit': 2, 'stop-loss': 10} | 0 | 9 |
| time-5d | 21 | 19.0% | $-348.71 | $-16.61 | $31.11 | $-27.83 | -3.93% | {'time exit (5 days)': 4, 'stop-loss': 16, 'take-profit': 1} | 0 | 0 |
| signal-exit | 21 | 14.3% | $-439.76 | $-20.94 | $29.83 | $-29.40 | -4.84% | {'time exit (10 days)': 2, 'signal exit (reversal)': 1, 'stop-loss': 18} | 0 | 0 |
| combined-wide-5-filter | 12 | 16.7% | $-332.97 | $-27.75 | $46.31 | $-42.56 | -4.25% | {'time exit (10 days)': 3, 'stop-loss': 8, 'take-profit': 1} | 0 | 9 |

- baseline per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- wide-5 per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- wide-6 per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- filter per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 1, 'TSLA': 3, 'JPM': 2}
- time-5d per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- signal-exit per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- combined-wide-5-filter per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 1, 'TSLA': 3, 'JPM': 2}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 13 | 15.4% | $-238.19 | $-18.32 | $43.60 | $-29.58 | -2.96% | {'stop-loss': 11, 'take-profit': 2} | 0 | 0 |
| wide-5 | 13 | 61.5% | $352.19 | $27.09 | $75.42 | $-50.24 | -1.00% | {'stop-loss': 5, 'take-profit': 8} | 0 | 0 |
| wide-6 | 13 | 69.2% | $482.00 | $37.08 | $80.48 | $-60.59 | -0.60% | {'stop-loss': 4, 'take-profit': 7, 'time exit (10 days)': 2} | 0 | 0 |
| filter | 2 | 50.0% | $14.55 | $7.28 | $44.56 | $-30.01 | -0.30% | {'stop-loss': 1, 'take-profit': 1} | 0 | 11 |
| time-5d | 13 | 15.4% | $-238.19 | $-18.32 | $43.60 | $-29.58 | -2.96% | {'stop-loss': 11, 'take-profit': 2} | 0 | 0 |
| signal-exit | 13 | 7.7% | $-289.37 | $-22.26 | $64.99 | $-29.53 | -3.25% | {'stop-loss': 12, 'time exit (10 days)': 1} | 0 | 0 |
| combined-wide-5-filter | 2 | 50.0% | $24.26 | $12.13 | $74.27 | $-50.01 | -0.50% | {'stop-loss': 1, 'take-profit': 1} | 0 | 11 |

- baseline per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- wide-5 per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- wide-6 per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- filter per symbol: {'JNJ': 1, 'BTC-USD': 1}
- time-5d per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- signal-exit per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- combined-wide-5-filter per symbol: {'JNJ': 1, 'BTC-USD': 1}

## OOS-3 — 2024-09-01 → 2025-02-28 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 21 | 71.4% | $472.75 | $22.51 | $40.50 | $-22.47 | -0.30% | {'take-profit': 12, 'stop-loss': 4, 'time exit (10 days)': 5} | 0 | 0 |
| wide-5 | 21 | 81.0% | $1,021.98 | $48.67 | $65.43 | $-22.58 | -0.50% | {'take-profit': 12, 'stop-loss': 1, 'time exit (10 days)': 8} | 0 | 0 |
| wide-6 | 21 | 81.0% | $1,073.32 | $51.11 | $69.03 | $-25.04 | -0.60% | {'time exit (10 days)': 10, 'stop-loss': 1, 'take-profit': 10} | 0 | 0 |
| filter | 12 | 83.3% | $340.43 | $28.37 | $40.09 | $-30.25 | -0.30% | {'take-profit': 8, 'stop-loss': 2, 'time exit (10 days)': 2} | 0 | 9 |
| time-5d | 22 | 77.3% | $500.89 | $22.77 | $36.15 | $-22.75 | -0.36% | {'take-profit': 12, 'stop-loss': 3, 'time exit (5 days)': 7} | 0 | 0 |
| signal-exit | 21 | 61.9% | $616.57 | $29.36 | $60.35 | $-21.00 | -0.30% | {'time exit (10 days)': 14, 'stop-loss': 5, 'signal exit (reversal)': 2} | 0 | 0 |
| combined-wide-5-filter | 12 | 91.7% | $660.06 | $55.00 | $64.58 | $-50.36 | -0.50% | {'take-profit': 8, 'stop-loss': 1, 'time exit (10 days)': 3} | 0 | 9 |

- baseline per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- wide-5 per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- wide-6 per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- filter per symbol: {'AAPL': 3, 'MSFT': 1, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- time-5d per symbol: {'AAPL': 3, 'MSFT': 3, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- signal-exit per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- combined-wide-5-filter per symbol: {'AAPL': 3, 'MSFT': 1, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 12 | 66.7% | $191.67 | $15.97 | $36.20 | $-24.49 | -0.47% | {'stop-loss': 3, 'time exit (10 days)': 4, 'take-profit': 5} | 0 | 0 |
| wide-5 | 12 | 66.7% | $263.31 | $21.94 | $52.75 | $-39.68 | -0.87% | {'stop-loss': 3, 'time exit (10 days)': 5, 'take-profit': 4} | 0 | 0 |
| wide-6 | 12 | 66.7% | $293.26 | $24.44 | $60.31 | $-47.30 | -1.07% | {'stop-loss': 3, 'time exit (10 days)': 5, 'take-profit': 4} | 0 | 0 |
| filter | 7 | 71.4% | $117.76 | $16.82 | $35.55 | $-29.98 | -0.47% | {'stop-loss': 2, 'time exit (10 days)': 2, 'take-profit': 3} | 0 | 5 |
| time-5d | 12 | 66.7% | $172.36 | $14.36 | $34.50 | $-25.91 | -0.31% | {'stop-loss': 3, 'time exit (5 days)': 4, 'take-profit': 5} | 0 | 0 |
| signal-exit | 12 | 58.3% | $194.60 | $16.22 | $46.10 | $-25.62 | -0.47% | {'stop-loss': 4, 'time exit (10 days)': 8} | 0 | 0 |
| combined-wide-5-filter | 7 | 71.4% | $148.61 | $21.23 | $49.68 | $-49.91 | -0.87% | {'stop-loss': 2, 'time exit (10 days)': 3, 'take-profit': 2} | 0 | 5 |

- baseline per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- wide-5 per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- wide-6 per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- filter per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2}
- time-5d per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- signal-exit per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- combined-wide-5-filter per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2}

## Phase-4 window (in-sample) — 2026-02-23 → 2026-11-06 (in-sample — the window the hypothesis was picked from)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 18 | 72.2% | $435.99 | $24.22 | $43.03 | $-24.69 | -0.30% | {'take-profit': 12, 'stop-loss': 4, 'time exit (10 days)': 2} | 0 | 0 |
| wide-5 | 18 | 72.2% | $521.54 | $28.97 | $53.30 | $-34.26 | -1.00% | {'take-profit': 7, 'time exit (10 days)': 8, 'stop-loss': 3} | 0 | 0 |
| wide-6 | 18 | 77.8% | $728.11 | $40.45 | $59.35 | $-25.70 | -0.46% | {'take-profit': 7, 'time exit (10 days)': 11} | 0 | 0 |
| filter | 9 | 66.7% | $211.12 | $23.46 | $45.41 | $-20.44 | -0.30% | {'take-profit': 6, 'stop-loss': 2, 'time exit (10 days)': 1} | 0 | 9 |
| time-5d | 21 | 71.4% | $437.36 | $20.83 | $39.88 | $-26.80 | -0.60% | {'take-profit': 12, 'stop-loss': 5, 'time exit (5 days)': 4} | 0 | 0 |
| signal-exit | 18 | 55.6% | $713.28 | $39.63 | $93.24 | $-27.38 | -0.60% | {'time exit (10 days)': 10, 'stop-loss': 7, 'signal exit (reversal)': 1} | 0 | 0 |
| combined-wide-5-filter | 9 | 55.6% | $91.09 | $10.12 | $48.71 | $-38.11 | -1.00% | {'take-profit': 3, 'stop-loss': 3, 'time exit (10 days)': 3} | 0 | 9 |

- baseline per symbol: {'AAPL': 2, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 4, 'META': 3, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- wide-5 per symbol: {'AAPL': 2, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 4, 'META': 3, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- wide-6 per symbol: {'AAPL': 2, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 4, 'META': 3, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- filter per symbol: {'AAPL': 1, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 2, 'JNJ': 1}
- time-5d per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 1, 'AMZN': 4, 'GOOGL': 5, 'META': 4, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- signal-exit per symbol: {'AAPL': 2, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 4, 'META': 3, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- combined-wide-5-filter per symbol: {'AAPL': 1, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 2, 'JNJ': 1}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked | Skipped (filter) |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| baseline | 11 | 72.7% | $241.97 | $22.00 | $41.66 | $-30.45 | -0.30% | {'take-profit': 7, 'time exit (10 days)': 1, 'stop-loss': 3} | 0 | 0 |
| wide-5 | 11 | 63.6% | $133.02 | $12.09 | $43.89 | $-43.55 | -1.08% | {'take-profit': 3, 'time exit (10 days)': 5, 'stop-loss': 3} | 0 | 0 |
| wide-6 | 11 | 63.6% | $173.79 | $15.80 | $50.41 | $-44.76 | -1.14% | {'take-profit': 3, 'time exit (10 days)': 7, 'stop-loss': 1} | 0 | 0 |
| filter | 9 | 77.8% | $226.76 | $25.20 | $41.06 | $-30.34 | -0.30% | {'take-profit': 6, 'time exit (10 days)': 1, 'stop-loss': 2} | 0 | 2 |
| time-5d | 13 | 61.5% | $211.15 | $16.24 | $42.48 | $-25.74 | -0.30% | {'take-profit': 7, 'time exit (5 days)': 2, 'stop-loss': 4} | 0 | 0 |
| signal-exit | 11 | 27.3% | $40.05 | $3.64 | $89.84 | $-28.68 | -1.07% | {'time exit (10 days)': 4, 'stop-loss': 7} | 0 | 0 |
| combined-wide-5-filter | 9 | 55.6% | $7.87 | $0.87 | $36.34 | $-43.46 | -1.44% | {'take-profit': 2, 'time exit (10 days)': 4, 'stop-loss': 3} | 0 | 2 |

- baseline per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 1, 'TSLA': 2, 'JNJ': 1}
- wide-5 per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 1, 'TSLA': 2, 'JNJ': 1}
- wide-6 per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 1, 'TSLA': 2, 'JNJ': 1}
- filter per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 1, 'TSLA': 1, 'JNJ': 1}
- time-5d per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 3, 'META': 2, 'TSLA': 2, 'JNJ': 1}
- signal-exit per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 1, 'TSLA': 2, 'JNJ': 1}
- combined-wide-5-filter per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 1, 'TSLA': 1, 'JNJ': 1}

## What this does and does not prove

Nothing here proves future profits: past performance does not guarantee future results. Seven variants were tested on the same three windows, so the best-looking one is partly the best by chance (multiple comparisons) — a variant that only looks good here needs a fresh window before it is trusted. The combined variant was selected after seeing the base results on these same windows, so it is not independent evidence either. Live paper trades over real days plus a compliance/legal review are still required before any real money is considered.

## Trades (every trade, in order) — baseline and combined variants

Trade-by-trade rows for the baseline and the combined variant are printed here. Every trade for every variant is in the JSON report — the Markdown would be seven times as long otherwise.

### OOS-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $253.80 | stop-loss | 9 | -29.99 |
| 2 | AAPL | $260.34 | $252.53 | stop-loss | 4 | -29.91 |
| 3 | AAPL | $246.98 | $258.09 | take-profit | 4 | +44.72 |
| 4 | MSFT | $475.41 | $480.11 | time exit (10 days) | 10 | +9.86 |
| 5 | MSFT | $441.31 | $461.18 | take-profit | 2 | +45.00 |
| 6 | SPY | $645.57 | $674.62 | take-profit | 5 | +45.18 |
| 7 | AMZN | $217.14 | $226.91 | take-profit | 2 | +45.38 |
| 8 | GOOGL | $240.90 | $251.74 | take-profit | 5 | +45.57 |
| 9 | META | $616.85 | $598.34 | stop-loss | 6 | -30.53 |
| 10 | META | $607.83 | $589.59 | stop-loss | 3 | -30.44 |
| 11 | META | $587.16 | $613.59 | take-profit | 2 | +45.53 |
| 12 | META | $611.39 | $638.91 | take-profit | 1 | +45.74 |
| 13 | JPM | $296.42 | $309.75 | take-profit | 4 | +45.90 |
| 14 | JNJ | $201.55 | $210.63 | take-profit | 5 | +46.20 |
| 15 | BTC-USD | $111,222.06 | $107,885.40 | stop-loss | 2 | -30.70 |
| 16 | BTC-USD | $109,712.83 | $114,649.92 | take-profit | 4 | +45.91 |
| 17 | BTC-USD | $95,549.15 | $92,682.67 | stop-loss | 2 | -30.67 |
| 18 | BTC-USD | $86,631.90 | $84,032.94 | stop-loss | 1 | -30.67 |
| 19 | BTC-USD | $87,341.89 | $91,272.29 | take-profit | 2 | +45.99 |
| 20 | BTC-USD | $84,561.59 | $82,024.74 | stop-loss | 1 | -30.70 |
| 21 | BTC-USD | $75,633.55 | $73,364.54 | stop-loss | 1 | -30.63 |
| 22 | ETH-USD | $4,035.89 | $4,217.51 | take-profit | 3 | +46.06 |
| 23 | ETH-USD | $2,903.58 | $3,034.25 | take-profit | 4 | +46.27 |
| 24 | ETH-USD | $2,818.23 | $2,733.69 | stop-loss | 1 | -30.98 |
| 25 | ETH-USD | $2,227.56 | $2,160.73 | stop-loss | 1 | -30.89 |

### OOS-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $248.57 | stop-loss | 9 | -49.98 |
| 2 | AAPL | $260.34 | $247.32 | stop-loss | 4 | -49.77 |
| 3 | SPY | $645.57 | $678.37 | time exit (10 days) | 10 | +50.31 |
| 4 | AMZN | $217.14 | $233.43 | take-profit | 6 | +74.65 |
| 5 | GOOGL | $240.90 | $252.42 | time exit (10 days) | 10 | +47.93 |
| 6 | JNJ | $201.55 | $214.56 | time exit (10 days) | 10 | +65.03 |
| 7 | BTC-USD | $111,222.06 | $110,224.70 | time exit (10 days) | 10 | -9.08 |
| 8 | ETH-USD | $4,035.89 | $4,338.59 | take-profit | 5 | +75.95 |

### OOS-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $248.57 | stop-loss | 9 | -49.98 |
| 2 | AAPL | $260.34 | $247.32 | stop-loss | 4 | -49.77 |
| 3 | SPY | $645.57 | $678.37 | time exit (10 days) | 10 | +50.31 |
| 4 | AMZN | $217.14 | $233.43 | take-profit | 6 | +74.65 |
| 5 | GOOGL | $240.90 | $252.42 | time exit (10 days) | 10 | +47.93 |
| 6 | JNJ | $201.55 | $214.56 | time exit (10 days) | 10 | +65.03 |
| 7 | BTC-USD | $111,222.06 | $110,224.70 | time exit (10 days) | 10 | -9.08 |
| 8 | ETH-USD | $4,035.89 | $4,338.59 | take-profit | 5 | +75.95 |

### OOS-1 — Bollinger mean-reversion (buy lower band, sell upper band) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $253.80 | stop-loss | 9 | -29.99 |
| 2 | MSFT | $493.04 | $478.25 | stop-loss | 10 | -29.91 |
| 3 | MSFT | $441.31 | $461.18 | take-profit | 2 | +44.75 |
| 4 | NVDA | $173.78 | $181.61 | take-profit | 2 | +44.97 |
| 5 | SPY | $645.57 | $674.62 | take-profit | 5 | +45.14 |
| 6 | AMZN | $218.15 | $227.96 | take-profit | 10 | +45.31 |
| 7 | META | $664.22 | $644.29 | stop-loss | 1 | -30.36 |
| 8 | META | $629.47 | $610.59 | stop-loss | 4 | -30.26 |
| 9 | TSLA | $401.99 | $389.93 | stop-loss | 1 | -30.18 |
| 10 | TSLA | $406.01 | $393.83 | stop-loss | 1 | -30.09 |
| 11 | JPM | $292.90 | $306.09 | take-profit | 10 | +45.03 |
| 12 | JNJ | $170.32 | $177.99 | take-profit | 8 | +45.22 |
| 13 | BTC-USD | $86,631.90 | $84,032.94 | stop-loss | 1 | -30.15 |
| 14 | BTC-USD | $86,419.78 | $90,308.67 | take-profit | 7 | +45.11 |
| 15 | ETH-USD | $3,425.17 | $3,322.42 | stop-loss | 1 | -30.31 |

### OOS-1 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $248.57 | stop-loss | 9 | -49.98 |
| 2 | MSFT | $493.04 | $475.41 | time exit (10 days) | 10 | -35.58 |
| 3 | SPY | $645.57 | $678.37 | time exit (10 days) | 10 | +50.38 |
| 4 | AMZN | $218.15 | $227.74 | time exit (10 days) | 10 | +43.81 |
| 5 | TSLA | $401.99 | $432.14 | take-profit | 10 | +75.06 |
| 6 | TSLA | $406.01 | $411.71 | time exit (10 days) | 10 | +14.16 |
| 7 | JPM | $292.90 | $303.59 | time exit (10 days) | 10 | +36.86 |
| 8 | JNJ | $170.32 | $181.88 | time exit (10 days) | 10 | +68.78 |

### OOS-1 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $261.65 | $248.57 | stop-loss | 9 | -49.98 |
| 2 | MSFT | $493.04 | $475.41 | time exit (10 days) | 10 | -35.58 |
| 3 | SPY | $645.57 | $678.37 | time exit (10 days) | 10 | +50.38 |
| 4 | AMZN | $218.15 | $227.74 | time exit (10 days) | 10 | +43.81 |
| 5 | TSLA | $401.99 | $432.14 | take-profit | 10 | +75.06 |
| 6 | TSLA | $406.01 | $411.71 | time exit (10 days) | 10 | +14.16 |
| 7 | JPM | $292.90 | $303.59 | time exit (10 days) | 10 | +36.86 |
| 8 | JNJ | $170.32 | $181.88 | time exit (10 days) | 10 | +68.78 |

### OOS-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $212.18 | $221.74 | take-profit | 7 | +45.03 |
| 2 | AAPL | $216.94 | $210.43 | stop-loss | 9 | -30.12 |
| 3 | MSFT | $355.66 | $344.99 | stop-loss | 1 | -30.06 |
| 4 | NVDA | $112.40 | $109.02 | stop-loss | 1 | -29.99 |
| 5 | NVDA | $94.07 | $91.25 | stop-loss | 1 | -29.87 |
| 6 | SPY | $564.82 | $547.88 | stop-loss | 1 | -29.77 |
| 7 | SPY | $497.04 | $482.12 | stop-loss | 1 | -29.69 |
| 8 | AMZN | $212.28 | $205.91 | stop-loss | 1 | -29.60 |
| 9 | AMZN | $199.25 | $193.27 | stop-loss | 1 | -29.52 |
| 10 | GOOGL | $169.29 | $164.21 | stop-loss | 6 | -29.41 |
| 11 | GOOGL | $144.92 | $140.57 | stop-loss | 1 | -29.33 |
| 12 | META | $622.09 | $603.43 | stop-loss | 1 | -29.24 |
| 13 | META | $502.30 | $487.23 | stop-loss | 1 | -29.15 |
| 14 | TSLA | $292.98 | $284.19 | stop-loss | 1 | -29.07 |
| 15 | TSLA | $262.67 | $254.79 | stop-loss | 1 | -28.98 |
| 16 | TSLA | $249.98 | $242.48 | stop-loss | 1 | -28.90 |
| 17 | JPM | $233.98 | $226.96 | stop-loss | 1 | -28.80 |
| 18 | JPM | $224.47 | $234.58 | take-profit | 6 | +43.10 |
| 19 | BTC-USD | $84,373.01 | $88,169.79 | take-profit | 2 | +42.90 |
| 20 | ETH-USD | $2,237.91 | $2,170.77 | stop-loss | 1 | -28.98 |
| 21 | ETH-USD | $1,861.15 | $1,805.32 | stop-loss | 1 | -28.89 |

### OOS-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $212.18 | $216.57 | time exit (10 days) | 10 | +20.67 |
| 2 | NVDA | $112.40 | $106.78 | stop-loss | 1 | -50.07 |
| 3 | SPY | $564.82 | $554.78 | time exit (10 days) | 10 | -17.73 |
| 4 | AMZN | $212.28 | $201.67 | stop-loss | 2 | -49.74 |
| 5 | AMZN | $199.25 | $196.21 | time exit (10 days) | 10 | -15.11 |
| 6 | GOOGL | $169.29 | $160.82 | stop-loss | 7 | -49.45 |
| 7 | META | $622.09 | $590.99 | stop-loss | 1 | -49.19 |
| 8 | TSLA | $292.98 | $278.33 | stop-loss | 1 | -48.95 |
| 9 | TSLA | $262.67 | $249.54 | stop-loss | 1 | -48.69 |
| 10 | TSLA | $249.98 | $237.48 | stop-loss | 1 | -48.46 |
| 11 | JPM | $233.98 | $222.28 | stop-loss | 1 | -48.21 |
| 12 | JPM | $224.47 | $241.31 | take-profit | 7 | +71.96 |

### OOS-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $212.18 | $216.57 | time exit (10 days) | 10 | +20.67 |
| 2 | NVDA | $112.40 | $106.78 | stop-loss | 1 | -50.07 |
| 3 | SPY | $564.82 | $554.78 | time exit (10 days) | 10 | -17.73 |
| 4 | AMZN | $212.28 | $201.67 | stop-loss | 2 | -49.74 |
| 5 | AMZN | $199.25 | $196.21 | time exit (10 days) | 10 | -15.11 |
| 6 | GOOGL | $169.29 | $160.82 | stop-loss | 7 | -49.45 |
| 7 | META | $622.09 | $590.99 | stop-loss | 1 | -49.19 |
| 8 | TSLA | $292.98 | $278.33 | stop-loss | 1 | -48.95 |
| 9 | TSLA | $262.67 | $249.54 | stop-loss | 1 | -48.69 |
| 10 | TSLA | $249.98 | $237.48 | stop-loss | 1 | -48.46 |
| 11 | JPM | $233.98 | $222.28 | stop-loss | 1 | -48.21 |
| 12 | JPM | $224.47 | $241.31 | take-profit | 7 | +71.96 |

### OOS-2 — Bollinger mean-reversion (buy lower band, sell upper band) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $187.23 | $181.61 | stop-loss | 1 | -30.01 |
| 2 | MSFT | $355.66 | $344.99 | stop-loss | 1 | -29.92 |
| 3 | NVDA | $94.07 | $91.25 | stop-loss | 1 | -29.83 |
| 4 | SPY | $497.04 | $482.12 | stop-loss | 1 | -29.74 |
| 5 | AMZN | $171.00 | $165.87 | stop-loss | 1 | -29.64 |
| 6 | GOOGL | $153.61 | $149.00 | stop-loss | 5 | -29.54 |
| 7 | GOOGL | $144.92 | $140.57 | stop-loss | 1 | -29.46 |
| 8 | META | $502.30 | $487.23 | stop-loss | 1 | -29.37 |
| 9 | JPM | $204.32 | $198.19 | stop-loss | 1 | -29.31 |
| 10 | JNJ | $147.51 | $143.08 | stop-loss | 1 | -29.21 |
| 11 | BTC-USD | $84,373.01 | $88,169.79 | take-profit | 2 | +43.66 |
| 12 | BTC-USD | $112,526.91 | $117,590.63 | take-profit | 5 | +43.55 |
| 13 | ETH-USD | $2,237.91 | $2,170.77 | stop-loss | 1 | -29.37 |

### OOS-2 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | JNJ | $147.51 | $140.13 | stop-loss | 3 | -50.01 |
| 2 | BTC-USD | $112,526.91 | $120,966.44 | take-profit | 9 | +74.27 |

### OOS-2 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | JNJ | $147.51 | $140.13 | stop-loss | 3 | -50.01 |
| 2 | BTC-USD | $112,526.91 | $120,966.44 | take-profit | 9 | +74.27 |

### OOS-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $214.99 | $224.67 | take-profit | 2 | +45.02 |
| 2 | AAPL | $232.71 | $225.73 | stop-loss | 5 | -30.13 |
| 3 | AAPL | $221.04 | $230.99 | take-profit | 5 | +45.10 |
| 4 | MSFT | $417.60 | $422.68 | time exit (10 days) | 10 | +12.24 |
| 5 | MSFT | $405.85 | $393.68 | stop-loss | 9 | -30.21 |
| 6 | GOOGL | $147.62 | $154.28 | take-profit | 3 | +45.28 |
| 7 | TSLA | $219.57 | $212.98 | stop-loss | 6 | -30.28 |
| 8 | TSLA | $217.97 | $227.79 | take-profit | 2 | +45.31 |
| 9 | TSLA | $328.50 | $343.29 | take-profit | 1 | +45.48 |
| 10 | JPM | $221.33 | $231.30 | take-profit | 4 | +45.70 |
| 11 | JNJ | $151.28 | $154.84 | time exit (10 days) | 10 | +23.99 |
| 12 | JNJ | $144.60 | $147.56 | time exit (10 days) | 10 | +20.90 |
| 13 | JNJ | $144.94 | $143.69 | time exit (10 days) | 10 | -8.85 |
| 14 | JNJ | $138.23 | $137.69 | time exit (10 days) | 10 | -3.98 |
| 15 | BTC-USD | $53,948.75 | $56,376.45 | take-profit | 3 | +45.88 |
| 16 | BTC-USD | $92,643.21 | $96,812.17 | take-profit | 3 | +45.86 |
| 17 | ETH-USD | $2,223.88 | $2,323.96 | take-profit | 2 | +46.43 |
| 18 | ETH-USD | $2,436.51 | $2,546.16 | take-profit | 3 | +46.63 |
| 19 | ETH-USD | $3,356.39 | $3,507.44 | take-profit | 4 | +46.84 |
| 20 | ETH-USD | $2,632.31 | $2,553.34 | stop-loss | 1 | -31.37 |
| 21 | ETH-USD | $2,675.90 | $2,796.32 | take-profit | 4 | +46.91 |

### OOS-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $214.99 | $231.12 | take-profit | 3 | +75.02 |
| 2 | AAPL | $232.71 | $221.08 | stop-loss | 5 | -50.36 |
| 3 | AAPL | $221.04 | $237.62 | take-profit | 5 | +75.21 |
| 4 | MSFT | $417.60 | $422.68 | time exit (10 days) | 10 | +12.28 |
| 5 | GOOGL | $147.62 | $158.70 | take-profit | 5 | +75.87 |
| 6 | TSLA | $219.57 | $236.05 | take-profit | 7 | +76.47 |
| 7 | TSLA | $217.97 | $234.33 | take-profit | 2 | +77.04 |
| 8 | TSLA | $328.50 | $353.15 | take-profit | 2 | +77.60 |
| 9 | JPM | $221.33 | $233.74 | time exit (10 days) | 10 | +58.41 |
| 10 | JNJ | $151.28 | $154.84 | time exit (10 days) | 10 | +24.65 |
| 11 | BTC-USD | $92,643.21 | $99,591.46 | take-profit | 7 | +78.52 |
| 12 | ETH-USD | $3,356.39 | $3,608.13 | take-profit | 4 | +79.35 |

### OOS-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $214.99 | $231.12 | take-profit | 3 | +75.02 |
| 2 | AAPL | $232.71 | $221.08 | stop-loss | 5 | -50.36 |
| 3 | AAPL | $221.04 | $237.62 | take-profit | 5 | +75.21 |
| 4 | MSFT | $417.60 | $422.68 | time exit (10 days) | 10 | +12.28 |
| 5 | GOOGL | $147.62 | $158.70 | take-profit | 5 | +75.87 |
| 6 | TSLA | $219.57 | $236.05 | take-profit | 7 | +76.47 |
| 7 | TSLA | $217.97 | $234.33 | take-profit | 2 | +77.04 |
| 8 | TSLA | $328.50 | $353.15 | take-profit | 2 | +77.60 |
| 9 | JPM | $221.33 | $233.74 | time exit (10 days) | 10 | +58.41 |
| 10 | JNJ | $151.28 | $154.84 | time exit (10 days) | 10 | +24.65 |
| 11 | BTC-USD | $92,643.21 | $99,591.46 | take-profit | 7 | +78.52 |
| 12 | ETH-USD | $3,356.39 | $3,608.13 | take-profit | 4 | +79.35 |

### OOS-3 — Bollinger mean-reversion (buy lower band, sell upper band) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $232.71 | $225.73 | stop-loss | 5 | -30.00 |
| 2 | SPY | $573.06 | $580.54 | time exit (10 days) | 10 | +13.02 |
| 3 | GOOGL | $156.06 | $151.37 | stop-loss | 3 | -29.97 |
| 4 | GOOGL | $147.62 | $154.28 | take-profit | 3 | +44.88 |
| 5 | TSLA | $328.50 | $343.29 | take-profit | 1 | +45.01 |
| 6 | JPM | $196.29 | $202.05 | time exit (10 days) | 10 | +29.46 |
| 7 | JPM | $221.33 | $231.30 | take-profit | 4 | +45.36 |
| 8 | JNJ | $144.60 | $147.56 | time exit (10 days) | 10 | +20.70 |
| 9 | JNJ | $140.03 | $139.02 | time exit (10 days) | 10 | -7.33 |
| 10 | BTC-USD | $53,948.75 | $56,376.45 | take-profit | 3 | +45.40 |
| 11 | ETH-USD | $2,223.88 | $2,323.96 | take-profit | 2 | +45.80 |
| 12 | ETH-USD | $2,884.57 | $2,798.03 | stop-loss | 1 | -30.66 |

### OOS-3 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $232.71 | $221.08 | stop-loss | 5 | -49.98 |
| 2 | SPY | $573.06 | $580.54 | time exit (10 days) | 10 | +13.00 |
| 3 | GOOGL | $156.06 | $148.25 | stop-loss | 4 | -49.83 |
| 4 | GOOGL | $147.62 | $158.70 | take-profit | 5 | +74.38 |
| 5 | TSLA | $328.50 | $353.15 | take-profit | 2 | +74.94 |
| 6 | JPM | $196.29 | $202.05 | time exit (10 days) | 10 | +29.52 |
| 7 | JPM | $221.33 | $233.74 | time exit (10 days) | 10 | +56.58 |

### OOS-3 — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $232.71 | $221.08 | stop-loss | 5 | -49.98 |
| 2 | SPY | $573.06 | $580.54 | time exit (10 days) | 10 | +13.00 |
| 3 | GOOGL | $156.06 | $148.25 | stop-loss | 4 | -49.83 |
| 4 | GOOGL | $147.62 | $158.70 | take-profit | 5 | +74.38 |
| 5 | TSLA | $328.50 | $353.15 | take-profit | 2 | +74.94 |
| 6 | JPM | $196.29 | $202.05 | time exit (10 days) | 10 | +29.52 |
| 7 | JPM | $221.33 | $233.74 | time exit (10 days) | 10 | +56.58 |

### Phase-4 window (in-sample) — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $287.28 | take-profit | 2 | +44.99 |
| 2 | AAPL | $305.93 | $319.70 | take-profit | 4 | +45.21 |
| 3 | MSFT | $352.17 | $368.02 | take-profit | 1 | +45.42 |
| 4 | AMZN | $238.00 | $248.71 | take-profit | 4 | +45.61 |
| 5 | AMZN | $237.50 | $230.38 | stop-loss | 5 | -30.52 |
| 6 | AMZN | $227.01 | $237.23 | take-profit | 2 | +45.70 |
| 7 | AMZN | $258.63 | $258.51 | time exit (10 days) | 10 | -0.47 |
| 8 | GOOGL | $358.55 | $347.79 | stop-loss | 6 | -30.58 |
| 9 | GOOGL | $356.15 | $372.18 | take-profit | 3 | +45.75 |
| 10 | GOOGL | $319.53 | $333.92 | take-profit | 2 | +45.97 |
| 11 | GOOGL | $344.60 | $334.26 | stop-loss | 7 | -30.77 |
| 12 | META | $601.58 | $628.65 | take-profit | 5 | +46.02 |
| 13 | META | $542.44 | $566.85 | take-profit | 2 | +46.22 |
| 14 | META | $556.27 | $581.31 | take-profit | 1 | +46.44 |
| 15 | TSLA | $313.03 | $303.64 | stop-loss | 2 | -31.09 |
| 16 | TSLA | $311.21 | $325.22 | take-profit | 2 | +46.52 |
| 17 | JPM | $330.73 | $333.53 | time exit (10 days) | 10 | +8.79 |
| 18 | JNJ | $252.93 | $264.32 | take-profit | 5 | +46.78 |

### Phase-4 window (in-sample) — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $295.53 | take-profit | 4 | +74.99 |
| 2 | MSFT | $352.17 | $378.58 | take-profit | 2 | +75.56 |
| 3 | AMZN | $238.00 | $226.10 | stop-loss | 10 | -50.75 |
| 4 | AMZN | $237.50 | $225.62 | stop-loss | 5 | -50.52 |
| 5 | AMZN | $227.01 | $244.04 | take-profit | 2 | +75.39 |
| 6 | AMZN | $258.63 | $258.51 | time exit (10 days) | 10 | -0.47 |
| 7 | GOOGL | $358.55 | $363.56 | time exit (10 days) | 10 | +14.16 |
| 8 | GOOGL | $356.15 | $338.34 | stop-loss | 10 | -50.70 |
| 9 | JNJ | $252.93 | $253.79 | time exit (10 days) | 10 | +3.43 |

### Phase-4 window (in-sample) — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $295.53 | take-profit | 4 | +74.99 |
| 2 | MSFT | $352.17 | $378.58 | take-profit | 2 | +75.56 |
| 3 | AMZN | $238.00 | $226.10 | stop-loss | 10 | -50.75 |
| 4 | AMZN | $237.50 | $225.62 | stop-loss | 5 | -50.52 |
| 5 | AMZN | $227.01 | $244.04 | take-profit | 2 | +75.39 |
| 6 | AMZN | $258.63 | $258.51 | time exit (10 days) | 10 | -0.47 |
| 7 | GOOGL | $358.55 | $363.56 | time exit (10 days) | 10 | +14.16 |
| 8 | GOOGL | $356.15 | $338.34 | stop-loss | 10 | -50.70 |
| 9 | JNJ | $252.93 | $253.79 | time exit (10 days) | 10 | +3.43 |

### Phase-4 window (in-sample) — Bollinger mean-reversion (buy lower band, sell upper band) — baseline

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $287.28 | take-profit | 2 | +44.99 |
| 2 | NVDA | $200.20 | $209.21 | take-profit | 3 | +45.23 |
| 3 | SPY | $721.77 | $732.48 | time exit (10 days) | 10 | +14.97 |
| 4 | AMZN | $250.02 | $242.52 | stop-loss | 4 | -30.31 |
| 5 | AMZN | $238.00 | $248.71 | take-profit | 4 | +45.34 |
| 6 | GOOGL | $358.55 | $347.79 | stop-loss | 6 | -30.36 |
| 7 | GOOGL | $319.53 | $333.92 | take-profit | 2 | +45.42 |
| 8 | META | $570.00 | $595.66 | take-profit | 3 | +45.62 |
| 9 | TSLA | $381.59 | $398.77 | take-profit | 1 | +45.84 |
| 10 | TSLA | $313.03 | $303.64 | stop-loss | 2 | -30.68 |
| 11 | JNJ | $252.93 | $264.32 | take-profit | 5 | +45.91 |

### Phase-4 window (in-sample) — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $295.53 | take-profit | 4 | +74.99 |
| 2 | NVDA | $200.20 | $195.52 | time exit (10 days) | 10 | -23.53 |
| 3 | SPY | $721.77 | $732.48 | time exit (10 days) | 10 | +14.91 |
| 4 | AMZN | $250.02 | $237.52 | stop-loss | 5 | -50.33 |
| 5 | AMZN | $238.00 | $226.10 | stop-loss | 10 | -50.08 |
| 6 | GOOGL | $358.55 | $363.56 | time exit (10 days) | 10 | +13.94 |
| 7 | META | $570.00 | $541.50 | stop-loss | 10 | -49.90 |
| 8 | TSLA | $381.59 | $410.21 | take-profit | 3 | +74.47 |
| 9 | JNJ | $252.93 | $253.79 | time exit (10 days) | 10 | +3.40 |

### Phase-4 window (in-sample) — Bollinger mean-reversion (buy lower band, sell upper band) — combined-wide-5-filter

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $274.91 | $295.53 | take-profit | 4 | +74.99 |
| 2 | NVDA | $200.20 | $195.52 | time exit (10 days) | 10 | -23.53 |
| 3 | SPY | $721.77 | $732.48 | time exit (10 days) | 10 | +14.91 |
| 4 | AMZN | $250.02 | $237.52 | stop-loss | 5 | -50.33 |
| 5 | AMZN | $238.00 | $226.10 | stop-loss | 10 | -50.08 |
| 6 | GOOGL | $358.55 | $363.56 | time exit (10 days) | 10 | +13.94 |
| 7 | META | $570.00 | $541.50 | stop-loss | 10 | -49.90 |
| 8 | TSLA | $381.59 | $410.21 | take-profit | 3 | +74.47 |
| 9 | JNJ | $252.93 | $253.79 | time exit (10 days) | 10 | +3.40 |

