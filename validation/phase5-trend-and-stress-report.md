# VaultTec — Phase 5 Trend-Following & Stress Test Report

Generated: 2026-11-09T12:52:43.168285 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests strategies on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Two paper-only tests on delayed real yfinance history, 12 symbols, walk-forward, signals from history up to the trade day only — no look-ahead. Every trade goes through the real PaperTradingEngine and Risk Engine, balanced profile, $10,000 virtual cash, long-only, 10-day exit. Every variant keeps a stop-loss; the stop is never removed. (a) Trend-following: SMA crossover (SMA-10 cross above SMA-30) and MACD crossover (MACD cross above signal line), exactly as defined in analytics/backtest.py, with wide-6 exits (6% stop / 9% target, 1.5:1), on OOS-1/2/3, the Phase 4 window (re-run, in-sample), and FRESH-1/2/3. Trend entries are checked on EVERY bar because a crossover is a single-bar event a 5-day step would miss; mean-reversion entries in Phases 4b–4d used a 5-day step because their triggers are persistent states. (b) Stress: RSI + Bollinger mean-reversion under baseline (3% / 4.5%), wide-5 (5% / 7.5%) and wide-6 (6% / 9%) on one more fresh window, FRESH-4 (2022-09-12 → 2023-03-10), with the Phase 4d method (70 days warm-up, 5-day steps). Fetched histories are cached to data/fresh-cache/ as they arrive; FRESH-1/2/3 histories were already cached from Phase 4d and were not re-fetched.
- Data: yfinance (delayed real market data, free — Yahoo Finance)
- Trend verdict rule: A trend strategy 'beats mean-reversion in OOS-2' when its OOS-2 paper P&L is greater than BOTH mean-reversion wide-6 OOS-2 figures (RSI +$63.26, Bollinger +$482.00).
- Stress verdict rule: Wide-6 'holds up' on FRESH-4 when its FRESH-4 paper P&L is > $0 AND its win rate is > 40% (the 1.5:1 break-even). Single window only.

## Test (a) — Trend-following vs mean-reversion (wide-6 exits)

Mean-reversion wide-6 reference figures (Phases 4c/4d, same method, quoted — not re-run here):

| Strategy | Pooled OOS P&L | Pooled OOS win | OOS-2 P&L | Pooled fresh P&L |
|---|---:|---:|---:|---:|
| RSI mean-reversion (buy RSI < 30, sell RSI > 70) | $1,441.19 (67 trades, 59.7%) | $63.26 | $1,226.24 (73 trades, 61.6%) |
| Bollinger mean-reversion (buy lower band, sell upper band) | $880.48 (40 trades, 65.0%) | $482.00 | $1,043.47 (36 trades, 63.9%) |

### Trend pooled results

#### SMA trend-following (buy SMA-10 cross above SMA-30)

| Pool | Trades | Win rate | P&L | Expectancy / trade | Positive windows |
|---|---:|---:|---:|---:|:---:|
| OOS-1/2/3 pooled | 84 | 50.0% | $314.89 | $3.75 | 2/3 |
| FRESH-1/2/3 pooled | 73 | 58.9% | $351.50 | $4.82 | 2/3 |
| All 7 windows incl. Phase-4 in-sample | 184 | 53.8% | $1,015.83 | $5.52 | 5/7 |

#### MACD trend-following (buy MACD cross above signal line)

| Pool | Trades | Win rate | P&L | Expectancy / trade | Positive windows |
|---|---:|---:|---:|---:|:---:|
| OOS-1/2/3 pooled | 191 | 52.4% | $1,432.96 | $7.50 | 3/3 |
| FRESH-1/2/3 pooled | 174 | 60.9% | $2,899.45 | $16.66 | 3/3 |
| All 7 windows incl. Phase-4 in-sample | 416 | 55.0% | $4,581.51 | $11.01 | 7/7 |

### Trend verdict — does trend-following beat mean-reversion in falling windows?

#### SMA trend-following (buy SMA-10 cross above SMA-30)

- OOS-2 (the falling window) P&L: **$305.05** vs RSI wide-6 $63.26 and Bollinger wide-6 $482.00 — **does NOT beat mean-reversion in OOS-2**.
- Pooled OOS-1/2/3 P&L: $314.89 vs RSI wide-6 $1,441.19 and Bollinger wide-6 $880.48 — **does NOT beat pooled OOS**.
- Pooled FRESH-1/2/3 P&L: $351.50 vs RSI wide-6 $1,226.24 and Bollinger wide-6 $1,043.47 — **does NOT beat pooled fresh**.

#### MACD trend-following (buy MACD cross above signal line)

- OOS-2 (the falling window) P&L: **$223.23** vs RSI wide-6 $63.26 and Bollinger wide-6 $482.00 — **does NOT beat mean-reversion in OOS-2**.
- Pooled OOS-1/2/3 P&L: $1,432.96 vs RSI wide-6 $1,441.19 and Bollinger wide-6 $880.48 — **does NOT beat pooled OOS**.
- Pooled FRESH-1/2/3 P&L: $2,899.45 vs RSI wide-6 $1,226.24 and Bollinger wide-6 $1,043.47 — **beats pooled fresh**.

## Test (b) — Stress test: wide-6 mean-reversion on FRESH-4 (2022-09-12 → 2023-03-10)

One more fresh 180-day window, earlier than FRESH-3, overlapping no window used before. Single window — a hold-up here is weaker evidence than the Phase 4d three-window hold-up.

### RSI mean-reversion (buy RSI < 30, sell RSI > 70) — FRESH-4

| Variant | Trades | Win rate | P&L | Expectancy / trade | Holds up |
|---|---:|---:|---:|---:|:---:|
| baseline | 32 | 56.2% | $424.31 | $13.26 | yes |
| wide-5 | 32 | 43.8% | $302.41 | $9.45 | yes |
| wide-6 | 32 | 50.0% | $651.89 | $20.37 | yes |

- Best variant on FRESH-4: **wide-6** ($651.89).
- Wide-6 holds up on FRESH-4: **yes**.
- Variants holding up: ['baseline', 'wide-5', 'wide-6'].

### Bollinger mean-reversion (buy lower band, sell upper band) — FRESH-4

| Variant | Trades | Win rate | P&L | Expectancy / trade | Holds up |
|---|---:|---:|---:|---:|:---:|
| baseline | 14 | 50.0% | $123.22 | $8.80 | yes |
| wide-5 | 14 | 28.6% | $-119.80 | $-8.56 | NO |
| wide-6 | 14 | 35.7% | $3.24 | $0.23 | NO |

- Best variant on FRESH-4: **baseline** ($123.22).
- Wide-6 holds up on FRESH-4: **NO**.
- Variants holding up: ['baseline'].

## Reading it honestly

Nothing here proves future profits: past performance does not guarantee future results. Trend trade counts are not directly comparable with mean-reversion trade counts because trend entries are checked every bar while mean-reversion entries were checked every 5 days — P&L, win rate, and expectancy per trade are the comparison. The FRESH-4 stress check is a single window, so a hold-up there is weaker evidence than the Phase 4d three-window hold-up. Related work: a parallel Phase 4e run (validation/phase4e-trend-following-report.md) tested a different trend entry — buy when close > SMA-20 > SMA-50, a persistent state, on 5-day steps — on FRESH-1/2/3 only, from cache: wide-6 422 trades, 61.8% win, +$5,163.64 pooled fresh. It did not cover OOS-2, so it cannot answer the falling-window question; this Phase 5 test uses crossover entries (SMA-10/30, MACD) on the OOS + fresh windows instead. The two trend definitions are not the same strategy and their trade counts are not comparable. Live paper trades over real days plus a compliance/legal review are still required before any real money is considered.

## Trend — OOS-1 — 2025-08-27 → 2026-02-23 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 28 | 42.9% | $-237.03 | $-8.47 | $39.77 | $-44.64 | -2.96% | {'stop-loss': 10, 'time exit (10 days)': 16, 'take-profit': 2} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 62 | 50.0% | $455.04 | $7.34 | $53.76 | $-39.08 | -4.12% | {'time exit (10 days)': 36, 'take-profit': 10, 'stop-loss': 16} | 0 |

- sma per symbol: {'AAPL': 1, 'MSFT': 3, 'NVDA': 2, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 4, 'TSLA': 1, 'JPM': 2, 'JNJ': 3, 'BTC-USD': 4, 'ETH-USD': 4}
- macd per symbol: {'AAPL': 5, 'MSFT': 6, 'NVDA': 6, 'SPY': 9, 'AMZN': 5, 'GOOGL': 5, 'META': 4, 'TSLA': 3, 'JPM': 4, 'JNJ': 4, 'BTC-USD': 5, 'ETH-USD': 6}

## Trend — OOS-2 — 2025-02-28 → 2025-08-27 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 27 | 51.9% | $305.05 | $11.30 | $64.23 | $-45.70 | -2.38% | {'time exit (10 days)': 13, 'take-profit': 5, 'stop-loss': 9} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 68 | 51.5% | $223.23 | $3.28 | $52.26 | $-48.66 | -3.80% | {'stop-loss': 23, 'time exit (10 days)': 33, 'take-profit': 12} | 0 |

- sma per symbol: {'AAPL': 3, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 2, 'TSLA': 5, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 5, 'ETH-USD': 3}
- macd per symbol: {'AAPL': 6, 'MSFT': 5, 'NVDA': 4, 'SPY': 5, 'AMZN': 8, 'GOOGL': 7, 'META': 5, 'TSLA': 6, 'JPM': 4, 'JNJ': 3, 'BTC-USD': 9, 'ETH-USD': 6}

## Trend — OOS-3 — 2024-09-01 → 2025-02-28 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 29 | 55.2% | $246.87 | $8.51 | $49.57 | $-42.02 | -1.84% | {'time exit (10 days)': 17, 'stop-loss': 7, 'take-profit': 5} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 61 | 55.7% | $754.69 | $12.37 | $60.16 | $-47.81 | -2.96% | {'time exit (10 days)': 29, 'stop-loss': 17, 'take-profit': 15} | 0 |

- sma per symbol: {'AAPL': 2, 'MSFT': 5, 'NVDA': 2, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 4, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 3, 'ETH-USD': 3}
- macd per symbol: {'AAPL': 4, 'MSFT': 5, 'NVDA': 5, 'SPY': 5, 'AMZN': 5, 'GOOGL': 6, 'META': 5, 'TSLA': 2, 'JPM': 3, 'JNJ': 3, 'BTC-USD': 7, 'ETH-USD': 11}

