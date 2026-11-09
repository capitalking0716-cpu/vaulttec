# VaultTec — Phase 4d Fresh-Window Test Report

Generated: 2026-11-09T11:02:53.185965 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests exit rules on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Fresh-window test of the Phase 4c winners only: wide-5 (5% stop / 7.5% target) and wide-6 (6% / 9%), for RSI and Bollinger mean-reversion, plus the baseline (3% / 4.5%) as a control, on three fresh 180-calendar-day windows never used for selection (FRESH-1/2/3, all ending before OOS-3 starts). Delayed real market history from yfinance (free), 70 days of warm-up history before each window, 12 symbols, 5-day walk-forward steps, signals from history up to the trade day only — no look-ahead. Every trade goes through the real PaperTradingEngine and Risk Engine, balanced profile, $10,000 virtual cash, long-only, 10-day exit. Every variant keeps a stop-loss; the stop is never removed. Fetched histories are cached to data/fresh-cache/ as they arrive, so an interrupted run resumes from disk instead of re-fetching. Fresh results are pooled ONLY across the fresh windows — never with the selection windows, which are not re-run here.
- Data: yfinance (delayed real market data, free — Yahoo Finance)
- Verdict rule: A variant 'holds up' on fresh data when its pooled fresh-window paper P&L is > $0 AND its pooled win rate is > 40% (the 1.5:1 break-even) AND it is positive in at least 2 of the 3 fresh windows.

## Fresh windows (never used for selection)

All three end before OOS-3 starts (2024-09-01) and none overlaps OOS-1/2/3, the Phase 4 window, or each other:

- **FRESH-1**: 2024-03-04 → 2024-09-01
- **FRESH-2**: 2023-09-06 → 2024-03-04
- **FRESH-3**: 2023-03-10 → 2023-09-06

## What Phase 4c found on the selection windows (for comparison only — NOT pooled with fresh results)

### RSI mean-reversion (buy RSI < 30, sell RSI > 70) — Phase 4c pooled OOS-1/2/3

- wide-5: 67 trades, 59.7% win, $1,517.23
- wide-6: 67 trades, 59.7% win, $1,441.19
- baseline: 67 trades, 47.8% win, $341.61

### Bollinger mean-reversion (buy lower band, sell upper band) — Phase 4c pooled OOS-1/2/3

- wide-5: 40 trades, 65.0% win, $888.92
- wide-6: 40 trades, 65.0% win, $880.48
- baseline: 40 trades, 42.5% win, $27.76

## Pooled fresh-window verdict — 3 fresh windows, per strategy

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Holds up |
|---|---:|---:|---:|---:|:---:|:---:|
| baseline | 73 | 52.1% | $425.03 | $5.82 | 2/3 | yes |
| wide-5 | 73 | 58.9% | $936.61 | $12.83 | 3/3 | yes |
| wide-6 | 73 | 61.6% | $1,226.24 | $16.80 | 3/3 | yes |

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Holds up |
|---|---:|---:|---:|---:|:---:|:---:|
| baseline | 36 | 38.9% | $-66.99 | $-1.86 | 1/3 | NO |
| wide-5 | 36 | 58.3% | $678.66 | $18.85 | 3/3 | yes |
| wide-6 | 36 | 63.9% | $1,043.47 | $28.99 | 3/3 | yes |

## Verdict

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Best variant by pooled fresh P&L: **wide-6** ($1,226.24).
- Variants holding up on fresh data: ['baseline', 'wide-5', 'wide-6'].
- Verdict rule: holds up = pooled fresh P&L > $0 AND pooled win rate > 40% AND positive in at least 2 of 3 fresh windows.

### Bollinger mean-reversion (buy lower band, sell upper band)

- Best variant by pooled fresh P&L: **wide-6** ($1,043.47).
- Variants holding up on fresh data: ['wide-5', 'wide-6'].
- Verdict rule: holds up = pooled fresh P&L > $0 AND pooled win rate > 40% AND positive in at least 2 of 3 fresh windows.

## Reading it honestly