## Trend — FRESH-1 — 2024-03-04 → 2024-09-01 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 20 | 65.0% | $255.55 | $12.78 | $41.87 | $-41.25 | -1.20% | {'time exit (10 days)': 16, 'stop-loss': 3, 'take-profit': 1} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 59 | 61.0% | $1,128.53 | $19.13 | $55.60 | $-37.96 | -2.48% | {'time exit (10 days)': 36, 'take-profit': 13, 'stop-loss': 10} | 0 |

- sma per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 1, 'META': 2, 'TSLA': 2, 'JPM': 2, 'JNJ': 3, 'BTC-USD': 2, 'ETH-USD': 2}
- macd per symbol: {'AAPL': 7, 'MSFT': 4, 'NVDA': 3, 'SPY': 8, 'AMZN': 5, 'GOOGL': 4, 'META': 4, 'TSLA': 3, 'JPM': 4, 'JNJ': 6, 'BTC-USD': 5, 'ETH-USD': 6}

## Trend — FRESH-2 — 2023-09-06 → 2024-03-04 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 31 | 48.4% | $-29.30 | $-0.95 | $40.63 | $-39.92 | -2.44% | {'time exit (10 days)': 20, 'stop-loss': 8, 'take-profit': 3} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 56 | 51.8% | $733.55 | $13.10 | $57.95 | $-35.08 | -1.79% | {'time exit (10 days)': 38, 'stop-loss': 10, 'take-profit': 8} | 0 |

- sma per symbol: {'AAPL': 4, 'MSFT': 3, 'NVDA': 3, 'SPY': 2, 'AMZN': 1, 'GOOGL': 3, 'META': 3, 'TSLA': 3, 'JPM': 3, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 3}
- macd per symbol: {'AAPL': 5, 'MSFT': 3, 'NVDA': 4, 'SPY': 4, 'AMZN': 6, 'GOOGL': 4, 'META': 4, 'TSLA': 4, 'JPM': 6, 'JNJ': 4, 'BTC-USD': 5, 'ETH-USD': 7}

## Trend — FRESH-3 — 2023-03-10 → 2023-09-06 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 22 | 68.2% | $125.25 | $5.69 | $30.00 | $-46.39 | -1.57% | {'time exit (10 days)': 15, 'stop-loss': 5, 'take-profit': 2} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 59 | 69.5% | $1,037.37 | $17.58 | $48.05 | $-51.81 | -1.80% | {'time exit (10 days)': 38, 'stop-loss': 13, 'take-profit': 8} | 0 |

- sma per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'TSLA': 2, 'JPM': 2, 'JNJ': 3, 'BTC-USD': 4, 'ETH-USD': 3}
- macd per symbol: {'AAPL': 6, 'MSFT': 7, 'NVDA': 5, 'SPY': 5, 'AMZN': 6, 'GOOGL': 4, 'META': 6, 'TSLA': 3, 'JPM': 4, 'JNJ': 2, 'BTC-USD': 6, 'ETH-USD': 5}

## Trend — Phase-4 window (in-sample) — 2026-02-23 → 2026-11-06 (in-sample — the window the hypothesis was picked from)

- History: 12 symbols fetched; failed: none

| Strategy | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| SMA trend-following (buy SMA-10 cross above SMA-30) | 27 | 51.9% | $349.44 | $12.94 | $64.49 | $-42.57 | -3.22% | {'time exit (10 days)': 12, 'take-profit': 8, 'stop-loss': 7} | 0 |
| MACD trend-following (buy MACD cross above signal line) | 51 | 45.1% | $249.10 | $4.88 | $49.54 | $-31.80 | -2.17% | {'time exit (10 days)': 34, 'stop-loss': 10, 'take-profit': 7} | 0 |

- sma per symbol: {'AAPL': 2, 'MSFT': 2, 'NVDA': 3, 'SPY': 3, 'AMZN': 3, 'GOOGL': 3, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 2, 'ETH-USD': 1}
- macd per symbol: {'AAPL': 4, 'MSFT': 3, 'NVDA': 4, 'SPY': 4, 'AMZN': 3, 'GOOGL': 4, 'META': 5, 'TSLA': 6, 'JPM': 6, 'JNJ': 6, 'BTC-USD': 4, 'ETH-USD': 2}

## Stress — FRESH-4 — 2022-09-12 → 2023-03-10 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 32 | 56.2% | $424.31 | $13.26 | $45.92 | $-28.73 | -0.90% | {'stop-loss': 13, 'take-profit': 18, 'time exit (10 days)': 1} | 0 |
| wide-5 | 32 | 43.8% | $302.41 | $9.45 | $70.64 | $-38.14 | -1.49% | {'time exit (10 days)': 12, 'stop-loss': 10, 'take-profit': 10} | 0 |
| wide-6 | 32 | 50.0% | $651.89 | $20.37 | $83.34 | $-42.59 | -1.79% | {'time exit (10 days)': 13, 'stop-loss': 8, 'take-profit': 11} | 0 |

- baseline per symbol: {'AAPL': 4, 'MSFT': 2, 'NVDA': 2, 'SPY': 1, 'AMZN': 4, 'GOOGL': 3, 'META': 3, 'TSLA': 7, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-5 per symbol: {'AAPL': 4, 'MSFT': 2, 'NVDA': 2, 'SPY': 1, 'AMZN': 4, 'GOOGL': 3, 'META': 3, 'TSLA': 7, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-6 per symbol: {'AAPL': 4, 'MSFT': 2, 'NVDA': 2, 'SPY': 1, 'AMZN': 4, 'GOOGL': 3, 'META': 3, 'TSLA': 7, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 1, 'ETH-USD': 1}

### Bollinger mean-reversion (buy lower band, sell upper band)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 14 | 50.0% | $123.22 | $8.80 | $45.16 | $-27.56 | -0.90% | {'take-profit': 7, 'stop-loss': 6, 'time exit (10 days)': 1} | 0 |
| wide-5 | 14 | 28.6% | $-119.80 | $-8.56 | $68.22 | $-39.27 | -3.39% | {'take-profit': 3, 'stop-loss': 7, 'time exit (10 days)': 4} | 0 |
| wide-6 | 14 | 35.7% | $3.24 | $0.23 | $81.94 | $-45.16 | -2.70% | {'take-profit': 4, 'stop-loss': 6, 'time exit (10 days)': 4} | 0 |

- baseline per symbol: {'MSFT': 1, 'NVDA': 2, 'SPY': 1, 'AMZN': 1, 'META': 1, 'TSLA': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-5 per symbol: {'MSFT': 1, 'NVDA': 2, 'SPY': 1, 'AMZN': 1, 'META': 1, 'TSLA': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- wide-6 per symbol: {'MSFT': 1, 'NVDA': 2, 'SPY': 1, 'AMZN': 1, 'META': 1, 'TSLA': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}

## What this does and does not prove

Nothing here proves future profits: past performance does not guarantee future results. Trend trade counts are not directly comparable with mean-reversion trade counts because trend entries are checked every bar while mean-reversion entries were checked every 5 days — P&L, win rate, and expectancy per trade are the comparison. The FRESH-4 stress check is a single window, so a hold-up there is weaker evidence than the Phase 4d three-window hold-up. Related work: a parallel Phase 4e run (validation/phase4e-trend-following-report.md) tested a different trend entry — buy when close > SMA-20 > SMA-50, a persistent state, on 5-day steps — on FRESH-1/2/3 only, from cache: wide-6 422 trades, 61.8% win, +$5,163.64 pooled fresh. It did not cover OOS-2, so it cannot answer the falling-window question; this Phase 5 test uses crossover entries (SMA-10/30, MACD) on the OOS + fresh windows instead. The two trend definitions are not the same strategy and their trade counts are not comparable. Live paper trades over real days plus a compliance/legal review are still required before any real money is considered.

## Trades (every trade, in order) — trend wide-6 and stress wide-6

Trade-by-trade rows for the trend strategies (wide-6) on every window and for mean-reversion wide-6 on FRESH-4. Every trade for every variant is in the JSON report.

### Trend OOS-1 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $275.16 | $258.65 | stop-loss | 6 | -60.00 |
| 2 | MSFT | $505.07 | $519.70 | time exit (10 days) | 10 | +28.78 |
| 3 | MSFT | $519.34 | $492.77 | time exit (10 days) | 10 | -51.00 |
| 4 | MSFT | $484.41 | $455.34 | stop-loss | 10 | -59.51 |
| 5 | NVDA | $178.00 | $184.60 | time exit (10 days) | 10 | +36.53 |
| 6 | NVDA | $187.78 | $185.38 | time exit (10 days) | 10 | -12.65 |
| 7 | SPY | $678.37 | $675.32 | time exit (10 days) | 10 | -4.44 |
| 8 | AMZN | $222.86 | $242.92 | take-profit | 1 | +88.91 |
| 9 | AMZN | $232.53 | $236.65 | time exit (10 days) | 10 | +17.66 |
| 10 | GOOGL | $315.93 | $321.37 | time exit (10 days) | 10 | +17.21 |
| 11 | META | $772.58 | $726.22 | stop-loss | 9 | -60.01 |
| 12 | META | $749.13 | $704.18 | stop-loss | 1 | -59.65 |
| 13 | META | $664.55 | $659.80 | time exit (10 days) | 10 | -7.06 |
| 14 | META | $714.66 | $671.78 | stop-loss | 3 | -59.25 |
| 15 | TSLA | $439.58 | $479.14 | take-profit | 5 | +88.33 |
| 16 | JPM | $305.79 | $297.54 | time exit (10 days) | 10 | -26.72 |
| 17 | JPM | $309.25 | $316.98 | time exit (10 days) | 10 | +24.68 |
| 18 | JNJ | $181.33 | $186.64 | time exit (10 days) | 10 | +28.98 |
| 19 | JNJ | $195.18 | $202.17 | time exit (10 days) | 10 | +35.56 |
| 20 | JNJ | $210.27 | $224.12 | time exit (10 days) | 10 | +65.66 |
| 21 | BTC-USD | $115,407.66 | $113,328.63 | time exit (10 days) | 10 | -17.88 |
| 22 | BTC-USD | $122,266.53 | $114,930.54 | stop-loss | 7 | -59.42 |
| 23 | BTC-USD | $92,511.34 | $86,960.66 | stop-loss | 4 | -59.39 |
| 24 | BTC-USD | $93,882.55 | $95,551.19 | time exit (10 days) | 10 | +17.52 |
| 25 | ETH-USD | $4,526.82 | $4,255.21 | stop-loss | 7 | -59.46 |
| 26 | ETH-USD | $4,451.15 | $4,184.08 | stop-loss | 3 | -59.10 |
| 27 | ETH-USD | $3,321.11 | $3,121.85 | stop-loss | 3 | -58.76 |
| 28 | ETH-USD | $3,226.13 | $3,317.10 | time exit (10 days) | 10 | +27.45 |

### Trend OOS-1 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $237.59 | $238.11 | time exit (10 days) | 10 | +2.18 |
| 2 | AAPL | $244.60 | $257.07 | time exit (10 days) | 10 | +51.01 |
| 3 | AAPL | $258.62 | $268.78 | time exit (10 days) | 10 | +39.47 |
| 4 | AAPL | $278.09 | $277.52 | time exit (10 days) | 10 | -2.08 |
| 5 | AAPL | $255.74 | $278.76 | take-profit | 7 | +90.81 |
| 6 | MSFT | $511.15 | $510.40 | time exit (10 days) | 10 | -1.50 |
| 7 | MSFT | $516.31 | $493.04 | time exit (10 days) | 10 | -45.88 |
| 8 | MSFT | $486.91 | $473.39 | time exit (10 days) | 10 | -28.14 |
| 9 | MSFT | $480.11 | $482.86 | time exit (10 days) | 10 | +5.78 |
| 10 | MSFT | $480.42 | $451.60 | stop-loss | 8 | -60.66 |
| 11 | MSFT | $477.55 | $448.90 | stop-loss | 2 | -60.30 |
| 12 | NVDA | $177.33 | $181.42 | time exit (10 days) | 10 | +23.07 |
| 13 | NVDA | $176.25 | $187.17 | time exit (10 days) | 10 | +62.06 |
| 14 | NVDA | $191.03 | $208.23 | take-profit | 2 | +90.71 |
| 15 | NVDA | $185.12 | $174.01 | stop-loss | 7 | -61.00 |
| 16 | NVDA | $183.26 | $188.67 | time exit (10 days) | 10 | +29.83 |
| 17 | NVDA | $188.08 | $176.80 | stop-loss | 5 | -60.79 |
| 18 | SPY | $640.22 | $648.59 | time exit (10 days) | 10 | +13.17 |
| 19 | SPY | $643.46 | $654.04 | time exit (10 days) | 10 | +16.58 |
| 20 | SPY | $661.32 | $658.07 | time exit (10 days) | 10 | -4.96 |
| 21 | SPY | $670.02 | $663.81 | time exit (10 days) | 10 | -9.36 |
| 22 | SPY | $676.10 | $674.48 | time exit (10 days) | 10 | -2.41 |
| 23 | SPY | $682.63 | $684.17 | time exit (10 days) | 10 | +2.28 |
| 24 | SPY | $686.45 | $680.09 | time exit (10 days) | 10 | -9.35 |
| 25 | SPY | $690.03 | $686.60 | time exit (10 days) | 10 | -5.01 |
| 26 | SPY | $690.02 | $677.56 | time exit (10 days) | 10 | -18.19 |
| 27 | AMZN | $235.68 | $231.23 | time exit (10 days) | 10 | -18.99 |
| 28 | AMZN | $227.74 | $214.08 | stop-loss | 3 | -60.21 |
| 29 | AMZN | $217.95 | $237.57 | take-profit | 7 | +89.82 |
| 30 | AMZN | $232.14 | $246.29 | time exit (10 days) | 10 | +61.37 |
| 31 | AMZN | $244.68 | $230.00 | stop-loss | 7 | -60.77 |
| 32 | GOOGL | $206.76 | $225.37 | take-profit | 4 | +90.64 |
| 33 | GOOGL | $259.25 | $282.58 | take-profit | 4 | +91.44 |
| 34 | GOOGL | $298.88 | $325.79 | take-profit | 2 | +92.28 |
| 35 | GOOGL | $324.81 | $327.29 | time exit (10 days) | 10 | +7.90 |
| 36 | GOOGL | $337.59 | $317.34 | stop-loss | 5 | -62.10 |
| 37 | META | $761.60 | $740.89 | time exit (10 days) | 10 | -27.98 |
| 38 | META | $729.69 | $685.91 | stop-loss | 8 | -61.57 |
| 39 | META | $610.98 | $665.97 | take-profit | 7 | +91.80 |
| 40 | META | $657.07 | $716.22 | take-profit | 4 | +92.64 |
| 41 | TSLA | $350.84 | $382.42 | take-profit | 5 | +93.46 |
| 42 | TSLA | $468.37 | $440.27 | stop-loss | 3 | -62.86 |
| 43 | TSLA | $430.17 | $458.96 | time exit (10 days) | 10 | +69.70 |
| 44 | JPM | $298.34 | $306.04 | time exit (10 days) | 10 | +27.07 |
| 45 | JPM | $299.74 | $314.36 | time exit (10 days) | 10 | +51.28 |
| 46 | JPM | $307.16 | $312.50 | time exit (10 days) | 10 | +18.35 |
| 47 | JPM | $310.29 | $304.31 | time exit (10 days) | 10 | -20.40 |
| 48 | JNJ | $177.62 | $186.69 | time exit (10 days) | 10 | +53.94 |
| 49 | JNJ | $190.11 | $204.27 | time exit (10 days) | 10 | +79.08 |
| 50 | JNJ | $208.23 | $204.27 | time exit (10 days) | 10 | -20.34 |
| 51 | JNJ | $210.27 | $224.12 | time exit (10 days) | 10 | +70.31 |
| 52 | BTC-USD | $110,224.70 | $116,843.19 | time exit (10 days) | 10 | +64.20 |
| 53 | BTC-USD | $118,648.93 | $111,529.99 | stop-loss | 9 | -64.78 |
| 54 | BTC-USD | $114,472.45 | $107,604.10 | stop-loss | 4 | -63.88 |
| 55 | BTC-USD | $91,285.38 | $85,808.25 | stop-loss | 4 | -63.53 |
| 56 | BTC-USD | $88,344.00 | $88,430.13 | time exit (10 days) | 10 | +1.03 |
| 57 | ETH-USD | $4,715.25 | $4,432.33 | stop-loss | 4 | -63.68 |
| 58 | ETH-USD | $4,487.92 | $4,218.65 | stop-loss | 8 | -63.31 |
| 59 | ETH-USD | $4,157.99 | $3,908.51 | stop-loss | 3 | -62.92 |
| 60 | ETH-USD | $2,957.94 | $2,780.46 | stop-loss | 6 | -62.54 |
| 61 | ETH-USD | $3,006.07 | $3,000.39 | time exit (10 days) | 10 | -1.96 |
| 62 | ETH-USD | $2,948.00 | $3,213.32 | take-profit | 9 | +93.23 |

### Trend OOS-2 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $204.09 | $210.24 | time exit (10 days) | 10 | +30.11 |
| 2 | AAPL | $211.42 | $209.01 | time exit (10 days) | 10 | -11.42 |
| 3 | AAPL | $228.25 | $226.92 | time exit (10 days) | 10 | -5.82 |
| 4 | MSFT | $420.46 | $448.69 | time exit (10 days) | 10 | +67.21 |
| 5 | NVDA | $113.53 | $123.76 | take-profit | 6 | +90.79 |
| 6 | SPY | $557.51 | $584.50 | time exit (10 days) | 10 | +49.23 |
| 7 | AMZN | $185.01 | $201.66 | take-profit | 4 | +91.97 |
| 8 | GOOGL | $163.26 | $153.47 | stop-loss | 3 | -61.84 |
| 9 | META | $584.48 | $637.09 | take-profit | 4 | +92.26 |
| 10 | META | $746.97 | $782.05 | time exit (10 days) | 10 | +48.57 |
| 11 | TSLA | $267.28 | $251.24 | stop-loss | 1 | -62.36 |
| 12 | TSLA | $272.20 | $255.87 | stop-loss | 1 | -61.96 |
| 13 | TSLA | $292.03 | $274.51 | stop-loss | 1 | -61.59 |
| 14 | TSLA | $332.56 | $312.61 | stop-loss | 1 | -61.22 |
| 15 | TSLA | $329.65 | $340.01 | time exit (10 days) | 10 | +31.88 |
| 16 | JPM | $236.65 | $245.91 | time exit (10 days) | 10 | +39.81 |
| 17 | JNJ | $148.45 | $147.22 | time exit (10 days) | 10 | -8.46 |
| 18 | JNJ | $149.92 | $147.94 | time exit (10 days) | 10 | -13.46 |
| 19 | JNJ | $151.25 | $163.03 | time exit (10 days) | 10 | +79.42 |
| 20 | BTC-USD | $86,900.88 | $81,686.83 | stop-loss | 3 | -61.53 |
| 21 | BTC-USD | $84,450.80 | $92,051.38 | take-profit | 4 | +91.21 |
| 22 | BTC-USD | $105,552.02 | $99,218.90 | stop-loss | 7 | -61.43 |
| 23 | BTC-USD | $107,135.34 | $115,987.20 | time exit (10 days) | 10 | +84.09 |
| 24 | BTC-USD | $123,344.06 | $115,943.42 | stop-loss | 5 | -61.43 |
| 25 | ETH-USD | $1,792.86 | $1,811.61 | time exit (10 days) | 10 | +10.73 |
| 26 | ETH-USD | $2,813.52 | $2,644.71 | stop-loss | 2 | -61.63 |
| 27 | ETH-USD | $2,543.01 | $2,771.89 | take-profit | 2 | +91.92 |

### Trend OOS-2 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $222.38 | $209.04 | stop-loss | 7 | -60.00 |
| 2 | AAPL | $200.90 | $188.85 | stop-loss | 3 | -59.64 |
| 3 | AAPL | $209.78 | $197.19 | stop-loss | 9 | -59.28 |
| 4 | AAPL | $202.94 | $200.53 | time exit (10 days) | 10 | -11.66 |
| 5 | AAPL | $200.53 | $209.00 | time exit (10 days) | 10 | +41.43 |
| 6 | AAPL | $218.97 | $224.07 | time exit (10 days) | 10 | +22.94 |
| 7 | MSFT | $384.19 | $371.03 | time exit (10 days) | 10 | -33.82 |
| 8 | MSFT | $376.93 | $354.31 | stop-loss | 6 | -59.04 |
| 9 | MSFT | $382.81 | $417.26 | take-profit | 5 | +88.03 |
| 10 | MSFT | $492.58 | $498.39 | time exit (10 days) | 10 | +11.64 |
| 11 | MSFT | $528.28 | $517.37 | time exit (10 days) | 10 | -20.40 |
| 12 | NVDA | $119.23 | $112.08 | stop-loss | 8 | -59.12 |
| 13 | NVDA | $107.30 | $100.86 | stop-loss | 4 | -58.82 |
| 14 | NVDA | $106.16 | $115.73 | take-profit | 9 | +87.80 |
| 15 | NVDA | $153.93 | $163.70 | time exit (10 days) | 10 | +62.37 |
| 16 | SPY | $554.78 | $521.49 | stop-loss | 10 | -59.36 |
| 17 | SPY | $528.84 | $545.49 | time exit (10 days) | 10 | +30.96 |
| 18 | SPY | $518.65 | $549.68 | time exit (10 days) | 10 | +59.02 |
| 19 | SPY | $603.67 | $615.26 | time exit (10 days) | 10 | +19.06 |
| 20 | SPY | $628.56 | $628.64 | time exit (10 days) | 10 | +0.13 |
| 21 | AMZN | $196.21 | $184.44 | stop-loss | 6 | -59.64 |
| 22 | AMZN | $184.87 | $173.78 | stop-loss | 3 | -59.28 |
| 23 | AMZN | $180.60 | $188.71 | time exit (10 days) | 10 | +44.11 |
| 24 | AMZN | $213.57 | $208.47 | time exit (10 days) | 10 | -23.56 |
| 25 | AMZN | $223.30 | $225.69 | time exit (10 days) | 10 | +10.54 |
| 26 | AMZN | $229.30 | $215.54 | stop-loss | 9 | -59.13 |
| 27 | AMZN | $232.23 | $218.30 | stop-loss | 6 | -58.76 |
| 28 | AMZN | $234.11 | $220.06 | stop-loss | 1 | -58.43 |
| 29 | GOOGL | $162.04 | $152.31 | stop-loss | 7 | -58.09 |
| 30 | GOOGL | $152.10 | $161.20 | time exit (10 days) | 10 | +57.53 |
| 31 | GOOGL | $157.72 | $171.92 | take-profit | 7 | +87.15 |
| 32 | GOOGL | $172.87 | $162.49 | stop-loss | 10 | -58.61 |
| 33 | GOOGL | $175.23 | $182.33 | time exit (10 days) | 10 | +39.34 |
| 34 | GOOGL | $179.56 | $195.73 | take-profit | 9 | +87.75 |
| 35 | GOOGL | $200.72 | $205.37 | time exit (10 days) | 10 | +22.79 |
| 36 | META | $623.29 | $585.89 | stop-loss | 3 | -59.14 |
| 37 | META | $530.58 | $578.33 | take-profit | 5 | +88.16 |
| 38 | META | $667.67 | $699.27 | time exit (10 days) | 10 | +46.79 |
| 39 | META | $730.66 | $718.00 | time exit (10 days) | 10 | -17.20 |
| 40 | META | $770.31 | $778.96 | time exit (10 days) | 10 | +11.14 |
| 41 | TSLA | $235.86 | $257.09 | take-profit | 3 | +89.34 |
| 42 | TSLA | $272.20 | $255.87 | stop-loss | 1 | -60.08 |
| 43 | TSLA | $250.74 | $273.31 | take-profit | 2 | +89.61 |
| 44 | TSLA | $340.47 | $320.04 | stop-loss | 3 | -60.27 |
| 45 | TSLA | $321.67 | $302.37 | stop-loss | 6 | -59.90 |
| 46 | TSLA | $322.27 | $320.11 | time exit (10 days) | 10 | -6.65 |
| 47 | JPM | $233.35 | $219.35 | stop-loss | 10 | -59.50 |
| 48 | JPM | $229.51 | $236.33 | time exit (10 days) | 10 | +29.29 |
| 49 | JPM | $267.21 | $285.07 | time exit (10 days) | 10 | +66.08 |
| 50 | JPM | $291.56 | $281.93 | time exit (10 days) | 10 | -32.88 |
| 51 | JNJ | $151.58 | $150.28 | time exit (10 days) | 10 | -8.49 |
| 52 | JNJ | $147.45 | $149.18 | time exit (10 days) | 10 | +11.64 |
| 53 | JNJ | $151.37 | $159.97 | time exit (10 days) | 10 | +56.36 |
| 54 | BTC-USD | $89,961.73 | $84,564.02 | stop-loss | 3 | -59.37 |
| 55 | BTC-USD | $84,343.11 | $87,471.70 | time exit (10 days) | 10 | +36.60 |
| 56 | BTC-USD | $83,404.84 | $87,518.91 | time exit (10 days) | 10 | +48.96 |
| 57 | BTC-USD | $106,446.01 | $107,802.33 | time exit (10 days) | 10 | +12.75 |
| 58 | BTC-USD | $109,678.08 | $104,638.09 | time exit (10 days) | 10 | -45.86 |
| 59 | BTC-USD | $110,257.23 | $103,641.80 | stop-loss | 3 | -59.54 |
| 60 | BTC-USD | $106,960.00 | $109,232.07 | time exit (10 days) | 10 | +20.90 |
| 61 | BTC-USD | $119,995.41 | $112,795.69 | stop-loss | 10 | -59.04 |
| 62 | BTC-USD | $119,306.76 | $114,274.74 | time exit (10 days) | 10 | -41.26 |
| 63 | ETH-USD | $1,927.00 | $2,100.44 | take-profit | 7 | +88.50 |
| 64 | ETH-USD | $1,622.77 | $1,768.83 | take-profit | 8 | +89.30 |
| 65 | ETH-USD | $2,773.53 | $2,607.12 | stop-loss | 2 | -60.06 |
| 66 | ETH-USD | $2,486.46 | $2,710.25 | take-profit | 9 | +89.56 |
| 67 | ETH-USD | $2,571.34 | $2,802.75 | take-profit | 8 | +90.37 |
| 68 | ETH-USD | $4,263.60 | $4,647.33 | take-profit | 4 | +91.17 |

### Trend OOS-3 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $225.90 | $225.66 | time exit (10 days) | 10 | -1.06 |
| 2 | AAPL | $233.37 | $244.71 | time exit (10 days) | 10 | +48.60 |
| 3 | MSFT | $420.36 | $424.60 | time exit (10 days) | 10 | +10.14 |
| 4 | MSFT | $425.80 | $400.26 | stop-loss | 1 | -60.33 |
| 5 | MSFT | $409.29 | $425.34 | time exit (10 days) | 10 | +39.19 |
| 6 | MSFT | $425.34 | $448.29 | time exit (10 days) | 10 | +54.14 |
| 7 | MSFT | $441.13 | $414.66 | stop-loss | 2 | -60.54 |
| 8 | NVDA | $121.12 | $132.02 | take-profit | 6 | +90.31 |
| 9 | NVDA | $149.04 | $140.10 | stop-loss | 1 | -60.71 |
| 10 | SPY | $596.26 | $589.19 | time exit (10 days) | 10 | -11.92 |
| 11 | AMZN | $189.70 | $199.50 | time exit (10 days) | 10 | +51.91 |
| 12 | AMZN | $234.85 | $229.15 | time exit (10 days) | 10 | -24.51 |
| 13 | GOOGL | $160.36 | $160.73 | time exit (10 days) | 10 | +2.30 |
| 14 | GOOGL | $194.26 | $194.46 | time exit (10 days) | 10 | +1.04 |
| 15 | META | $555.46 | $578.98 | time exit (10 days) | 10 | +42.67 |
| 16 | META | $609.79 | $593.78 | time exit (10 days) | 10 | -26.57 |
| 17 | META | $626.61 | $589.01 | stop-loss | 5 | -60.57 |
| 18 | META | $607.81 | $662.53 | take-profit | 7 | +90.33 |
| 19 | TSLA | $249.85 | $272.34 | take-profit | 4 | +91.13 |
| 20 | JPM | $213.57 | $213.59 | time exit (10 days) | 10 | +0.10 |
| 21 | JPM | $235.84 | $257.07 | take-profit | 7 | +91.96 |
| 22 | JNJ | $157.13 | $149.57 | time exit (10 days) | 10 | -49.56 |
| 23 | JNJ | $140.20 | $146.22 | time exit (10 days) | 10 | +44.01 |
| 24 | BTC-USD | $62,940.46 | $65,635.30 | time exit (10 days) | 10 | +43.93 |
| 25 | BTC-USD | $67,041.11 | $66,642.41 | time exit (10 days) | 10 | -6.14 |
| 26 | BTC-USD | $104,462.04 | $98,194.32 | stop-loss | 10 | -61.42 |
| 27 | ETH-USD | $2,648.55 | $2,489.63 | stop-loss | 8 | -61.66 |
| 28 | ETH-USD | $2,648.66 | $2,489.74 | stop-loss | 4 | -61.29 |
| 29 | ETH-USD | $2,895.59 | $3,156.19 | take-profit | 2 | +91.39 |

### Trend OOS-3 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $226.31 | $224.92 | time exit (10 days) | 10 | -6.13 |
| 2 | AAPL | $227.14 | $228.66 | time exit (10 days) | 10 | +6.69 |
| 3 | AAPL | $226.64 | $241.26 | time exit (10 days) | 10 | +64.53 |
| 4 | AAPL | $237.64 | $235.42 | time exit (10 days) | 10 | -9.38 |
| 5 | MSFT | $407.76 | $422.50 | time exit (10 days) | 10 | +36.35 |
| 6 | MSFT | $420.86 | $405.06 | time exit (10 days) | 10 | -37.89 |
| 7 | MSFT | $415.97 | $411.34 | time exit (10 days) | 10 | -11.19 |
| 8 | MSFT | $422.18 | $442.89 | time exit (10 days) | 10 | +49.27 |
| 9 | MSFT | $422.68 | $406.77 | time exit (10 days) | 10 | -37.99 |
| 10 | NVDA | $118.78 | $121.08 | time exit (10 days) | 10 | +19.46 |
| 11 | NVDA | $148.48 | $139.57 | stop-loss | 7 | -60.46 |
| 12 | NVDA | $139.85 | $152.45 | take-profit | 8 | +90.18 |
| 13 | NVDA | $140.46 | $132.04 | stop-loss | 4 | -60.58 |
| 14 | NVDA | $133.22 | $125.23 | stop-loss | 10 | -60.25 |
| 15 | SPY | $547.65 | $558.58 | time exit (10 days) | 10 | +19.92 |
| 16 | SPY | $563.13 | $566.17 | time exit (10 days) | 10 | +5.39 |
| 17 | SPY | $582.17 | $580.28 | time exit (10 days) | 10 | -3.26 |
| 18 | SPY | $584.05 | $589.20 | time exit (10 days) | 10 | +8.82 |
| 19 | SPY | $586.07 | $586.25 | time exit (10 days) | 10 | +0.31 |
| 20 | AMZN | $189.07 | $195.78 | time exit (10 days) | 10 | +35.54 |
| 21 | AMZN | $190.83 | $208.01 | take-profit | 7 | +90.47 |
| 22 | AMZN | $197.93 | $215.75 | take-profit | 9 | +91.29 |
| 23 | AMZN | $213.44 | $232.66 | take-profit | 9 | +92.13 |
| 24 | AMZN | $235.01 | $236.17 | time exit (10 days) | 10 | +5.10 |
| 25 | GOOGL | $156.96 | $164.69 | time exit (10 days) | 10 | +50.88 |
| 26 | GOOGL | $163.81 | $165.56 | time exit (10 days) | 10 | +11.09 |
| 27 | GOOGL | $165.56 | $180.47 | take-profit | 2 | +93.59 |
| 28 | GOOGL | $174.35 | $190.04 | take-profit | 2 | +94.37 |
| 29 | GOOGL | $199.04 | $187.10 | stop-loss | 8 | -63.46 |
| 30 | GOOGL | $202.83 | $190.66 | stop-loss | 3 | -63.09 |
| 31 | META | $529.81 | $568.72 | time exit (10 days) | 10 | +76.76 |
| 32 | META | $581.02 | $546.16 | stop-loss | 7 | -63.16 |
| 33 | META | $588.97 | $620.68 | time exit (10 days) | 10 | +56.34 |
| 34 | META | $614.37 | $632.82 | time exit (10 days) | 10 | +31.60 |
| 35 | META | $612.94 | $668.11 | take-profit | 5 | +94.98 |
| 36 | TSLA | $260.48 | $244.85 | stop-loss | 7 | -63.89 |
| 37 | TSLA | $389.22 | $424.25 | take-profit | 3 | +95.26 |
| 38 | JPM | $202.65 | $214.25 | time exit (10 days) | 10 | +61.11 |
| 39 | JPM | $237.37 | $231.33 | time exit (10 days) | 10 | -27.32 |
| 40 | JPM | $232.60 | $253.53 | take-profit | 9 | +96.42 |
| 41 | JNJ | $155.46 | $151.66 | time exit (10 days) | 10 | -26.41 |
| 42 | JNJ | $147.00 | $142.86 | time exit (10 days) | 10 | -30.36 |
| 43 | JNJ | $139.02 | $137.96 | time exit (10 days) | 10 | -8.20 |
| 44 | BTC-USD | $58,127.01 | $63,358.45 | take-profit | 7 | +96.26 |
| 45 | BTC-USD | $66,046.12 | $68,161.05 | time exit (10 days) | 10 | +34.68 |
| 46 | BTC-USD | $69,907.76 | $76,199.46 | take-profit | 9 | +97.52 |
| 47 | BTC-USD | $75,639.08 | $82,446.61 | take-profit | 5 | +98.71 |
| 48 | BTC-USD | $106,029.72 | $99,667.94 | stop-loss | 3 | -66.16 |
| 49 | BTC-USD | $98,314.96 | $92,416.06 | stop-loss | 4 | -65.48 |
| 50 | BTC-USD | $100,504.49 | $104,714.65 | time exit (10 days) | 10 | +45.47 |
| 51 | ETH-USD | $2,538.19 | $2,385.90 | stop-loss | 2 | -65.91 |
| 52 | ETH-USD | $2,339.84 | $2,550.43 | take-profit | 9 | +98.26 |
| 53 | ETH-USD | $2,628.90 | $2,471.17 | stop-loss | 9 | -66.10 |
| 54 | ETH-USD | $2,657.37 | $2,497.93 | stop-loss | 2 | -65.71 |
| 55 | ETH-USD | $2,895.59 | $3,156.19 | take-profit | 2 | +97.96 |
| 56 | ETH-USD | $3,361.05 | $3,663.55 | take-profit | 6 | +98.86 |
| 57 | ETH-USD | $3,605.01 | $3,388.71 | stop-loss | 4 | -66.49 |
| 58 | ETH-USD | $3,474.11 | $3,265.66 | stop-loss | 1 | -66.10 |
| 59 | ETH-USD | $3,327.41 | $3,127.76 | stop-loss | 6 | -65.70 |
| 60 | ETH-USD | $3,298.27 | $3,100.37 | stop-loss | 2 | -65.31 |
| 61 | ETH-USD | $2,726.09 | $2,562.53 | stop-loss | 10 | -64.90 |

### Trend FRESH-1 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $181.40 | $188.08 | time exit (10 days) | 10 | +36.81 |
| 2 | MSFT | $415.75 | $407.49 | time exit (10 days) | 10 | -19.94 |
| 3 | NVDA | $90.15 | $94.68 | time exit (10 days) | 10 | +50.28 |
| 4 | SPY | $505.25 | $510.88 | time exit (10 days) | 10 | +11.21 |
| 5 | AMZN | $188.00 | $183.13 | time exit (10 days) | 10 | -26.11 |
| 6 | AMZN | $184.06 | $200.00 | time exit (10 days) | 10 | +87.05 |
| 7 | GOOGL | $147.34 | $149.11 | time exit (10 days) | 10 | +12.19 |
| 8 | META | $474.19 | $498.36 | time exit (10 days) | 10 | +51.75 |
| 9 | META | $524.60 | $515.23 | time exit (10 days) | 10 | -18.23 |
| 10 | TSLA | $181.19 | $170.32 | stop-loss | 3 | -61.10 |
| 11 | TSLA | $187.44 | $204.32 | take-profit | 9 | +91.17 |
| 12 | JPM | $182.33 | $185.73 | time exit (10 days) | 10 | +19.03 |
| 13 | JPM | $195.11 | $203.99 | time exit (10 days) | 10 | +46.60 |
| 14 | JNJ | $141.19 | $135.80 | time exit (10 days) | 10 | -39.22 |
| 15 | JNJ | $136.98 | $146.13 | time exit (10 days) | 10 | +68.43 |
| 16 | JNJ | $140.49 | $146.93 | time exit (10 days) | 10 | +47.23 |
| 17 | BTC-USD | $66,940.80 | $68,296.22 | time exit (10 days) | 10 | +20.87 |
| 18 | BTC-USD | $66,710.16 | $66,819.91 | time exit (10 days) | 10 | +1.70 |
| 19 | ETH-USD | $3,789.31 | $3,561.95 | stop-loss | 2 | -62.27 |
| 20 | ETH-USD | $3,505.73 | $3,295.39 | stop-loss | 6 | -61.90 |

### Trend FRESH-1 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $171.85 | $167.02 | time exit (10 days) | 10 | -28.09 |
| 2 | AAPL | $168.06 | $183.19 | take-profit | 6 | +89.79 |
| 3 | AAPL | $194.02 | $211.49 | take-profit | 5 | +90.59 |
| 4 | AAPL | $195.03 | $212.59 | take-profit | 3 | +91.40 |
| 5 | AAPL | $205.19 | $211.24 | time exit (10 days) | 10 | +30.18 |
| 6 | AAPL | $218.19 | $226.72 | time exit (10 days) | 10 | +40.16 |
| 7 | AAPL | $219.88 | $224.61 | time exit (10 days) | 10 | +22.18 |
| 8 | MSFT | $417.10 | $412.69 | time exit (10 days) | 10 | -10.93 |
| 9 | MSFT | $405.64 | $417.97 | time exit (10 days) | 10 | +31.37 |
| 10 | MSFT | $425.18 | $444.33 | time exit (10 days) | 10 | +46.63 |
| 11 | MSFT | $409.64 | $404.21 | time exit (10 days) | 10 | -13.79 |
| 12 | NVDA | $86.16 | $91.10 | time exit (10 days) | 10 | +59.61 |
| 13 | NVDA | $85.57 | $93.28 | take-profit | 9 | +94.11 |
| 14 | NVDA | $115.82 | $126.25 | take-profit | 4 | +94.95 |
| 15 | SPY | $498.50 | $507.22 | time exit (10 days) | 10 | +18.62 |
| 16 | SPY | $500.40 | $503.93 | time exit (10 days) | 10 | +7.51 |
| 17 | SPY | $505.55 | $498.36 | time exit (10 days) | 10 | -15.17 |
| 18 | SPY | $508.17 | $503.14 | time exit (10 days) | 10 | -10.53 |
| 19 | SPY | $496.63 | $514.27 | time exit (10 days) | 10 | +37.79 |
| 20 | SPY | $519.33 | $530.60 | time exit (10 days) | 10 | +23.18 |
| 21 | SPY | $540.47 | $534.97 | time exit (10 days) | 10 | -10.89 |
| 22 | SPY | $529.86 | $544.04 | time exit (10 days) | 10 | +28.61 |
| 23 | AMZN | $180.97 | $183.62 | time exit (10 days) | 10 | +15.69 |
| 24 | AMZN | $185.07 | $173.97 | stop-loss | 10 | -64.37 |
| 25 | AMZN | $186.21 | $184.70 | time exit (10 days) | 10 | -8.65 |
| 26 | AMZN | $184.30 | $185.57 | time exit (10 days) | 10 | +7.35 |
| 27 | AMZN | $177.59 | $172.12 | time exit (10 days) | 10 | -32.86 |
| 28 | GOOGL | $137.19 | $149.55 | take-profit | 4 | +95.77 |
| 29 | GOOGL | $170.33 | $167.06 | time exit (10 days) | 10 | -20.59 |
| 30 | GOOGL | $182.50 | $189.60 | time exit (10 days) | 10 | +41.64 |
| 31 | GOOGL | $161.61 | $162.03 | time exit (10 days) | 10 | +2.80 |
| 32 | META | $522.89 | $491.52 | stop-loss | 8 | -64.52 |
| 33 | META | $468.61 | $463.83 | time exit (10 days) | 10 | -10.91 |
| 34 | META | $535.89 | $503.73 | stop-loss | 5 | -64.08 |
| 35 | META | $484.50 | $455.43 | stop-loss | 1 | -63.69 |
| 36 | TSLA | $172.82 | $162.45 | stop-loss | 10 | -63.31 |
| 37 | TSLA | $170.18 | $185.50 | take-profit | 2 | +94.41 |
| 38 | TSLA | $178.01 | $194.03 | take-profit | 7 | +95.23 |
| 39 | JPM | $181.90 | $187.75 | time exit (10 days) | 10 | +34.34 |
| 40 | JPM | $183.63 | $187.56 | time exit (10 days) | 10 | +22.90 |
| 41 | JPM | $188.10 | $198.43 | time exit (10 days) | 10 | +58.97 |
| 42 | JPM | $202.01 | $212.19 | time exit (10 days) | 10 | +54.38 |
| 43 | JNJ | $151.78 | $145.28 | time exit (10 days) | 10 | -46.47 |
| 44 | JNJ | $147.11 | $138.28 | stop-loss | 8 | -64.82 |
| 45 | JNJ | $139.49 | $138.71 | time exit (10 days) | 10 | -6.00 |
| 46 | JNJ | $138.94 | $137.72 | time exit (10 days) | 10 | -9.44 |
| 47 | JNJ | $137.72 | $145.44 | time exit (10 days) | 10 | +60.09 |
| 48 | JNJ | $138.26 | $143.24 | time exit (10 days) | 10 | +38.86 |
| 49 | BTC-USD | $64,031.13 | $66,267.49 | time exit (10 days) | 10 | +37.57 |
| 50 | BTC-USD | $61,448.39 | $66,978.76 | take-profit | 5 | +97.33 |
| 51 | BTC-USD | $71,082.82 | $66,817.85 | stop-loss | 6 | -65.68 |
| 52 | BTC-USD | $57,899.46 | $63,110.42 | take-profit | 3 | +97.97 |
| 53 | BTC-USD | $59,493.45 | $64,847.86 | take-profit | 4 | +98.52 |
| 54 | ETH-USD | $3,695.29 | $3,473.58 | stop-loss | 1 | -66.49 |
| 55 | ETH-USD | $3,219.91 | $3,026.72 | stop-loss | 7 | -66.11 |
| 56 | ETH-USD | $3,117.58 | $2,930.52 | stop-loss | 6 | -65.71 |
| 57 | ETH-USD | $3,037.06 | $3,310.40 | take-profit | 5 | +97.97 |
| 58 | ETH-USD | $3,177.20 | $3,463.15 | take-profit | 2 | +98.85 |
| 59 | ETH-USD | $2,662.91 | $2,769.39 | time exit (10 days) | 10 | +44.31 |

### Trend FRESH-2 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $180.47 | $173.15 | time exit (10 days) | 10 | -40.56 |
| 2 | AAPL | $176.34 | $165.75 | stop-loss | 8 | -59.78 |
| 3 | AAPL | $179.98 | $187.68 | time exit (10 days) | 10 | +42.38 |
| 4 | AAPL | $189.42 | $178.06 | stop-loss | 4 | -59.63 |
| 5 | MSFT | $325.26 | $313.43 | time exit (10 days) | 10 | -35.95 |
| 6 | MSFT | $325.03 | $329.59 | time exit (10 days) | 10 | +13.82 |
| 7 | MSFT | $374.77 | $396.41 | time exit (10 days) | 10 | +56.94 |
| 8 | NVDA | $46.81 | $44.00 | stop-loss | 3 | -59.44 |
| 9 | NVDA | $48.19 | $48.10 | time exit (10 days) | 10 | -1.86 |
| 10 | NVDA | $47.97 | $48.96 | time exit (10 days) | 10 | +20.30 |
| 11 | SPY | $428.15 | $415.10 | time exit (10 days) | 10 | -30.10 |
| 12 | SPY | $418.40 | $439.09 | time exit (10 days) | 10 | +48.70 |
| 13 | AMZN | $138.07 | $142.83 | time exit (10 days) | 10 | +34.11 |
| 14 | GOOGL | $139.23 | $130.87 | stop-loss | 10 | -59.59 |
| 15 | GOOGL | $134.97 | $126.87 | stop-loss | 9 | -59.20 |
| 16 | GOOGL | $137.04 | $134.45 | time exit (10 days) | 10 | -18.51 |
| 17 | META | $302.17 | $294.92 | time exit (10 days) | 10 | -23.48 |
| 18 | META | $325.65 | $331.52 | time exit (10 days) | 10 | +17.60 |
| 19 | META | $347.04 | $343.83 | time exit (10 days) | 10 | -9.04 |
| 20 | TSLA | $251.92 | $274.60 | take-profit | 3 | +88.02 |
| 21 | TSLA | $258.87 | $243.34 | stop-loss | 4 | -59.18 |
| 22 | TSLA | $235.60 | $238.72 | time exit (10 days) | 10 | +12.99 |
| 23 | JPM | $136.42 | $135.85 | time exit (10 days) | 10 | -4.07 |
| 24 | JPM | $138.44 | $130.13 | stop-loss | 8 | -58.89 |
| 25 | JPM | $139.29 | $144.81 | time exit (10 days) | 10 | +38.66 |
| 26 | JNJ | $140.35 | $143.54 | time exit (10 days) | 10 | +22.23 |
| 27 | BTC-USD | $26,754.28 | $27,021.55 | time exit (10 days) | 10 | +9.78 |
| 28 | BTC-USD | $42,658.67 | $46,497.95 | take-profit | 4 | +88.30 |
| 29 | ETH-USD | $1,733.81 | $1,629.78 | stop-loss | 3 | -59.48 |
| 30 | ETH-USD | $1,784.44 | $1,832.80 | time exit (10 days) | 10 | +26.71 |
| 31 | ETH-USD | $2,507.57 | $2,733.25 | take-profit | 3 | +88.92 |

### Trend FRESH-2 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $171.34 | $173.49 | time exit (10 days) | 10 | +12.53 |
| 2 | AAPL | $175.20 | $187.43 | time exit (10 days) | 10 | +69.89 |
| 3 | AAPL | $193.35 | $191.27 | time exit (10 days) | 10 | -10.86 |
| 4 | AAPL | $195.58 | $191.25 | time exit (10 days) | 10 | -22.28 |
| 5 | AAPL | $189.25 | $177.90 | stop-loss | 10 | -60.28 |
| 6 | MSFT | $319.77 | $319.19 | time exit (10 days) | 10 | -1.81 |
| 7 | MSFT | $374.77 | $396.41 | time exit (10 days) | 10 | +57.67 |
| 8 | MSFT | $405.40 | $403.79 | time exit (10 days) | 10 | -3.98 |
| 9 | NVDA | $44.65 | $45.96 | time exit (10 days) | 10 | +29.49 |
| 10 | NVDA | $44.87 | $48.91 | take-profit | 6 | +90.65 |
| 11 | NVDA | $48.75 | $48.03 | time exit (10 days) | 10 | -14.98 |
| 12 | NVDA | $52.10 | $56.79 | take-profit | 7 | +91.29 |
| 13 | SPY | $416.90 | $405.49 | time exit (10 days) | 10 | -28.02 |
| 14 | SPY | $415.43 | $434.20 | time exit (10 days) | 10 | +46.14 |
| 15 | SPY | $447.58 | $461.41 | time exit (10 days) | 10 | +31.69 |
| 16 | SPY | $468.13 | $476.94 | time exit (10 days) | 10 | +19.36 |
| 17 | AMZN | $131.83 | $123.92 | stop-loss | 10 | -61.84 |
| 18 | AMZN | $128.56 | $120.85 | stop-loss | 1 | -61.44 |
| 19 | AMZN | $132.71 | $142.59 | time exit (10 days) | 10 | +75.81 |
| 20 | AMZN | $154.07 | $148.47 | time exit (10 days) | 10 | -37.29 |
| 21 | AMZN | $154.62 | $161.26 | time exit (10 days) | 10 | +43.90 |
| 22 | AMZN | $155.34 | $169.32 | take-profit | 10 | +92.39 |
| 23 | GOOGL | $136.28 | $134.32 | time exit (10 days) | 10 | -14.92 |
| 24 | GOOGL | $130.60 | $137.18 | time exit (10 days) | 10 | +52.13 |
| 25 | GOOGL | $134.52 | $137.61 | time exit (10 days) | 10 | +23.88 |
| 26 | GOOGL | $140.94 | $150.44 | time exit (10 days) | 10 | +70.24 |
| 27 | META | $303.91 | $318.10 | time exit (10 days) | 10 | +48.98 |
| 28 | META | $312.80 | $336.74 | time exit (10 days) | 10 | +80.64 |
| 29 | META | $331.74 | $343.00 | time exit (10 days) | 10 | +36.03 |
| 30 | META | $366.96 | $389.45 | time exit (10 days) | 10 | +65.32 |
| 31 | TSLA | $260.05 | $244.45 | stop-loss | 9 | -64.31 |
| 32 | TSLA | $219.27 | $206.11 | stop-loss | 4 | -63.95 |
| 33 | TSLA | $251.05 | $248.48 | time exit (10 days) | 10 | -10.84 |
| 34 | TSLA | $189.56 | $191.97 | time exit (10 days) | 10 | +13.45 |
| 35 | JPM | $139.02 | $137.48 | time exit (10 days) | 10 | -11.77 |
| 36 | JPM | $137.48 | $136.82 | time exit (10 days) | 10 | -5.06 |
| 37 | JPM | $135.85 | $132.31 | time exit (10 days) | 10 | -27.53 |
| 38 | JPM | $135.20 | $143.84 | time exit (10 days) | 10 | +67.43 |
| 39 | JPM | $166.42 | $164.53 | time exit (10 days) | 10 | -12.09 |
| 40 | JPM | $169.82 | $174.94 | time exit (10 days) | 10 | +31.95 |
| 41 | JNJ | $150.59 | $144.27 | time exit (10 days) | 10 | -44.64 |
| 42 | JNJ | $145.58 | $139.02 | time exit (10 days) | 10 | -47.76 |
| 43 | JNJ | $138.97 | $137.55 | time exit (10 days) | 10 | -10.79 |
| 44 | JNJ | $148.07 | $148.50 | time exit (10 days) | 10 | +3.03 |
| 45 | BTC-USD | $28,519.47 | $31,086.22 | take-profit | 7 | +94.71 |
| 46 | BTC-USD | $37,313.97 | $35,075.13 | stop-loss | 4 | -63.58 |
| 47 | BTC-USD | $39,476.33 | $43,029.21 | take-profit | 3 | +94.86 |
| 48 | BTC-USD | $46,970.50 | $44,152.27 | stop-loss | 4 | -63.97 |
| 49 | BTC-USD | $43,288.25 | $45,301.57 | time exit (10 days) | 10 | +49.13 |
| 50 | ETH-USD | $1,607.99 | $1,593.86 | time exit (10 days) | 10 | -9.36 |
| 51 | ETH-USD | $1,604.67 | $1,749.09 | take-profit | 3 | +95.75 |
| 52 | ETH-USD | $2,193.69 | $2,391.13 | take-profit | 6 | +96.61 |
| 53 | ETH-USD | $2,347.57 | $2,206.71 | stop-loss | 6 | -64.98 |
| 54 | ETH-USD | $2,355.84 | $2,214.49 | stop-loss | 1 | -64.60 |
| 55 | ETH-USD | $2,582.10 | $2,427.18 | stop-loss | 8 | -64.20 |
| 56 | ETH-USD | $2,372.20 | $2,585.70 | take-profit | 6 | +95.73 |

### Trend FRESH-3 — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $150.54 | $158.19 | time exit (10 days) | 10 | +50.84 |
| 2 | MSFT | $271.86 | $280.49 | time exit (10 days) | 10 | +31.89 |
| 3 | SPY | $386.52 | $394.91 | time exit (10 days) | 10 | +21.87 |
| 4 | SPY | $397.56 | $403.87 | time exit (10 days) | 10 | +16.03 |
| 5 | AMZN | $98.70 | $101.10 | time exit (10 days) | 10 | +24.61 |
| 6 | AMZN | $139.57 | $131.20 | stop-loss | 10 | -60.84 |
| 7 | GOOGL | $100.27 | $103.38 | time exit (10 days) | 10 | +31.32 |
| 8 | GOOGL | $120.38 | $131.23 | take-profit | 3 | +91.13 |
| 9 | TSLA | $207.46 | $195.01 | stop-loss | 1 | -61.25 |
| 10 | TSLA | $180.14 | $196.36 | take-profit | 5 | +91.35 |
| 11 | JPM | $129.36 | $130.63 | time exit (10 days) | 10 | +10.04 |
| 12 | JPM | $129.95 | $132.53 | time exit (10 days) | 10 | +20.32 |
| 13 | JNJ | $149.85 | $148.01 | time exit (10 days) | 10 | -12.60 |
| 14 | JNJ | $147.29 | $149.60 | time exit (10 days) | 10 | +16.10 |
| 15 | JNJ | $157.16 | $157.88 | time exit (10 days) | 10 | +4.70 |
| 16 | BTC-USD | $26,965.88 | $27,268.13 | time exit (10 days) | 10 | +11.52 |
| 17 | BTC-USD | $29,534.38 | $27,762.32 | stop-loss | 3 | -61.67 |
| 18 | BTC-USD | $27,119.07 | $25,491.92 | stop-loss | 1 | -61.34 |
| 19 | BTC-USD | $29,912.28 | $30,620.77 | time exit (10 days) | 10 | +24.02 |
| 20 | ETH-USD | $1,785.58 | $1,793.00 | time exit (10 days) | 10 | +4.24 |
| 21 | ETH-USD | $1,901.03 | $1,786.97 | stop-loss | 6 | -61.15 |
| 22 | ETH-USD | $1,859.43 | $1,848.64 | time exit (10 days) | 10 | -5.88 |

### Trend FRESH-3 — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $153.35 | $159.76 | time exit (10 days) | 10 | +41.79 |
| 2 | AAPL | $166.87 | $169.54 | time exit (10 days) | 10 | +16.06 |
| 3 | AAPL | $170.79 | $172.59 | time exit (10 days) | 10 | +10.62 |
| 4 | AAPL | $172.48 | $178.29 | time exit (10 days) | 10 | +33.91 |
| 5 | AAPL | $174.65 | $181.25 | time exit (10 days) | 10 | +38.18 |
| 6 | AAPL | $185.30 | $186.99 | time exit (10 days) | 10 | +9.25 |
| 7 | MSFT | $258.25 | $272.91 | time exit (10 days) | 10 | +57.60 |
| 8 | MSFT | $296.58 | $301.71 | time exit (10 days) | 10 | +17.67 |
| 9 | MSFT | $310.57 | $327.03 | time exit (10 days) | 10 | +54.18 |
| 10 | MSFT | $317.79 | $318.64 | time exit (10 days) | 10 | +2.75 |
| 11 | MSFT | $339.41 | $332.04 | time exit (10 days) | 10 | -22.34 |
| 12 | MSFT | $337.10 | $327.54 | time exit (10 days) | 10 | -29.11 |
| 13 | MSFT | $342.22 | $321.69 | stop-loss | 2 | -61.38 |
| 14 | NVDA | $25.46 | $27.30 | time exit (10 days) | 10 | +73.48 |
| 15 | NVDA | $28.12 | $29.12 | time exit (10 days) | 10 | +36.40 |
| 16 | NVDA | $28.59 | $31.17 | take-profit | 9 | +92.79 |
| 17 | NVDA | $28.86 | $31.46 | take-profit | 3 | +93.38 |
| 18 | NVDA | $45.33 | $46.61 | time exit (10 days) | 10 | +29.55 |
| 19 | SPY | $381.94 | $391.28 | time exit (10 days) | 10 | +25.67 |
| 20 | SPY | $401.39 | $409.71 | time exit (10 days) | 10 | +21.79 |
| 21 | SPY | $402.15 | $415.34 | time exit (10 days) | 10 | +34.58 |
| 22 | SPY | $426.49 | $436.48 | time exit (10 days) | 10 | +24.78 |
| 23 | SPY | $432.03 | $434.85 | time exit (10 days) | 10 | +6.91 |
| 24 | AMZN | $96.20 | $100.25 | time exit (10 days) | 10 | +44.66 |
| 25 | AMZN | $104.30 | $103.65 | time exit (10 days) | 10 | -6.64 |
| 26 | AMZN | $110.19 | $116.75 | time exit (10 days) | 10 | +63.38 |
| 27 | AMZN | $134.68 | $126.60 | stop-loss | 8 | -64.25 |
| 28 | AMZN | $135.36 | $127.24 | stop-loss | 5 | -63.86 |
| 29 | AMZN | $139.57 | $131.20 | stop-loss | 10 | -63.46 |
| 30 | GOOGL | $93.08 | $101.47 | take-profit | 3 | +94.76 |
| 31 | GOOGL | $110.70 | $120.67 | take-profit | 6 | +95.62 |
| 32 | GOOGL | $124.24 | $131.33 | time exit (10 days) | 10 | +61.13 |
| 33 | GOOGL | $128.05 | $128.44 | time exit (10 days) | 10 | +3.27 |
| 34 | META | $195.87 | $203.40 | time exit (10 days) | 10 | +41.39 |
| 35 | META | $238.04 | $231.59 | time exit (10 days) | 10 | -29.30 |
| 36 | META | $244.51 | $266.52 | take-profit | 9 | +97.09 |
| 37 | META | $279.16 | $284.26 | time exit (10 days) | 10 | +19.90 |
| 38 | META | $306.41 | $288.02 | stop-loss | 8 | -65.42 |
| 39 | META | $315.58 | $296.64 | stop-loss | 10 | -65.03 |
| 40 | TSLA | $191.81 | $180.30 | stop-loss | 8 | -64.64 |
| 41 | TSLA | $170.06 | $180.14 | time exit (10 days) | 10 | +63.46 |
| 42 | TSLA | $282.48 | $265.53 | stop-loss | 3 | -64.63 |
| 43 | JPM | $118.18 | $128.34 | time exit (10 days) | 10 | +92.01 |
| 44 | JPM | $128.76 | $128.68 | time exit (10 days) | 10 | -0.67 |
| 45 | JPM | $129.95 | $132.53 | time exit (10 days) | 10 | +21.41 |
| 46 | JPM | $134.55 | $142.87 | time exit (10 days) | 10 | +66.89 |
| 47 | JNJ | $144.33 | $149.63 | time exit (10 days) | 10 | +39.94 |
| 48 | JNJ | $153.51 | $155.57 | time exit (10 days) | 10 | +14.69 |
| 49 | BTC-USD | $24,746.07 | $26,973.23 | take-profit | 3 | +98.44 |
| 50 | BTC-USD | $30,235.06 | $28,420.96 | stop-loss | 9 | -66.21 |
| 51 | BTC-USD | $26,868.35 | $27,238.78 | time exit (10 days) | 10 | +15.11 |
| 52 | BTC-USD | $27,238.78 | $25,604.46 | stop-loss | 4 | -65.86 |
| 53 | BTC-USD | $26,510.68 | $28,896.63 | take-profit | 4 | +98.06 |
| 54 | BTC-USD | $29,765.49 | $27,979.56 | stop-loss | 9 | -66.08 |
| 55 | ETH-USD | $1,680.31 | $1,831.54 | take-profit | 5 | +98.57 |
| 56 | ETH-USD | $1,854.38 | $1,907.26 | time exit (10 days) | 10 | +31.52 |
| 57 | ETH-USD | $1,792.12 | $1,933.19 | time exit (10 days) | 10 | +87.24 |
| 58 | ETH-USD | $2,006.51 | $1,886.12 | stop-loss | 4 | -67.02 |
| 59 | ETH-USD | $1,850.75 | $1,739.71 | stop-loss | 7 | -66.61 |

### Trend Phase-4 window (in-sample) — SMA trend-following (buy SMA-10 cross above SMA-30)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $315.05 | $332.73 | time exit (10 days) | 10 | +56.12 |
| 2 | AAPL | $328.21 | $336.13 | time exit (10 days) | 10 | +24.27 |
| 3 | MSFT | $426.19 | $464.54 | take-profit | 2 | +90.71 |
| 4 | MSFT | $400.35 | $436.38 | take-profit | 10 | +91.54 |
| 5 | NVDA | $202.58 | $190.43 | stop-loss | 8 | -61.57 |
| 6 | NVDA | $206.41 | $225.00 | take-profit | 8 | +91.88 |
| 7 | NVDA | $224.58 | $230.48 | time exit (10 days) | 10 | +27.04 |
| 8 | SPY | $753.08 | $737.10 | time exit (10 days) | 10 | -21.90 |
| 9 | SPY | $769.42 | $765.55 | time exit (10 days) | 10 | -5.18 |
| 10 | SPY | $765.61 | $778.10 | time exit (10 days) | 10 | +16.79 |
| 11 | AMZN | $247.49 | $232.64 | stop-loss | 7 | -61.86 |
| 12 | AMZN | $284.02 | $266.98 | stop-loss | 8 | -61.48 |
| 13 | AMZN | $259.53 | $249.09 | time exit (10 days) | 10 | -40.98 |
| 14 | GOOGL | $359.28 | $337.72 | stop-loss | 7 | -60.88 |
| 15 | GOOGL | $357.29 | $347.84 | time exit (10 days) | 10 | -26.67 |
| 16 | GOOGL | $351.16 | $347.68 | time exit (10 days) | 10 | -9.97 |
| 17 | META | $668.68 | $628.56 | stop-loss | 5 | -60.29 |
| 18 | META | $616.28 | $671.75 | take-profit | 6 | +89.89 |
| 19 | TSLA | $407.76 | $383.29 | stop-loss | 5 | -60.48 |
| 20 | TSLA | $348.95 | $380.37 | take-profit | 8 | +90.19 |
| 21 | JPM | $306.23 | $333.79 | take-profit | 5 | +90.98 |
| 22 | JNJ | $229.05 | $235.84 | time exit (10 days) | 10 | +30.23 |
| 23 | JNJ | $260.79 | $265.77 | time exit (10 days) | 10 | +19.52 |
| 24 | JNJ | $271.22 | $254.95 | stop-loss | 6 | -61.47 |
| 25 | BTC-USD | $73,032.76 | $79,605.71 | take-profit | 4 | +91.36 |
| 26 | BTC-USD | $86,602.91 | $84,853.10 | time exit (10 days) | 10 | -20.65 |
| 27 | ETH-USD | $2,251.46 | $2,454.10 | take-profit | 2 | +92.30 |

### Trend Phase-4 window (in-sample) — MACD trend-following (buy MACD cross above signal line)

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $308.36 | $333.45 | time exit (10 days) | 10 | +81.35 |
| 2 | AAPL | $313.45 | $326.57 | time exit (10 days) | 10 | +42.20 |
| 3 | AAPL | $342.96 | $343.83 | time exit (10 days) | 10 | +2.57 |
| 4 | AAPL | $348.22 | $327.33 | stop-loss | 8 | -60.75 |
| 5 | MSFT | $449.39 | $422.43 | stop-loss | 5 | -60.39 |
| 6 | MSFT | $389.76 | $393.08 | time exit (10 days) | 10 | +8.53 |
| 7 | MSFT | $512.80 | $539.44 | time exit (10 days) | 10 | +52.02 |
| 8 | NVDA | $203.89 | $211.82 | time exit (10 days) | 10 | +39.14 |
| 9 | NVDA | $211.70 | $219.49 | time exit (10 days) | 10 | +37.17 |
| 10 | NVDA | $228.19 | $214.50 | stop-loss | 6 | -60.86 |
| 11 | NVDA | $228.87 | $239.24 | time exit (10 days) | 10 | +45.68 |
| 12 | SPY | $749.42 | $740.25 | time exit (10 days) | 10 | -12.39 |
| 13 | SPY | $755.79 | $770.76 | time exit (10 days) | 10 | +20.03 |
| 14 | SPY | $773.50 | $774.83 | time exit (10 days) | 10 | +1.74 |
| 15 | SPY | $769.64 | $763.25 | time exit (10 days) | 10 | -8.42 |
| 16 | AMZN | $241.70 | $249.89 | time exit (10 days) | 10 | +34.32 |
| 17 | AMZN | $271.58 | $262.65 | time exit (10 days) | 10 | -33.41 |
| 18 | AMZN | $251.40 | $262.45 | time exit (10 days) | 10 | +44.52 |
| 19 | GOOGL | $359.68 | $346.55 | time exit (10 days) | 10 | -37.13 |
| 20 | GOOGL | $355.90 | $345.68 | time exit (10 days) | 10 | -29.11 |
| 21 | GOOGL | $349.39 | $342.75 | time exit (10 days) | 10 | -19.21 |
| 22 | GOOGL | $346.47 | $344.18 | time exit (10 days) | 10 | -6.67 |
| 23 | META | $634.17 | $596.12 | stop-loss | 4 | -60.49 |
| 24 | META | $621.91 | $584.60 | stop-loss | 2 | -60.12 |
| 25 | META | $612.43 | $667.55 | take-profit | 6 | +89.65 |
| 26 | META | $589.38 | $554.02 | stop-loss | 2 | -60.30 |
| 27 | META | $575.69 | $627.51 | take-profit | 9 | +89.93 |
| 28 | TSLA | $440.36 | $413.94 | stop-loss | 4 | -60.47 |
| 29 | TSLA | $420.60 | $395.36 | stop-loss | 2 | -60.12 |
| 30 | TSLA | $328.58 | $358.15 | take-profit | 10 | +89.62 |
| 31 | TSLA | $366.20 | $354.11 | time exit (10 days) | 10 | -33.17 |
| 32 | TSLA | $380.68 | $357.84 | stop-loss | 7 | -60.09 |
| 33 | TSLA | $386.47 | $385.19 | time exit (10 days) | 10 | -3.30 |
| 34 | JPM | $307.96 | $322.15 | time exit (10 days) | 10 | +45.86 |
| 35 | JPM | $345.19 | $343.00 | time exit (10 days) | 10 | -6.34 |
| 36 | JPM | $346.48 | $357.46 | time exit (10 days) | 10 | +31.66 |
| 37 | JPM | $357.46 | $355.49 | time exit (10 days) | 10 | -5.51 |
| 38 | JPM | $363.37 | $354.73 | time exit (10 days) | 10 | -23.81 |
| 39 | JPM | $334.30 | $334.04 | time exit (10 days) | 10 | -0.78 |
| 40 | JNJ | $231.63 | $230.15 | time exit (10 days) | 10 | -6.37 |
| 41 | JNJ | $237.91 | $259.33 | take-profit | 7 | +89.93 |
| 42 | JNJ | $264.64 | $260.53 | time exit (10 days) | 10 | -15.67 |
| 43 | JNJ | $269.78 | $271.19 | time exit (10 days) | 10 | +5.26 |
| 44 | JNJ | $275.21 | $270.22 | time exit (10 days) | 10 | -18.25 |
| 45 | JNJ | $257.78 | $280.99 | take-profit | 7 | +90.47 |
| 46 | BTC-USD | $64,880.19 | $64,506.25 | time exit (10 days) | 10 | -5.83 |
| 47 | BTC-USD | $64,680.71 | $70,501.98 | take-profit | 2 | +90.81 |
| 48 | BTC-USD | $81,271.74 | $76,395.44 | stop-loss | 8 | -60.95 |
| 49 | BTC-USD | $86,602.91 | $84,853.10 | time exit (10 days) | 10 | -20.47 |
| 50 | ETH-USD | $2,251.46 | $2,454.10 | take-profit | 2 | +91.27 |
| 51 | ETH-USD | $2,643.00 | $2,683.68 | time exit (10 days) | 10 | +15.75 |

### Stress FRESH-4 — RSI mean-reversion (buy RSI < 30, sell RSI > 70) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $137.73 | $146.59 | time exit (10 days) | 10 | +64.34 |
| 2 | AAPL | $129.98 | $122.18 | stop-loss | 8 | -60.39 |
| 3 | AAPL | $123.83 | $131.07 | time exit (10 days) | 10 | +58.49 |
| 4 | AAPL | $122.83 | $133.88 | take-profit | 7 | +90.54 |
| 5 | MSFT | $236.64 | $232.98 | time exit (10 days) | 10 | -15.69 |
| 6 | MSFT | $215.75 | $235.17 | take-profit | 8 | +91.25 |
| 7 | NVDA | $13.33 | $12.53 | stop-loss | 3 | -61.67 |
| 8 | NVDA | $14.22 | $15.51 | take-profit | 2 | +92.43 |
| 9 | SPY | $362.96 | $361.86 | time exit (10 days) | 10 | -3.12 |
| 10 | AMZN | $90.53 | $98.68 | take-profit | 3 | +92.33 |
| 11 | AMZN | $98.49 | $92.58 | stop-loss | 4 | -62.10 |
| 12 | AMZN | $88.25 | $96.20 | take-profit | 5 | +92.66 |
| 13 | AMZN | $85.19 | $83.12 | time exit (10 days) | 10 | -25.22 |
| 14 | GOOGL | $88.18 | $85.39 | time exit (10 days) | 10 | -32.77 |
| 15 | GOOGL | $85.21 | $90.27 | time exit (10 days) | 10 | +61.30 |
| 16 | GOOGL | $85.39 | $93.08 | take-profit | 10 | +93.53 |
| 17 | META | $135.08 | $132.52 | time exit (10 days) | 10 | -19.83 |
| 18 | META | $92.28 | $100.59 | take-profit | 7 | +94.21 |
| 19 | META | $95.80 | $104.44 | take-profit | 3 | +95.12 |
| 20 | TSLA | $242.40 | $227.86 | stop-loss | 4 | -63.85 |
| 21 | TSLA | $222.96 | $209.58 | stop-loss | 3 | -63.50 |
| 22 | TSLA | $219.35 | $206.19 | stop-loss | 3 | -63.10 |
| 23 | TSLA | $167.87 | $182.98 | take-profit | 2 | +94.11 |
| 24 | TSLA | $137.80 | $129.53 | stop-loss | 2 | -63.31 |
| 25 | TSLA | $112.71 | $122.85 | take-profit | 1 | +94.33 |
| 26 | TSLA | $110.34 | $103.72 | stop-loss | 1 | -63.48 |
| 27 | JPM | $119.08 | $124.24 | time exit (10 days) | 10 | +45.53 |
| 28 | JNJ | $151.59 | $147.88 | time exit (10 days) | 10 | -25.86 |
| 29 | JNJ | $151.13 | $145.67 | time exit (10 days) | 10 | -38.09 |
| 30 | JNJ | $147.88 | $145.13 | time exit (10 days) | 10 | -19.53 |
| 31 | BTC-USD | $15,787.28 | $16,967.13 | time exit (10 days) | 10 | +78.22 |
| 32 | ETH-USD | $1,108.35 | $1,208.11 | take-profit | 3 | +95.01 |

### Stress FRESH-4 — Bollinger mean-reversion (buy lower band, sell upper band) — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | MSFT | $215.75 | $235.17 | take-profit | 8 | +90.01 |
| 2 | NVDA | $11.63 | $10.93 | stop-loss | 3 | -60.58 |
| 3 | NVDA | $13.99 | $15.25 | take-profit | 7 | +90.39 |
| 4 | SPY | $345.90 | $341.82 | time exit (10 days) | 10 | -11.93 |
| 5 | AMZN | $102.44 | $96.29 | stop-loss | 1 | -60.68 |
| 6 | META | $92.28 | $100.59 | take-profit | 7 | +90.52 |
| 7 | TSLA | $242.40 | $227.86 | stop-loss | 4 | -60.81 |
| 8 | TSLA | $197.08 | $185.26 | stop-loss | 2 | -60.44 |
| 9 | TSLA | $160.95 | $151.29 | stop-loss | 3 | -60.12 |
| 10 | TSLA | $137.80 | $129.53 | stop-loss | 2 | -59.75 |
| 11 | JPM | $96.44 | $95.67 | time exit (10 days) | 10 | -7.94 |
| 12 | JNJ | $151.59 | $147.88 | time exit (10 days) | 10 | -24.21 |
| 13 | BTC-USD | $21,819.04 | $23,782.75 | take-profit | 6 | +88.76 |
| 14 | ETH-USD | $1,168.26 | $1,226.97 | time exit (10 days) | 10 | +50.02 |