A wider stop helps only if the win rate rises enough to pay for the bigger losses when the stop does fire — at 1.5:1 the break-even win rate is 40%, so a 60% win rate with a 5% stop is worth far more than a 60% win rate with a 3% stop, and a win rate just above 40% with a wide stop can still lose money. Fresh windows are a genuinely new test, but they are still past prices: three more windows do not prove the next window, and a variant that holds up here still needs live paper trades over real days — where prices arrive one day at a time and cannot be re-run — before real money is ever considered.

## FRESH-1 — 2024-03-04 → 2024-09-01 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 27 | 40.7% | $-72.53 | $-2.69 | $36.76 | $-29.80 | -1.64% | {'stop-loss': 16, 'take-profit': 9, 'time exit (10 days)': 2} | 0 |
| wide-5 | 27 | 51.9% | $129.46 | $4.79 | $52.63 | $-46.72 | -1.70% | {'time exit (10 days)': 7, 'stop-loss': 12, 'take-profit': 8} | 0 |
| wide-6 | 27 | 59.3% | $298.22 | $11.05 | $55.55 | $-53.69 | -1.75% | {'time exit (10 days)': 11, 'stop-loss': 9, 'take-profit': 7} | 0 |

- baseline per symbol: {'AAPL': 2, 'MSFT': 4, 'AMZN': 3, 'GOOGL': 4, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 3, 'ETH-USD': 3}
- wide-5 per symbol: {'AAPL': 2, 'MSFT': 4, 'AMZN': 3, 'GOOGL': 4, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 3, 'ETH-USD': 3}
- wide-6 per symbol: {'AAPL': 2, 'MSFT': 4, 'AMZN': 3, 'GOOGL': 4, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 3, 'ETH-USD': 3}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 18 | 38.9% | $-76.80 | $-4.27 | $32.30 | $-27.54 | -1.19% | {'stop-loss': 10, 'take-profit': 4, 'time exit (10 days)': 4} | 0 |
| wide-5 | 18 | 61.1% | $349.46 | $19.41 | $55.91 | $-37.94 | -1.00% | {'time exit (10 days)': 7, 'stop-loss': 5, 'take-profit': 6} | 0 |
| wide-6 | 18 | 66.7% | $499.89 | $27.77 | $62.79 | $-42.27 | -1.20% | {'time exit (10 days)': 9, 'stop-loss': 4, 'take-profit': 5} | 0 |

- baseline per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 3, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 4}
- wide-5 per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 3, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 4}
- wide-6 per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 3, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 4}

## FRESH-2 — 2023-09-06 → 2024-03-04 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 22 | 63.6% | $319.23 | $14.51 | $38.71 | $-27.84 | -0.90% | {'take-profit': 11, 'time exit (10 days)': 5, 'stop-loss': 6} | 0 |
| wide-5 | 22 | 63.6% | $327.46 | $14.88 | $43.45 | $-35.10 | -1.49% | {'time exit (10 days)': 13, 'take-profit': 5, 'stop-loss': 4} | 0 |
| wide-6 | 22 | 63.6% | $296.06 | $13.46 | $44.12 | $-40.20 | -1.79% | {'time exit (10 days)': 14, 'take-profit': 4, 'stop-loss': 4} | 0 |

- baseline per symbol: {'AAPL': 3, 'NVDA': 2, 'SPY': 2, 'AMZN': 1, 'TSLA': 6, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-5 per symbol: {'AAPL': 3, 'NVDA': 2, 'SPY': 2, 'AMZN': 1, 'TSLA': 6, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-6 per symbol: {'AAPL': 3, 'NVDA': 2, 'SPY': 2, 'AMZN': 1, 'TSLA': 6, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 1, 'ETH-USD': 1}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 5 | 40.0% | $23.77 | $4.75 | $44.94 | $-22.04 | -0.66% | {'take-profit': 2, 'stop-loss': 2, 'time exit (10 days)': 1} | 0 |
| wide-5 | 5 | 60.0% | $144.00 | $28.80 | $66.85 | $-28.27 | -0.56% | {'take-profit': 2, 'time exit (10 days)': 2, 'stop-loss': 1} | 0 |
| wide-6 | 5 | 60.0% | $128.53 | $25.71 | $53.77 | $-16.39 | -0.32% | {'take-profit': 1, 'time exit (10 days)': 4} | 0 |

- baseline per symbol: {'AMZN': 1, 'GOOGL': 1, 'JNJ': 2, 'ETH-USD': 1}
- wide-5 per symbol: {'AMZN': 1, 'GOOGL': 1, 'JNJ': 2, 'ETH-USD': 1}
- wide-6 per symbol: {'AMZN': 1, 'GOOGL': 1, 'JNJ': 2, 'ETH-USD': 1}

## FRESH-3 — 2023-03-10 → 2023-09-06 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 24 | 54.2% | $178.33 | $7.43 | $38.17 | $-28.89 | -1.58% | {'stop-loss': 10, 'take-profit': 9, 'time exit (10 days)': 5} | 0 |
| wide-5 | 24 | 62.5% | $479.69 | $19.99 | $48.78 | $-28.01 | -1.00% | {'time exit (10 days)': 15, 'take-profit': 6, 'stop-loss': 3} | 0 |
| wide-6 | 24 | 62.5% | $631.96 | $26.33 | $54.64 | $-20.84 | -0.60% | {'time exit (10 days)': 18, 'take-profit': 5, 'stop-loss': 1} | 0 |

- baseline per symbol: {'AAPL': 2, 'MSFT': 1, 'SPY': 2, 'META': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 5, 'ETH-USD': 4}
- wide-5 per symbol: {'AAPL': 2, 'MSFT': 1, 'SPY': 2, 'META': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 5, 'ETH-USD': 4}
- wide-6 per symbol: {'AAPL': 2, 'MSFT': 1, 'SPY': 2, 'META': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 5, 'ETH-USD': 4}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 13 | 38.5% | $-13.96 | $-1.07 | $42.34 | $-28.21 | -0.90% | {'stop-loss': 7, 'take-profit': 4, 'time exit (10 days)': 2} | 0 |
| wide-5 | 13 | 53.8% | $185.20 | $14.25 | $57.24 | $-35.91 | -1.00% | {'take-profit': 4, 'time exit (10 days)': 6, 'stop-loss': 3} | 0 |
| wide-6 | 13 | 61.5% | $415.05 | $31.93 | $69.71 | $-28.53 | -0.60% | {'take-profit': 5, 'time exit (10 days)': 7, 'stop-loss': 1} | 0 |

- baseline per symbol: {'NVDA': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 2, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 2}
- wide-5 per symbol: {'NVDA': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 2, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 2}
- wide-6 per symbol: {'NVDA': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 2, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 2}

## What this does and does not prove

Fresh-window results are the honest check on Phase 4c: the wide-stop variants were picked because they looked good on OOS-1/2/3, so those windows cannot confirm them. A variant that holds up here — positive pooled, above break-even win rate, positive in at least 2 of 3 fresh windows — has survived a genuinely new test; a variant that fades or reverses here means the Phase 4c result was selection luck, and the wider stop should not be trusted on its own. Nothing here proves future profits: past performance does not guarantee future results, and live paper trades over real days plus a compliance/legal review are still required before any real money is considered.

## Trades (every trade, in order) — wide-5 and wide-6

Trade-by-trade rows for the two winning variants are printed here. Every trade for every variant (including the baseline) is in the JSON report.

### FRESH-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | AAPL | $217.78 | $206.89 | stop-loss | 1 | -49.98 |
| 3 | MSFT | $381.90 | $408.61 | time exit (10 days) | 10 | +69.54 |
| 4 | MSFT | $417.90 | $397.01 | stop-loss | 6 | -50.05 |
| 5 | MSFT | $401.41 | $381.34 | stop-loss | 1 | -49.82 |
| 6 | MSFT | $398.99 | $410.31 | time exit (10 days) | 10 | +28.13 |
| 7 | AMZN | $182.02 | $186.89 | time exit (10 days) | 10 | +26.59 |
| 8 | AMZN | $182.50 | $173.38 | stop-loss | 5 | -49.81 |
| 9 | AMZN | $167.90 | $159.50 | stop-loss | 1 | -49.61 |
| 10 | GOOGL | $132.09 | $142.00 | take-profit | 8 | +74.00 |
| 11 | GOOGL | $165.62 | $157.33 | stop-loss | 6 | -49.73 |
| 12 | GOOGL | $165.28 | $157.01 | stop-loss | 1 | -49.48 |
| 13 | GOOGL | $162.31 | $164.25 | time exit (10 days) | 10 | +11.74 |
| 14 | META | $426.54 | $458.54 | take-profit | 4 | +73.92 |
| 15 | META | $462.23 | $496.90 | take-profit | 4 | +74.46 |
| 16 | TSLA | $173.80 | $165.11 | stop-loss | 10 | -50.01 |
| 17 | TSLA | $200.00 | $215.00 | take-profit | 4 | +74.64 |
| 18 | JPM | $171.70 | $184.58 | take-profit | 8 | +75.23 |
| 19 | JNJ | $147.11 | $139.75 | stop-loss | 6 | -50.53 |
| 20 | JNJ | $134.72 | $134.85 | time exit (10 days) | 10 | +0.95 |
| 21 | JNJ | $136.71 | $137.08 | time exit (10 days) | 10 | +2.69 |
| 22 | BTC-USD | $64,252.58 | $61,039.95 | stop-loss | 2 | -50.12 |
| 23 | BTC-USD | $61,604.80 | $58,524.56 | stop-loss | 7 | -49.90 |
| 24 | BTC-USD | $56,034.32 | $60,236.90 | take-profit | 2 | +74.39 |
| 25 | ETH-USD | $2,929.39 | $3,149.09 | take-profit | 4 | +75.20 |
| 26 | ETH-USD | $2,458.72 | $2,335.79 | stop-loss | 1 | -50.51 |
| 27 | ETH-USD | $2,553.25 | $2,744.75 | take-profit | 1 | +75.39 |

### FRESH-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | AAPL | $217.78 | $204.72 | stop-loss | 1 | -59.94 |
| 3 | MSFT | $381.90 | $408.61 | time exit (10 days) | 10 | +69.47 |
| 4 | MSFT | $417.90 | $392.83 | stop-loss | 6 | -60.01 |
| 5 | MSFT | $401.41 | $411.96 | time exit (10 days) | 10 | +26.12 |
| 6 | MSFT | $398.99 | $410.31 | time exit (10 days) | 10 | +28.29 |
| 7 | AMZN | $182.02 | $186.89 | time exit (10 days) | 10 | +26.74 |
| 8 | AMZN | $182.50 | $171.55 | stop-loss | 5 | -60.14 |
| 9 | AMZN | $167.90 | $157.83 | stop-loss | 1 | -59.75 |
| 10 | GOOGL | $132.09 | $143.98 | take-profit | 10 | +89.12 |
| 11 | GOOGL | $165.62 | $155.68 | stop-loss | 6 | -59.94 |
| 12 | GOOGL | $165.28 | $155.36 | stop-loss | 1 | -59.60 |
| 13 | GOOGL | $162.31 | $164.25 | time exit (10 days) | 10 | +11.78 |
| 14 | META | $426.54 | $464.93 | take-profit | 5 | +88.96 |
| 15 | META | $462.23 | $503.83 | take-profit | 4 | +89.76 |
| 16 | TSLA | $173.80 | $166.63 | time exit (10 days) | 10 | -41.51 |
| 17 | TSLA | $200.00 | $218.00 | take-profit | 5 | +90.19 |
| 18 | JPM | $171.70 | $182.09 | time exit (10 days) | 10 | +61.21 |
| 19 | JNJ | $147.11 | $138.28 | stop-loss | 8 | -61.05 |
| 20 | JNJ | $134.72 | $134.85 | time exit (10 days) | 10 | +0.95 |
| 21 | JNJ | $136.71 | $137.08 | time exit (10 days) | 10 | +2.70 |
| 22 | BTC-USD | $64,252.58 | $60,397.42 | stop-loss | 2 | -60.53 |
| 23 | BTC-USD | $61,604.80 | $57,908.51 | stop-loss | 7 | -60.25 |
| 24 | BTC-USD | $56,034.32 | $61,077.41 | take-profit | 2 | +89.77 |
| 25 | ETH-USD | $2,929.39 | $3,193.04 | take-profit | 4 | +90.75 |
| 26 | ETH-USD | $2,458.72 | $2,680.01 | take-profit | 2 | +91.57 |
| 27 | ETH-USD | $2,553.25 | $2,631.40 | time exit (10 days) | 10 | +31.42 |

### FRESH-1 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | MSFT | $381.90 | $408.61 | time exit (10 days) | 10 | +69.89 |
| 3 | SPY | $489.09 | $487.58 | time exit (10 days) | 10 | -3.10 |
| 4 | SPY | $519.29 | $540.15 | time exit (10 days) | 10 | +40.41 |
| 5 | AMZN | $167.90 | $159.50 | stop-loss | 1 | -50.53 |
| 6 | GOOGL | $132.09 | $142.00 | take-profit | 8 | +75.37 |
| 7 | GOOGL | $165.62 | $157.33 | stop-loss | 6 | -50.65 |
| 8 | TSLA | $157.11 | $149.25 | stop-loss | 2 | -50.40 |
| 9 | JPM | $171.70 | $184.58 | take-profit | 8 | +75.21 |
| 10 | JPM | $181.89 | $189.14 | time exit (10 days) | 10 | +40.27 |
| 11 | JPM | $190.16 | $204.43 | take-profit | 10 | +76.07 |
| 12 | JNJ | $146.20 | $147.11 | time exit (10 days) | 10 | +6.33 |
| 13 | JNJ | $134.72 | $134.85 | time exit (10 days) | 10 | +0.96 |
| 14 | BTC-USD | $63,821.47 | $60,630.40 | stop-loss | 4 | -51.06 |
| 15 | ETH-USD | $3,157.62 | $3,394.44 | take-profit | 1 | +76.28 |
| 16 | ETH-USD | $3,004.90 | $3,230.27 | take-profit | 2 | +76.85 |
| 17 | ETH-USD | $2,929.39 | $3,149.09 | take-profit | 4 | +77.42 |
| 18 | ETH-USD | $2,458.72 | $2,335.79 | stop-loss | 1 | -52.00 |

### FRESH-1 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | MSFT | $381.90 | $408.61 | time exit (10 days) | 10 | +69.89 |
| 3 | SPY | $489.09 | $487.58 | time exit (10 days) | 10 | -3.10 |
| 4 | SPY | $519.29 | $540.15 | time exit (10 days) | 10 | +40.41 |
| 5 | AMZN | $167.90 | $157.83 | stop-loss | 1 | -60.57 |
| 6 | GOOGL | $132.09 | $143.98 | take-profit | 10 | +90.34 |
| 7 | GOOGL | $165.62 | $155.68 | stop-loss | 6 | -60.77 |
| 8 | TSLA | $157.11 | $147.68 | stop-loss | 3 | -60.43 |
| 9 | JPM | $171.70 | $182.09 | time exit (10 days) | 10 | +60.58 |
| 10 | JPM | $181.89 | $189.14 | time exit (10 days) | 10 | +40.15 |
| 11 | JPM | $190.16 | $204.32 | time exit (10 days) | 10 | +75.26 |
| 12 | JNJ | $146.20 | $147.11 | time exit (10 days) | 10 | +6.31 |
| 13 | JNJ | $134.72 | $134.85 | time exit (10 days) | 10 | +0.96 |
| 14 | BTC-USD | $63,821.47 | $59,992.18 | stop-loss | 4 | -60.89 |
| 15 | ETH-USD | $3,157.62 | $3,441.81 | take-profit | 1 | +91.17 |
| 16 | ETH-USD | $3,004.90 | $3,275.34 | take-profit | 2 | +91.98 |
| 17 | ETH-USD | $2,929.39 | $3,193.04 | take-profit | 4 | +92.81 |
| 18 | ETH-USD | $2,458.72 | $2,680.01 | take-profit | 2 | +93.65 |

### FRESH-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $183.32 | $192.83 | time exit (10 days) | 10 | +51.85 |
| 2 | AAPL | $181.42 | $185.78 | time exit (10 days) | 10 | +24.17 |
| 3 | AAPL | $183.04 | $179.46 | time exit (10 days) | 10 | -19.73 |
| 4 | NVDA | $42.11 | $43.91 | time exit (10 days) | 10 | +42.91 |
| 5 | NVDA | $42.34 | $45.53 | take-profit | 7 | +76.05 |
| 6 | SPY | $410.88 | $420.79 | time exit (10 days) | 10 | +24.53 |
| 7 | SPY | $409.54 | $414.90 | time exit (10 days) | 10 | +13.34 |
| 8 | AMZN | $127.00 | $128.13 | time exit (10 days) | 10 | +9.09 |
| 9 | TSLA | $212.42 | $201.80 | stop-loss | 3 | -51.11 |
| 10 | TSLA | $205.66 | $221.09 | take-profit | 2 | +76.31 |
| 11 | TSLA | $219.91 | $208.91 | stop-loss | 2 | -51.26 |
| 12 | TSLA | $209.14 | $198.68 | stop-loss | 2 | -50.99 |
| 13 | TSLA | $191.59 | $182.01 | stop-loss | 3 | -50.73 |
| 14 | TSLA | $185.10 | $198.98 | take-profit | 7 | +75.69 |
| 15 | JPM | $133.53 | $143.55 | take-profit | 7 | +76.33 |
| 16 | JNJ | $145.10 | $149.60 | time exit (10 days) | 10 | +31.80 |
| 17 | JNJ | $142.81 | $140.25 | time exit (10 days) | 10 | -18.43 |
| 18 | JNJ | $143.42 | $139.18 | time exit (10 days) | 10 | -30.31 |
| 19 | JNJ | $139.18 | $138.06 | time exit (10 days) | 10 | -8.26 |
| 20 | JNJ | $136.54 | $136.64 | time exit (10 days) | 10 | +0.76 |
| 21 | BTC-USD | $40,077.07 | $43,082.86 | take-profit | 5 | +76.65 |
| 22 | ETH-USD | $2,233.56 | $2,296.04 | time exit (10 days) | 10 | +28.80 |

### FRESH-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $183.32 | $192.83 | time exit (10 days) | 10 | +51.85 |
| 2 | AAPL | $181.42 | $185.78 | time exit (10 days) | 10 | +24.17 |
| 3 | AAPL | $183.04 | $179.46 | time exit (10 days) | 10 | -19.73 |
| 4 | NVDA | $42.11 | $43.91 | time exit (10 days) | 10 | +42.91 |
| 5 | NVDA | $42.34 | $46.16 | take-profit | 10 | +91.08 |
| 6 | SPY | $410.88 | $420.79 | time exit (10 days) | 10 | +24.57 |
| 7 | SPY | $409.54 | $414.90 | time exit (10 days) | 10 | +13.36 |
| 8 | AMZN | $127.00 | $128.13 | time exit (10 days) | 10 | +9.10 |
| 9 | TSLA | $212.42 | $199.67 | stop-loss | 3 | -61.45 |
| 10 | TSLA | $205.66 | $224.18 | take-profit | 2 | +91.63 |
| 11 | TSLA | $219.91 | $206.72 | stop-loss | 4 | -61.58 |
| 12 | TSLA | $209.14 | $196.59 | stop-loss | 2 | -61.24 |
| 13 | TSLA | $191.59 | $180.09 | stop-loss | 4 | -60.89 |
| 14 | TSLA | $185.10 | $201.77 | take-profit | 8 | +90.81 |
| 15 | JPM | $133.53 | $136.92 | time exit (10 days) | 10 | +25.84 |
| 16 | JNJ | $145.10 | $149.60 | time exit (10 days) | 10 | +31.65 |
| 17 | JNJ | $142.81 | $140.25 | time exit (10 days) | 10 | -18.35 |
| 18 | JNJ | $143.42 | $139.18 | time exit (10 days) | 10 | -30.17 |
| 19 | JNJ | $139.18 | $138.06 | time exit (10 days) | 10 | -8.22 |
| 20 | JNJ | $136.54 | $136.64 | time exit (10 days) | 10 | +0.75 |
| 21 | BTC-USD | $40,077.07 | $43,684.02 | take-profit | 6 | +91.26 |
| 22 | ETH-USD | $2,233.56 | $2,296.04 | time exit (10 days) | 10 | +28.71 |

### FRESH-2 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AMZN | $121.39 | $130.50 | take-profit | 3 | +75.05 |
| 2 | GOOGL | $124.43 | $130.60 | time exit (10 days) | 10 | +49.99 |
| 3 | JNJ | $144.27 | $143.42 | time exit (10 days) | 10 | -5.97 |
| 4 | JNJ | $140.25 | $133.24 | stop-loss | 7 | -50.57 |
| 5 | ETH-USD | $1,551.64 | $1,668.01 | take-profit | 7 | +75.50 |

### FRESH-2 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AMZN | $121.39 | $132.31 | take-profit | 3 | +89.96 |
| 2 | GOOGL | $124.43 | $130.60 | time exit (10 days) | 10 | +50.07 |
| 3 | JNJ | $144.27 | $143.42 | time exit (10 days) | 10 | -5.98 |
| 4 | JNJ | $140.25 | $136.54 | time exit (10 days) | 10 | -26.80 |
| 5 | ETH-USD | $1,551.64 | $1,584.31 | time exit (10 days) | 10 | +21.28 |

### FRESH-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $175.36 | $174.03 | time exit (10 days) | 10 | -7.57 |
| 2 | AAPL | $171.68 | $184.57 | take-profit | 9 | +75.04 |
| 3 | MSFT | $309.63 | $320.26 | time exit (10 days) | 10 | +34.57 |
| 4 | SPY | $368.09 | $378.91 | time exit (10 days) | 10 | +29.70 |
| 5 | SPY | $419.28 | $432.79 | time exit (10 days) | 10 | +32.65 |
| 6 | META | $282.39 | $293.08 | time exit (10 days) | 10 | +38.49 |
| 7 | TSLA | $173.44 | $164.77 | stop-loss | 1 | -51.00 |
| 8 | TSLA | $162.55 | $154.42 | stop-loss | 2 | -50.77 |
| 9 | TSLA | $219.22 | $235.67 | take-profit | 3 | +75.80 |
| 10 | JPM | $138.45 | $136.30 | time exit (10 days) | 10 | -15.78 |
| 11 | JNJ | $137.18 | $138.12 | time exit (10 days) | 10 | +6.95 |
| 12 | JNJ | $144.37 | $140.73 | time exit (10 days) | 10 | -25.61 |
| 13 | JNJ | $143.01 | $144.21 | time exit (10 days) | 10 | +8.49 |
| 14 | JNJ | $140.73 | $146.54 | time exit (10 days) | 10 | +41.88 |
| 15 | JNJ | $144.78 | $155.65 | take-profit | 6 | +76.52 |
| 16 | BTC-USD | $20,187.24 | $21,701.30 | take-profit | 2 | +76.91 |
| 17 | BTC-USD | $26,930.64 | $26,334.82 | time exit (10 days) | 10 | -22.88 |
| 18 | BTC-USD | $26,890.13 | $27,745.88 | time exit (10 days) | 10 | +32.78 |
| 19 | BTC-USD | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -22.30 |
| 20 | BTC-USD | $26,031.66 | $27,984.04 | take-profit | 7 | +77.31 |
| 21 | ETH-USD | $1,429.16 | $1,536.35 | take-profit | 2 | +78.08 |
| 22 | ETH-USD | $1,812.59 | $1,893.08 | time exit (10 days) | 10 | +46.57 |
| 23 | ETH-USD | $1,684.93 | $1,600.69 | stop-loss | 5 | -52.67 |
| 24 | ETH-USD | $1,633.89 | $1,628.49 | time exit (10 days) | 10 | -3.47 |

### FRESH-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $175.36 | $174.03 | time exit (10 days) | 10 | -7.57 |
| 2 | AAPL | $171.68 | $185.36 | time exit (10 days) | 10 | +79.63 |
| 3 | MSFT | $309.63 | $320.26 | time exit (10 days) | 10 | +34.58 |
| 4 | SPY | $368.09 | $378.91 | time exit (10 days) | 10 | +29.72 |
| 5 | SPY | $419.28 | $432.79 | time exit (10 days) | 10 | +32.66 |
| 6 | META | $282.39 | $293.08 | time exit (10 days) | 10 | +38.51 |
| 7 | TSLA | $173.44 | $189.06 | take-profit | 7 | +91.93 |
| 8 | TSLA | $162.55 | $152.80 | stop-loss | 3 | -61.78 |
| 9 | TSLA | $219.22 | $238.95 | take-profit | 3 | +92.14 |
| 10 | JPM | $138.45 | $136.30 | time exit (10 days) | 10 | -16.02 |
| 11 | JNJ | $137.18 | $138.12 | time exit (10 days) | 10 | +7.05 |
| 12 | JNJ | $144.37 | $140.73 | time exit (10 days) | 10 | -26.00 |
| 13 | JNJ | $143.01 | $144.21 | time exit (10 days) | 10 | +8.62 |
| 14 | JNJ | $140.73 | $146.54 | time exit (10 days) | 10 | +42.51 |
| 15 | JNJ | $144.78 | $157.82 | take-profit | 7 | +93.18 |
| 16 | BTC-USD | $20,187.24 | $22,004.10 | take-profit | 2 | +93.93 |
| 17 | BTC-USD | $26,930.64 | $26,334.82 | time exit (10 days) | 10 | -23.30 |
| 18 | BTC-USD | $26,890.13 | $27,745.88 | time exit (10 days) | 10 | +33.37 |
| 19 | BTC-USD | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -22.71 |
| 20 | BTC-USD | $26,031.66 | $25,800.72 | time exit (10 days) | 10 | -9.33 |
| 21 | ETH-USD | $1,429.16 | $1,557.79 | take-profit | 2 | +94.60 |
| 22 | ETH-USD | $1,812.59 | $1,893.08 | time exit (10 days) | 10 | +47.10 |
| 23 | ETH-USD | $1,684.93 | $1,657.51 | time exit (10 days) | 10 | -17.34 |
| 24 | ETH-USD | $1,633.89 | $1,628.49 | time exit (10 days) | 10 | -3.52 |

### FRESH-3 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-5

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | NVDA | $42.26 | $45.43 | take-profit | 7 | +75.05 |
| 2 | SPY | $368.09 | $378.91 | time exit (10 days) | 10 | +29.62 |
| 3 | SPY | $419.28 | $432.79 | time exit (10 days) | 10 | +32.56 |
| 4 | TSLA | $173.44 | $164.77 | stop-loss | 1 | -50.67 |
| 5 | TSLA | $162.55 | $154.42 | stop-loss | 2 | -50.45 |
| 6 | TSLA | $219.22 | $235.67 | take-profit | 3 | +75.31 |
| 7 | JPM | $115.48 | $119.62 | time exit (10 days) | 10 | +36.21 |
| 8 | JPM | $138.45 | $136.30 | time exit (10 days) | 10 | -15.73 |
| 9 | JNJ | $144.37 | $140.73 | time exit (10 days) | 10 | -25.52 |
| 10 | BTC-USD | $20,187.24 | $21,701.30 | take-profit | 2 | +75.70 |
| 11 | BTC-USD | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -21.90 |
| 12 | ETH-USD | $1,429.16 | $1,536.35 | take-profit | 2 | +76.20 |
| 13 | ETH-USD | $1,684.93 | $1,600.69 | stop-loss | 5 | -51.18 |

### FRESH-3 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | NVDA | $42.26 | $46.07 | take-profit | 7 | +90.20 |
| 2 | SPY | $368.09 | $378.91 | time exit (10 days) | 10 | +29.67 |
| 3 | SPY | $419.28 | $432.79 | time exit (10 days) | 10 | +32.61 |
| 4 | TSLA | $173.44 | $189.06 | take-profit | 7 | +91.43 |
| 5 | TSLA | $162.55 | $152.80 | stop-loss | 3 | -61.44 |
| 6 | TSLA | $219.22 | $238.95 | take-profit | 3 | +91.64 |
| 7 | JPM | $115.48 | $119.62 | time exit (10 days) | 10 | +36.79 |
| 8 | JPM | $138.45 | $136.30 | time exit (10 days) | 10 | -15.99 |
| 9 | JNJ | $144.37 | $140.73 | time exit (10 days) | 10 | -25.93 |
| 10 | BTC-USD | $20,187.24 | $22,004.10 | take-profit | 2 | +92.30 |
| 11 | BTC-USD | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -22.30 |
| 12 | ETH-USD | $1,429.16 | $1,557.79 | take-profit | 2 | +93.05 |
| 13 | ETH-USD | $1,684.93 | $1,657.51 | time exit (10 days) | 10 | -16.98 |

