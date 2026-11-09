# VaultTec — Phase 6 Win-Rate Test Report

Generated: 2026-11-09T16:08:49.646125 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests entry rules on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Three new wide-6 variants (6% stop / 9% target, 1.5:1, 10-day exit) on OOS-1/2/3 + FRESH-1/2/3/4, delayed real yfinance history from the disk cache (no Yahoo re-fetch), 12 symbols, walk-forward, signals from history up to the trade day only — no look-ahead. Every trade goes through the real PaperTradingEngine and Risk Engine, balanced profile, $10,000 virtual cash, long-only. (1) High-confidence-only: RSI + Bollinger wide-6 only when the explainable signal is long with confidence >= 0.70 (app scanner floor is 0.55). (2) Volume confirmation: same entries only when the entry bar's volume is above its 20-day average (ratio > 1.0). (3) Combined: mean-reversion wide-6 (RSI + Bollinger, 5-day grid) PLUS MACD trend-following (every bar) in one shared $10,000 portfolio, at most one trade per symbol per day. The wide-6 baseline is re-run on the same windows so the comparison is like-for-like. Every variant keeps a stop-loss; the stop is never removed.
- Data: yfinance (delayed real market data, free — Yahoo Finance), from data/fresh-cache/
- Verdict rule: Worth keeping = pooled fresh P&L > $0 AND pooled fresh win rate > 40% AND positive in at least 2 fresh windows AND pooled OOS P&L > $0. The same pool rule is also reported for the OOS pool on its own.

## Variants tested (all wide-6: 6% stop / 9% target, 10-day exit)

- **rsi_wide6** — RSI wide-6 (baseline, re-run).
- **rsi_highconf** — RSI wide-6, confidence >= 0.70 only.
- **rsi_volume** — RSI wide-6, volume > 20-day average only.
- **bollinger_wide6** — Bollinger wide-6 (baseline, re-run).
- **bollinger_highconf** — Bollinger wide-6, confidence >= 0.70 only.
- **bollinger_volume** — Bollinger wide-6, volume > 20-day average only.
- **combined** — Combined — MR wide-6 (RSI + Bollinger) + MACD trend, one portfolio.

## Verdict — pooled fresh (FRESH-1/2/3/4)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Worth keeping |
|---|---:|---:|---:|---:|:---:|:---:|
| rsi_wide6 | 105 | 58.1% | $1,878.13 | $17.89 | 4/4 | YES |
| rsi_highconf | 1 | 100.0% | $27.97 | $27.97 | 1/4 | no |
| rsi_volume | 49 | 55.1% | $877.43 | $17.91 | 4/4 | YES |
| bollinger_wide6 | 50 | 56.0% | $1,046.71 | $20.93 | 4/4 | YES |
| bollinger_highconf | 5 | 80.0% | $244.01 | $48.80 | 3/4 | YES |
| bollinger_volume | 46 | 54.3% | $883.47 | $19.21 | 3/4 | YES |
| combined | 354 | 57.9% | $5,575.29 | $15.75 | 4/4 | YES |

## Verdict — pooled out-of-sample (OOS-1/2/3)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Pool passes |
|---|---:|---:|---:|---:|:---:|:---:|
| rsi_wide6 | 67 | 59.7% | $1,441.19 | $21.51 | 3/3 | yes |
| rsi_highconf | 1 | 100.0% | $47.81 | $47.81 | 1/3 | no |
| rsi_volume | 47 | 51.1% | $572.56 | $12.18 | 2/3 | yes |
| bollinger_wide6 | 40 | 65.0% | $880.48 | $22.01 | 3/3 | yes |
| bollinger_highconf | 1 | 100.0% | $29.33 | $29.33 | 1/3 | no |
| bollinger_volume | 38 | 63.2% | $800.78 | $21.07 | 3/3 | yes |
| combined | 280 | 54.6% | $3,190.39 | $11.39 | 3/3 | yes |

## Combined vs its legs (same pool, like-for-like)

### OOS pool

- Combined: 280 trades, 54.6% win, P&L $3,190.39 (expectancy $11.39/trade).
- RSI wide-6 alone: $1,441.19; Bollinger wide-6 alone: $880.48.
- Combined beats both legs on P&L: **yes** (beats RSI: yes; beats Bollinger: yes).
- MACD trend alone (Phase 5, quoted, same windows): oos pooled $1,432.96 — the combined run is NOT the sum of the two legs run on separate $10,000 pots; it is one shared pot, so same-day skips and shared cash cost it some trades.

### FRESH pool

- Combined: 354 trades, 57.9% win, P&L $5,575.29 (expectancy $15.75/trade).
- RSI wide-6 alone: $1,878.13; Bollinger wide-6 alone: $1,046.71.
- Combined beats both legs on P&L: **yes** (beats RSI: yes; beats Bollinger: yes).
- MACD trend alone (Phase 5, quoted, same windows): fresh pooled $2,899.45 — the combined run is NOT the sum of the two legs run on separate $10,000 pots; it is one shared pot, so same-day skips and shared cash cost it some trades.

⚠️ **Small-sample warning:** the high-confidence variants pass the verdict rule on paper but on almost no trades — RSI high-confidence took 1 fresh trade (of 105 RSI signals) and 1 out-of-sample trade; Bollinger high-confidence took 5 fresh trades and 1 out-of-sample trade. A 100% / 80% win rate on 1–6 trades proves nothing. Do NOT adopt the high-confidence gate on this evidence. At a mean-reversion entry the trend/EMA/MACD checks are usually bearish, so four bullish checks almost never agree — the gate is effectively a 'don't trade' filter for this entry, not a pickier entry.

## Reading it honestly

Nothing here proves future profits: past performance does not guarantee future results. Three new variants were tested on the same seven windows the lead was picked on, so the best-looking one is partly the best by chance (multiple comparisons) — a variant that only looks good here needs a fresh window and live paper trades over real days before it is trusted. Combined trade counts are not directly comparable with single-strategy counts (MACD is checked every bar, mean-reversion on a 5-day grid) — P&L, win rate and expectancy per trade are the comparison. Live paper evidence is still Day 1 only (2026-11-09: 3 trades open, 0 closed, $0 realised) and proves nothing yet. A compliance/legal review is still required before any real money is considered.

## OOS-1 — 2025-08-27 → 2026-02-23 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 25 | 25 | 0 | 56.0% | $304.61 | $12.18 | $66.23 | $-56.61 | -2.14% | 0 |
| rsi_highconf | 1 | 25 | 24 | 100.0% | $47.81 | $47.81 | $47.81 | $0.00 | 0.00% | 0 |
| rsi_volume | 16 | 25 | 9 | 43.8% | $-58.28 | $-3.64 | $68.93 | $-60.09 | -2.09% | 0 |
| bollinger_wide6 | 15 | 15 | 0 | 60.0% | $105.22 | $7.01 | $49.13 | $-56.16 | -1.55% | 0 |
| bollinger_highconf | 0 | 15 | 15 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| bollinger_volume | 14 | 15 | 1 | 57.1% | $95.75 | $6.84 | $54.08 | $-56.15 | -1.55% | 0 |
| combined | 98 | 102 | 0 | 54.1% | $1,028.26 | $10.49 | $58.52 | $-46.08 | -5.82% | 0 |

- rsi_wide6 per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- rsi_highconf per symbol: {'GOOGL': 1}
- rsi_volume per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'META': 2, 'JNJ': 1, 'BTC-USD': 4, 'ETH-USD': 3}
- bollinger_wide6 per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- bollinger_highconf per symbol: {}
- bollinger_volume per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- combined per symbol: {'AAPL': 8, 'MSFT': 9, 'NVDA': 7, 'SPY': 10, 'AMZN': 7, 'GOOGL': 6, 'META': 10, 'TSLA': 5, 'JPM': 6, 'JNJ': 6, 'BTC-USD': 13, 'ETH-USD': 11}

## OOS-2 — 2025-02-28 → 2025-08-27 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 21 | 21 | 0 | 42.9% | $63.26 | $3.01 | $73.18 | $-49.61 | -3.39% | 0 |
| rsi_highconf | 0 | 21 | 21 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| rsi_volume | 20 | 21 | 1 | 45.0% | $123.49 | $6.17 | $73.36 | $-48.79 | -2.81% | 0 |
| bollinger_wide6 | 13 | 13 | 0 | 69.2% | $482.00 | $37.08 | $80.48 | $-60.59 | -0.60% | 0 |
| bollinger_highconf | 0 | 13 | 13 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| bollinger_volume | 12 | 13 | 1 | 66.7% | $411.77 | $34.31 | $81.76 | $-60.59 | -0.60% | 0 |
| combined | 95 | 102 | 0 | 49.5% | $354.60 | $3.73 | $57.51 | $-48.93 | -5.94% | 0 |

- rsi_wide6 per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- rsi_highconf per symbol: {}
- rsi_volume per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 2, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- bollinger_wide6 per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- bollinger_highconf per symbol: {}
- bollinger_volume per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- combined per symbol: {'AAPL': 9, 'MSFT': 6, 'NVDA': 6, 'SPY': 7, 'AMZN': 11, 'GOOGL': 10, 'META': 7, 'TSLA': 9, 'JPM': 7, 'JNJ': 4, 'BTC-USD': 11, 'ETH-USD': 8}

## OOS-3 — 2024-09-01 → 2025-02-28 (out-of-sample)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 21 | 21 | 0 | 81.0% | $1,073.32 | $51.11 | $69.03 | $-25.04 | -0.60% | 0 |
| rsi_highconf | 0 | 21 | 21 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| rsi_volume | 11 | 21 | 10 | 72.7% | $507.35 | $46.12 | $72.57 | $-24.40 | -0.60% | 0 |
| bollinger_wide6 | 12 | 12 | 0 | 66.7% | $293.26 | $24.44 | $60.31 | $-47.30 | -1.07% | 0 |
| bollinger_highconf | 1 | 12 | 11 | 100.0% | $29.33 | $29.33 | $29.33 | $0.00 | 0.00% | 0 |
| bollinger_volume | 12 | 12 | 0 | 66.7% | $293.26 | $24.44 | $60.31 | $-47.30 | -1.07% | 0 |
| combined | 87 | 94 | 0 | 60.9% | $1,807.53 | $20.78 | $64.31 | $-47.08 | -2.96% | 0 |

- rsi_wide6 per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- rsi_highconf per symbol: {}
- rsi_volume per symbol: {'AAPL': 3, 'GOOGL': 1, 'TSLA': 1, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 1, 'ETH-USD': 1}
- bollinger_wide6 per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- bollinger_highconf per symbol: {'JPM': 1}
- bollinger_volume per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- combined per symbol: {'AAPL': 7, 'MSFT': 7, 'NVDA': 5, 'SPY': 6, 'AMZN': 5, 'GOOGL': 8, 'META': 5, 'TSLA': 5, 'JPM': 5, 'JNJ': 8, 'BTC-USD': 9, 'ETH-USD': 17}

## FRESH-1 — 2024-03-04 → 2024-09-01 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 27 | 27 | 0 | 59.3% | $298.22 | $11.05 | $55.55 | $-53.69 | -1.75% | 0 |
| rsi_highconf | 0 | 27 | 27 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| rsi_volume | 14 | 27 | 13 | 50.0% | $75.90 | $5.42 | $60.55 | $-49.71 | -1.65% | 0 |
| bollinger_wide6 | 18 | 18 | 0 | 66.7% | $499.89 | $27.77 | $62.79 | $-42.27 | -1.20% | 0 |
| bollinger_highconf | 3 | 18 | 15 | 66.7% | $104.45 | $34.82 | $82.28 | $-60.12 | -0.60% | 0 |
| bollinger_volume | 16 | 18 | 2 | 62.5% | $399.76 | $24.98 | $65.34 | $-42.27 | -1.20% | 0 |
| combined | 94 | 104 | 0 | 61.7% | $1,781.37 | $18.95 | $58.03 | $-44.02 | -2.75% | 0 |

- rsi_wide6 per symbol: {'AAPL': 2, 'MSFT': 4, 'AMZN': 3, 'GOOGL': 4, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 3, 'ETH-USD': 3}
- rsi_highconf per symbol: {}
- rsi_volume per symbol: {'AAPL': 2, 'MSFT': 3, 'AMZN': 1, 'GOOGL': 3, 'TSLA': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- bollinger_wide6 per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 3, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 4}
- bollinger_highconf per symbol: {'JPM': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- bollinger_volume per symbol: {'AAPL': 1, 'MSFT': 1, 'SPY': 2, 'AMZN': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 3, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 3}
- combined per symbol: {'AAPL': 9, 'MSFT': 8, 'NVDA': 3, 'SPY': 10, 'AMZN': 8, 'GOOGL': 8, 'META': 6, 'TSLA': 6, 'JPM': 7, 'JNJ': 9, 'BTC-USD': 9, 'ETH-USD': 11}

## FRESH-2 — 2023-09-06 → 2024-03-04 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 22 | 22 | 0 | 63.6% | $296.06 | $13.46 | $44.12 | $-40.20 | -1.79% | 0 |
| rsi_highconf | 1 | 22 | 21 | 100.0% | $27.97 | $27.97 | $27.97 | $0.00 | 0.00% | 0 |
| rsi_volume | 9 | 22 | 13 | 66.7% | $143.25 | $15.92 | $49.23 | $-50.71 | -1.20% | 0 |
| bollinger_wide6 | 5 | 5 | 0 | 60.0% | $128.53 | $25.71 | $53.77 | $-16.39 | -0.32% | 0 |
| bollinger_highconf | 1 | 5 | 4 | 100.0% | $49.62 | $49.62 | $49.62 | $0.00 | 0.00% | 0 |
| bollinger_volume | 5 | 5 | 0 | 60.0% | $128.53 | $25.71 | $53.77 | $-16.39 | -0.32% | 0 |
| combined | 83 | 83 | 0 | 55.4% | $1,194.06 | $14.39 | $55.42 | $-36.63 | -2.78% | 0 |

- rsi_wide6 per symbol: {'AAPL': 3, 'NVDA': 2, 'SPY': 2, 'AMZN': 1, 'TSLA': 6, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 1, 'ETH-USD': 1}
- rsi_highconf per symbol: {'ETH-USD': 1}
- rsi_volume per symbol: {'AAPL': 2, 'SPY': 2, 'TSLA': 4, 'JNJ': 1}
- bollinger_wide6 per symbol: {'AMZN': 1, 'GOOGL': 1, 'JNJ': 2, 'ETH-USD': 1}
- bollinger_highconf per symbol: {'GOOGL': 1}
- bollinger_volume per symbol: {'AMZN': 1, 'GOOGL': 1, 'JNJ': 2, 'ETH-USD': 1}
- combined per symbol: {'AAPL': 8, 'MSFT': 3, 'NVDA': 6, 'SPY': 6, 'AMZN': 8, 'GOOGL': 5, 'META': 4, 'TSLA': 10, 'JPM': 7, 'JNJ': 11, 'BTC-USD': 6, 'ETH-USD': 9}

## FRESH-3 — 2023-03-10 → 2023-09-06 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 24 | 24 | 0 | 62.5% | $631.96 | $26.33 | $54.64 | $-20.84 | -0.60% | 0 |
| rsi_highconf | 0 | 24 | 24 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| rsi_volume | 14 | 24 | 10 | 57.1% | $387.62 | $27.69 | $64.59 | $-21.52 | -0.60% | 0 |
| bollinger_wide6 | 13 | 13 | 0 | 61.5% | $415.05 | $31.93 | $69.71 | $-28.53 | -0.60% | 0 |
| bollinger_highconf | 0 | 13 | 13 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| bollinger_volume | 12 | 13 | 1 | 66.7% | $441.29 | $36.77 | $69.76 | $-29.20 | -0.60% | 0 |
| combined | 85 | 96 | 0 | 68.2% | $1,883.14 | $22.15 | $52.75 | $-43.58 | -1.79% | 0 |

- rsi_wide6 per symbol: {'AAPL': 2, 'MSFT': 1, 'SPY': 2, 'META': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 5, 'BTC-USD': 5, 'ETH-USD': 4}
- rsi_highconf per symbol: {}
- rsi_volume per symbol: {'AAPL': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 3, 'ETH-USD': 3}
- bollinger_wide6 per symbol: {'NVDA': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 2, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 2}
- bollinger_highconf per symbol: {}
- bollinger_volume per symbol: {'NVDA': 1, 'SPY': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 2, 'ETH-USD': 2}
- combined per symbol: {'AAPL': 8, 'MSFT': 8, 'NVDA': 6, 'SPY': 7, 'AMZN': 6, 'GOOGL': 4, 'META': 7, 'TSLA': 6, 'JPM': 6, 'JNJ': 7, 'BTC-USD': 11, 'ETH-USD': 9}

## FRESH-4 — 2022-09-12 → 2023-03-10 (fresh — never used for selection)

- History: 12 symbols fetched; failed: none

| Variant | Trades | Signals seen | Skipped by gate | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 32 | 32 | 0 | 50.0% | $651.89 | $20.37 | $83.34 | $-42.59 | -1.79% | 0 |
| rsi_highconf | 0 | 32 | 32 | 0.0% | $0.00 | $0.00 | $0.00 | $0.00 | 0.00% | 0 |
| rsi_volume | 12 | 32 | 20 | 50.0% | $270.66 | $22.56 | $85.90 | $-40.79 | -1.20% | 0 |
| bollinger_wide6 | 14 | 14 | 0 | 35.7% | $3.24 | $0.23 | $81.94 | $-45.16 | -2.70% | 0 |
| bollinger_highconf | 1 | 14 | 13 | 100.0% | $89.94 | $89.94 | $89.94 | $0.00 | 0.00% | 0 |
| bollinger_volume | 13 | 14 | 1 | 30.8% | $-86.11 | $-6.62 | $79.31 | $-44.82 | -3.11% | 0 |
| combined | 92 | 98 | 0 | 46.7% | $716.72 | $7.79 | $67.07 | $-44.23 | -4.42% | 0 |

- rsi_wide6 per symbol: {'AAPL': 4, 'MSFT': 2, 'NVDA': 2, 'SPY': 1, 'AMZN': 4, 'GOOGL': 3, 'META': 3, 'TSLA': 7, 'JPM': 1, 'JNJ': 3, 'BTC-USD': 1, 'ETH-USD': 1}
- rsi_highconf per symbol: {}
- rsi_volume per symbol: {'AAPL': 1, 'MSFT': 2, 'META': 3, 'TSLA': 5, 'JNJ': 1}
- bollinger_wide6 per symbol: {'MSFT': 1, 'NVDA': 2, 'SPY': 1, 'AMZN': 1, 'META': 1, 'TSLA': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- bollinger_highconf per symbol: {'BTC-USD': 1}
- bollinger_volume per symbol: {'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 1, 'TSLA': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 1, 'ETH-USD': 1}
- combined per symbol: {'AAPL': 7, 'MSFT': 7, 'NVDA': 8, 'SPY': 5, 'AMZN': 8, 'GOOGL': 6, 'META': 7, 'TSLA': 13, 'JPM': 8, 'JNJ': 7, 'BTC-USD': 9, 'ETH-USD': 7}

## What this does and does not prove

Nothing here proves future profits: past performance does not guarantee future results. Three new variants were tested on the same seven windows the lead was picked on, so the best-looking one is partly the best by chance (multiple comparisons) — a variant that only looks good here needs a fresh window and live paper trades over real days before it is trusted. Combined trade counts are not directly comparable with single-strategy counts (MACD is checked every bar, mean-reversion on a 5-day grid) — P&L, win rate and expectancy per trade are the comparison. Live paper evidence is still Day 1 only (2026-11-09: 3 trades open, 0 closed, $0 realised) and proves nothing yet. A compliance/legal review is still required before any real money is considered.

## Trades (every trade, in order) — high-confidence, volume and combined variants

Trade-by-trade rows for the three new variants. Every trade for every variant, including the re-run baselines, is in the JSON report.

### OOS-1 — rsi_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | GOOGL | rsi_highconf | $240.90 | $252.42 | time exit (10 days) | 10 | +47.81 |

### OOS-1 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $261.65 | $245.95 | stop-loss | 9 | -60.00 |
| 2 | AAPL | rsi_volume | $260.34 | $244.72 | stop-loss | 4 | -59.64 |
| 3 | AAPL | rsi_volume | $246.98 | $269.21 | take-profit | 8 | +88.94 |
| 4 | MSFT | rsi_volume | $475.41 | $480.11 | time exit (10 days) | 10 | +9.85 |
| 5 | MSFT | rsi_volume | $441.31 | $414.83 | stop-loss | 9 | -59.88 |
| 6 | SPY | rsi_volume | $645.57 | $678.37 | time exit (10 days) | 10 | +50.40 |
| 7 | META | rsi_volume | $616.85 | $579.84 | stop-loss | 9 | -59.81 |
| 8 | META | rsi_volume | $611.39 | $666.42 | take-profit | 3 | +89.20 |
| 9 | JNJ | rsi_volume | $201.55 | $214.56 | time exit (10 days) | 10 | +64.55 |
| 10 | BTC-USD | rsi_volume | $109,712.83 | $119,586.99 | take-profit | 6 | +89.85 |
| 11 | BTC-USD | rsi_volume | $86,631.90 | $81,433.98 | stop-loss | 1 | -60.82 |
| 12 | BTC-USD | rsi_volume | $84,561.59 | $79,487.89 | stop-loss | 2 | -60.38 |
| 13 | BTC-USD | rsi_volume | $75,633.55 | $71,095.53 | stop-loss | 2 | -59.90 |
| 14 | ETH-USD | rsi_volume | $4,035.89 | $4,399.13 | take-profit | 6 | +89.72 |
| 15 | ETH-USD | rsi_volume | $2,818.23 | $2,649.14 | stop-loss | 1 | -60.37 |
| 16 | ETH-USD | rsi_volume | $2,227.56 | $2,093.91 | stop-loss | 1 | -59.99 |

### OOS-1 — bollinger_highconf: no trades

### OOS-1 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | bollinger_volume | $261.65 | $245.95 | stop-loss | 9 | -60.00 |
| 2 | MSFT | bollinger_volume | $493.04 | $475.41 | time exit (10 days) | 10 | -35.55 |
| 3 | MSFT | bollinger_volume | $441.31 | $414.83 | stop-loss | 9 | -59.43 |
| 4 | NVDA | bollinger_volume | $173.78 | $189.42 | take-profit | 3 | +88.58 |
| 5 | SPY | bollinger_volume | $645.57 | $678.37 | time exit (10 days) | 10 | +50.48 |
| 6 | AMZN | bollinger_volume | $218.15 | $227.74 | time exit (10 days) | 10 | +43.89 |
| 7 | META | bollinger_volume | $664.22 | $624.36 | stop-loss | 3 | -60.17 |
| 8 | META | bollinger_volume | $629.47 | $667.01 | time exit (10 days) | 10 | +59.45 |
| 9 | TSLA | bollinger_volume | $401.99 | $430.17 | time exit (10 days) | 10 | +70.29 |
| 10 | TSLA | bollinger_volume | $406.01 | $411.71 | time exit (10 days) | 10 | +14.18 |
| 11 | JPM | bollinger_volume | $292.90 | $303.59 | time exit (10 days) | 10 | +36.91 |
| 12 | JNJ | bollinger_volume | $170.32 | $181.88 | time exit (10 days) | 10 | +68.87 |
| 13 | BTC-USD | bollinger_volume | $86,631.90 | $81,433.98 | stop-loss | 1 | -60.82 |
| 14 | ETH-USD | bollinger_volume | $3,425.17 | $3,219.66 | stop-loss | 2 | -60.93 |

### OOS-1 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | macd | $237.59 | $238.11 | time exit (10 days) | 10 | +2.18 |
| 2 | AAPL | macd | $244.60 | $257.07 | time exit (10 days) | 10 | +51.01 |
| 3 | AAPL | macd | $258.62 | $268.78 | time exit (10 days) | 10 | +39.47 |
| 4 | AAPL | macd | $278.09 | $277.52 | time exit (10 days) | 10 | -2.08 |
| 5 | AAPL | rsi | $261.65 | $245.95 | stop-loss | 9 | -60.54 |
| 6 | AAPL | rsi | $260.34 | $244.72 | stop-loss | 4 | -60.18 |
| 7 | AAPL | rsi | $246.98 | $269.21 | take-profit | 8 | +89.74 |
| 8 | AAPL | macd | $255.74 | $278.76 | take-profit | 7 | +90.53 |
| 9 | MSFT | macd | $511.15 | $510.40 | time exit (10 days) | 10 | -1.50 |
| 10 | MSFT | macd | $516.31 | $493.04 | time exit (10 days) | 10 | -45.74 |
| 11 | MSFT | bollinger | $493.04 | $475.41 | time exit (10 days) | 10 | -36.13 |
| 12 | MSFT | rsi | $475.41 | $480.11 | time exit (10 days) | 10 | +9.94 |
| 13 | MSFT | macd | $486.91 | $473.39 | time exit (10 days) | 10 | -27.98 |
| 14 | MSFT | macd | $480.11 | $482.86 | time exit (10 days) | 10 | +5.75 |
| 15 | MSFT | macd | $480.42 | $451.60 | stop-loss | 8 | -60.32 |
| 16 | MSFT | rsi | $441.31 | $414.83 | stop-loss | 9 | -59.97 |
| 17 | MSFT | macd | $477.55 | $448.90 | stop-loss | 2 | -59.60 |
| 18 | NVDA | macd | $177.33 | $181.42 | time exit (10 days) | 10 | +22.80 |
| 19 | NVDA | macd | $176.25 | $187.17 | time exit (10 days) | 10 | +61.34 |
| 20 | NVDA | macd | $191.03 | $208.23 | take-profit | 2 | +89.65 |
| 21 | NVDA | macd | $185.12 | $174.01 | stop-loss | 7 | -60.29 |
| 22 | NVDA | macd | $183.26 | $188.67 | time exit (10 days) | 10 | +29.48 |
| 23 | NVDA | macd | $188.08 | $176.80 | stop-loss | 5 | -60.08 |
| 24 | NVDA | bollinger | $173.78 | $189.42 | take-profit | 3 | +89.59 |
| 25 | SPY | macd | $640.22 | $648.59 | time exit (10 days) | 10 | +13.14 |
| 26 | SPY | macd | $643.46 | $654.04 | time exit (10 days) | 10 | +16.53 |
| 27 | SPY | macd | $661.32 | $658.07 | time exit (10 days) | 10 | -4.94 |
| 28 | SPY | macd | $670.02 | $663.81 | time exit (10 days) | 10 | -9.34 |
| 29 | SPY | rsi | $645.57 | $678.37 | time exit (10 days) | 10 | +51.13 |
| 30 | SPY | macd | $676.10 | $674.48 | time exit (10 days) | 10 | -2.42 |
| 31 | SPY | macd | $682.63 | $684.17 | time exit (10 days) | 10 | +2.28 |
| 32 | SPY | macd | $686.45 | $680.09 | time exit (10 days) | 10 | -9.37 |
| 33 | SPY | macd | $690.03 | $686.60 | time exit (10 days) | 10 | -5.02 |
| 34 | SPY | macd | $690.02 | $677.56 | time exit (10 days) | 10 | -18.24 |
| 35 | AMZN | macd | $235.68 | $231.23 | time exit (10 days) | 10 | -19.03 |
| 36 | AMZN | bollinger | $218.15 | $227.74 | time exit (10 days) | 10 | +44.23 |
| 37 | AMZN | macd | $227.74 | $214.08 | stop-loss | 3 | -60.62 |
| 38 | AMZN | macd | $217.95 | $237.57 | take-profit | 7 | +90.43 |
| 39 | AMZN | rsi | $217.14 | $236.69 | take-profit | 7 | +91.26 |
| 40 | AMZN | macd | $232.14 | $246.29 | time exit (10 days) | 10 | +62.34 |
| 41 | AMZN | macd | $244.68 | $230.00 | stop-loss | 7 | -61.73 |
| 42 | GOOGL | macd | $206.76 | $225.37 | take-profit | 4 | +92.07 |
| 43 | GOOGL | rsi | $240.90 | $252.42 | time exit (10 days) | 10 | +49.33 |
| 44 | GOOGL | macd | $259.25 | $282.58 | take-profit | 4 | +93.33 |
| 45 | GOOGL | macd | $298.88 | $325.79 | take-profit | 2 | +94.19 |
| 46 | GOOGL | macd | $324.81 | $327.29 | time exit (10 days) | 10 | +8.07 |
| 47 | GOOGL | macd | $337.59 | $317.34 | stop-loss | 5 | -63.38 |
| 48 | META | macd | $761.60 | $740.89 | time exit (10 days) | 10 | -28.56 |
| 49 | META | macd | $729.69 | $685.91 | stop-loss | 8 | -62.84 |
| 50 | META | bollinger | $664.22 | $624.36 | stop-loss | 3 | -62.46 |
| 51 | META | rsi | $616.85 | $579.84 | stop-loss | 9 | -62.08 |
| 52 | META | rsi | $607.83 | $645.76 | time exit (10 days) | 10 | +64.18 |
| 53 | META | rsi | $587.16 | $640.01 | take-profit | 5 | +93.16 |
| 54 | META | macd | $610.98 | $665.97 | take-profit | 7 | +93.99 |
| 55 | META | bollinger | $629.47 | $667.01 | time exit (10 days) | 10 | +62.84 |
| 56 | META | rsi | $611.39 | $666.42 | take-profit | 3 | +95.41 |
| 57 | META | macd | $657.07 | $716.22 | take-profit | 4 | +96.28 |
| 58 | TSLA | macd | $350.84 | $382.42 | take-profit | 5 | +97.13 |
| 59 | TSLA | macd | $468.37 | $440.27 | stop-loss | 3 | -65.32 |
| 60 | TSLA | bollinger | $401.99 | $430.17 | time exit (10 days) | 10 | +75.87 |
| 61 | TSLA | macd | $430.17 | $458.96 | time exit (10 days) | 10 | +72.94 |
| 62 | TSLA | bollinger | $406.01 | $411.71 | time exit (10 days) | 10 | +15.40 |
| 63 | JPM | macd | $298.34 | $306.04 | time exit (10 days) | 10 | +28.37 |
| 64 | JPM | bollinger | $292.90 | $303.59 | time exit (10 days) | 10 | +40.21 |
| 65 | JPM | macd | $299.74 | $314.36 | time exit (10 days) | 10 | +53.94 |
| 66 | JPM | macd | $307.16 | $312.50 | time exit (10 days) | 10 | +19.30 |
| 67 | JPM | rsi | $296.42 | $306.32 | time exit (10 days) | 10 | +37.18 |
| 68 | JPM | macd | $310.29 | $304.31 | time exit (10 days) | 10 | -21.53 |
| 69 | JNJ | bollinger | $170.32 | $181.88 | time exit (10 days) | 10 | +75.63 |
| 70 | JNJ | macd | $177.62 | $186.69 | time exit (10 days) | 10 | +57.31 |
| 71 | JNJ | macd | $190.11 | $204.27 | time exit (10 days) | 10 | +84.03 |
| 72 | JNJ | macd | $208.23 | $204.27 | time exit (10 days) | 10 | -21.61 |
| 73 | JNJ | rsi | $201.55 | $214.56 | time exit (10 days) | 10 | +73.21 |
| 74 | JNJ | macd | $210.27 | $224.12 | time exit (10 days) | 10 | +75.19 |
| 75 | BTC-USD | rsi | $111,222.06 | $110,224.70 | time exit (10 days) | 10 | -10.27 |
| 76 | BTC-USD | macd | $110,224.70 | $116,843.19 | time exit (10 days) | 10 | +68.83 |
| 77 | BTC-USD | rsi | $109,712.83 | $119,586.99 | take-profit | 6 | +103.68 |
| 78 | BTC-USD | macd | $118,648.93 | $111,529.99 | stop-loss | 9 | -69.77 |
| 79 | BTC-USD | macd | $114,472.45 | $107,604.10 | stop-loss | 4 | -69.37 |
| 80 | BTC-USD | rsi | $95,549.15 | $89,816.20 | stop-loss | 3 | -68.80 |
| 81 | BTC-USD | rsi | $86,631.90 | $81,433.98 | stop-loss | 1 | -68.61 |
| 82 | BTC-USD | rsi | $87,341.89 | $89,387.76 | time exit (10 days) | 10 | +26.60 |
| 83 | BTC-USD | macd | $91,285.38 | $85,808.25 | stop-loss | 4 | -67.92 |
| 84 | BTC-USD | bollinger | $86,419.78 | $87,234.74 | time exit (10 days) | 10 | +10.68 |
| 85 | BTC-USD | macd | $88,344.00 | $88,430.13 | time exit (10 days) | 10 | +1.10 |
| 86 | BTC-USD | rsi | $84,561.59 | $79,487.89 | stop-loss | 2 | -67.99 |
| 87 | BTC-USD | rsi | $75,633.55 | $71,095.53 | stop-loss | 2 | -67.62 |
| 88 | ETH-USD | macd | $4,715.25 | $4,432.33 | stop-loss | 4 | -67.25 |
| 89 | ETH-USD | rsi | $4,035.89 | $4,399.13 | take-profit | 6 | +100.25 |
| 90 | ETH-USD | macd | $4,487.92 | $4,218.65 | stop-loss | 8 | -67.43 |
| 91 | ETH-USD | macd | $4,157.99 | $3,908.51 | stop-loss | 3 | -67.04 |
| 92 | ETH-USD | bollinger | $3,425.17 | $3,219.66 | stop-loss | 2 | -66.63 |
| 93 | ETH-USD | macd | $2,957.94 | $2,780.46 | stop-loss | 6 | -66.23 |
| 94 | ETH-USD | macd | $3,006.07 | $3,000.39 | time exit (10 days) | 10 | -2.07 |
| 95 | ETH-USD | rsi | $2,903.58 | $3,140.71 | time exit (10 days) | 10 | +89.61 |
| 96 | ETH-USD | macd | $2,948.00 | $3,213.32 | take-profit | 9 | +99.55 |
| 97 | ETH-USD | rsi | $2,818.23 | $2,649.14 | stop-loss | 1 | -66.96 |
| 98 | ETH-USD | rsi | $2,227.56 | $2,093.91 | stop-loss | 1 | -66.56 |

### OOS-2 — rsi_highconf: no trades

### OOS-2 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $212.18 | $216.57 | time exit (10 days) | 10 | +20.67 |
| 2 | AAPL | rsi_volume | $216.94 | $203.92 | stop-loss | 9 | -60.12 |
| 3 | MSFT | rsi_volume | $355.66 | $387.69 | take-profit | 3 | +89.69 |
| 4 | NVDA | rsi_volume | $112.40 | $105.65 | stop-loss | 1 | -60.32 |
| 5 | NVDA | rsi_volume | $94.07 | $88.43 | stop-loss | 1 | -59.92 |
| 6 | SPY | rsi_volume | $564.82 | $554.78 | time exit (10 days) | 10 | -17.66 |
| 7 | SPY | rsi_volume | $497.04 | $505.50 | time exit (10 days) | 10 | +16.88 |
| 8 | AMZN | rsi_volume | $212.28 | $199.54 | stop-loss | 2 | -59.59 |
| 9 | AMZN | rsi_volume | $199.25 | $196.21 | time exit (10 days) | 10 | -15.06 |
| 10 | GOOGL | rsi_volume | $169.29 | $164.71 | time exit (10 days) | 10 | -26.64 |
| 11 | GOOGL | rsi_volume | $144.92 | $157.97 | take-profit | 3 | +88.52 |
| 12 | META | rsi_volume | $622.09 | $584.77 | stop-loss | 1 | -59.49 |
| 13 | META | rsi_volume | $502.30 | $547.51 | take-profit | 3 | +88.72 |
| 14 | TSLA | rsi_volume | $292.98 | $275.40 | stop-loss | 2 | -59.68 |
| 15 | TSLA | rsi_volume | $262.67 | $246.91 | stop-loss | 1 | -59.31 |
| 16 | JPM | rsi_volume | $233.98 | $219.94 | stop-loss | 2 | -58.95 |
| 17 | JPM | rsi_volume | $224.47 | $244.67 | take-profit | 8 | +87.88 |
| 18 | BTC-USD | rsi_volume | $84,373.01 | $91,966.58 | take-profit | 2 | +88.09 |
| 19 | ETH-USD | rsi_volume | $2,237.91 | $2,439.32 | take-profit | 2 | +89.49 |
| 20 | ETH-USD | rsi_volume | $1,861.15 | $2,028.66 | take-profit | 9 | +90.29 |

### OOS-2 — bollinger_highconf: no trades

### OOS-2 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | bollinger_volume | $187.23 | $175.99 | stop-loss | 1 | -60.02 |
| 2 | MSFT | bollinger_volume | $355.66 | $387.69 | take-profit | 3 | +89.50 |
| 3 | NVDA | bollinger_volume | $94.07 | $88.43 | stop-loss | 1 | -60.16 |
| 4 | SPY | bollinger_volume | $497.04 | $505.50 | time exit (10 days) | 10 | +16.98 |
| 5 | AMZN | bollinger_volume | $171.00 | $186.39 | take-profit | 3 | +89.88 |
| 6 | GOOGL | bollinger_volume | $153.61 | $144.39 | stop-loss | 6 | -60.46 |
| 7 | GOOGL | bollinger_volume | $144.92 | $157.97 | take-profit | 3 | +90.21 |
| 8 | META | bollinger_volume | $502.30 | $547.51 | take-profit | 3 | +90.96 |
| 9 | JPM | bollinger_volume | $204.32 | $222.73 | take-profit | 3 | +91.85 |
| 10 | JNJ | bollinger_volume | $147.51 | $138.66 | stop-loss | 3 | -61.70 |
| 11 | BTC-USD | bollinger_volume | $84,373.01 | $91,966.58 | take-profit | 2 | +91.88 |
| 12 | ETH-USD | bollinger_volume | $2,237.91 | $2,439.32 | take-profit | 2 | +92.85 |

### OOS-2 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi | $212.18 | $216.57 | time exit (10 days) | 10 | +20.67 |
| 2 | AAPL | rsi | $216.94 | $203.92 | stop-loss | 9 | -60.12 |
| 3 | AAPL | macd | $222.38 | $209.04 | stop-loss | 7 | -59.76 |
| 4 | AAPL | bollinger | $187.23 | $175.99 | stop-loss | 1 | -59.43 |
| 5 | AAPL | macd | $200.90 | $188.85 | stop-loss | 3 | -59.05 |
| 6 | AAPL | macd | $209.78 | $197.19 | stop-loss | 9 | -58.69 |
| 7 | AAPL | macd | $202.94 | $200.53 | time exit (10 days) | 10 | -11.54 |
| 8 | AAPL | macd | $200.53 | $209.00 | time exit (10 days) | 10 | +41.02 |
| 9 | AAPL | macd | $218.97 | $224.07 | time exit (10 days) | 10 | +22.71 |
| 10 | MSFT | macd | $384.19 | $371.03 | time exit (10 days) | 10 | -33.49 |
| 11 | MSFT | rsi | $355.66 | $387.69 | take-profit | 3 | +87.72 |
| 12 | MSFT | macd | $376.93 | $354.31 | stop-loss | 6 | -58.98 |
| 13 | MSFT | macd | $382.81 | $417.26 | take-profit | 5 | +87.94 |
| 14 | MSFT | macd | $492.58 | $498.39 | time exit (10 days) | 10 | +11.63 |
| 15 | MSFT | macd | $528.28 | $517.37 | time exit (10 days) | 10 | -20.38 |
| 16 | NVDA | rsi | $112.40 | $105.65 | stop-loss | 1 | -59.12 |
| 17 | NVDA | macd | $119.23 | $112.08 | stop-loss | 8 | -58.71 |
| 18 | NVDA | rsi | $94.07 | $88.43 | stop-loss | 1 | -58.38 |
| 19 | NVDA | macd | $107.30 | $100.86 | stop-loss | 4 | -58.06 |
| 20 | NVDA | macd | $106.16 | $115.73 | take-profit | 9 | +86.66 |
| 21 | NVDA | macd | $153.93 | $163.70 | time exit (10 days) | 10 | +61.57 |
| 22 | SPY | rsi | $564.82 | $554.78 | time exit (10 days) | 10 | -17.36 |
| 23 | SPY | macd | $554.78 | $521.49 | stop-loss | 10 | -58.48 |
| 24 | SPY | rsi | $497.04 | $505.50 | time exit (10 days) | 10 | +16.50 |
| 25 | SPY | macd | $528.84 | $545.49 | time exit (10 days) | 10 | +30.56 |
| 26 | SPY | macd | $518.65 | $549.68 | time exit (10 days) | 10 | +58.25 |
| 27 | SPY | macd | $603.67 | $615.26 | time exit (10 days) | 10 | +18.81 |
| 28 | SPY | macd | $628.56 | $628.64 | time exit (10 days) | 10 | +0.13 |
| 29 | AMZN | rsi | $212.28 | $199.54 | stop-loss | 2 | -58.89 |
| 30 | AMZN | rsi | $199.25 | $196.21 | time exit (10 days) | 10 | -14.88 |
| 31 | AMZN | macd | $196.21 | $184.44 | stop-loss | 6 | -58.42 |
| 32 | AMZN | bollinger | $171.00 | $186.39 | take-profit | 3 | +87.12 |
| 33 | AMZN | macd | $184.87 | $173.78 | stop-loss | 3 | -58.59 |
| 34 | AMZN | macd | $180.60 | $188.71 | time exit (10 days) | 10 | +43.60 |
| 35 | AMZN | macd | $213.57 | $208.47 | time exit (10 days) | 10 | -23.29 |
| 36 | AMZN | macd | $223.30 | $225.69 | time exit (10 days) | 10 | +10.41 |
| 37 | AMZN | macd | $229.30 | $215.54 | stop-loss | 9 | -58.45 |
| 38 | AMZN | macd | $232.23 | $218.30 | stop-loss | 6 | -58.07 |
| 39 | AMZN | macd | $234.11 | $220.06 | stop-loss | 1 | -57.75 |
| 40 | GOOGL | rsi | $169.29 | $164.71 | time exit (10 days) | 10 | -25.86 |
| 41 | GOOGL | macd | $162.04 | $152.31 | stop-loss | 7 | -57.26 |
| 42 | GOOGL | bollinger | $153.61 | $144.39 | stop-loss | 6 | -56.89 |
| 43 | GOOGL | rsi | $144.92 | $157.97 | take-profit | 3 | +84.89 |
| 44 | GOOGL | macd | $152.10 | $161.20 | time exit (10 days) | 10 | +56.88 |
| 45 | GOOGL | macd | $157.72 | $171.92 | take-profit | 7 | +86.16 |
| 46 | GOOGL | macd | $172.87 | $162.49 | stop-loss | 10 | -57.94 |
| 47 | GOOGL | macd | $175.23 | $182.33 | time exit (10 days) | 10 | +38.89 |
| 48 | GOOGL | macd | $179.56 | $195.73 | take-profit | 9 | +86.75 |
| 49 | GOOGL | macd | $200.72 | $205.37 | time exit (10 days) | 10 | +22.53 |
| 50 | META | rsi | $622.09 | $584.77 | stop-loss | 1 | -58.45 |
| 51 | META | macd | $623.29 | $585.89 | stop-loss | 3 | -58.12 |
| 52 | META | rsi | $502.30 | $547.51 | take-profit | 3 | +86.65 |
| 53 | META | macd | $530.58 | $578.33 | take-profit | 5 | +87.41 |
| 54 | META | macd | $667.67 | $699.27 | time exit (10 days) | 10 | +46.39 |
| 55 | META | macd | $730.66 | $718.00 | time exit (10 days) | 10 | -17.06 |
| 56 | META | macd | $770.31 | $778.96 | time exit (10 days) | 10 | +11.04 |
| 57 | TSLA | rsi | $292.98 | $275.40 | stop-loss | 2 | -59.05 |
| 58 | TSLA | rsi | $262.67 | $246.91 | stop-loss | 1 | -58.69 |
| 59 | TSLA | rsi | $249.98 | $234.98 | stop-loss | 1 | -58.35 |
| 60 | TSLA | macd | $235.86 | $257.09 | take-profit | 3 | +87.00 |
| 61 | TSLA | macd | $272.20 | $255.87 | stop-loss | 1 | -58.51 |
| 62 | TSLA | macd | $250.74 | $273.31 | take-profit | 2 | +87.26 |
| 63 | TSLA | macd | $340.47 | $320.04 | stop-loss | 3 | -58.69 |
| 64 | TSLA | macd | $321.67 | $302.37 | stop-loss | 6 | -58.33 |
| 65 | TSLA | macd | $322.27 | $320.11 | time exit (10 days) | 10 | -6.48 |
| 66 | JPM | rsi | $233.98 | $219.94 | stop-loss | 2 | -57.94 |
| 67 | JPM | rsi | $224.47 | $244.67 | take-profit | 8 | +86.37 |
| 68 | JPM | macd | $233.35 | $219.35 | stop-loss | 10 | -58.11 |
| 69 | JPM | bollinger | $204.32 | $222.73 | take-profit | 3 | +86.73 |
| 70 | JPM | macd | $229.51 | $236.33 | time exit (10 days) | 10 | +28.87 |
| 71 | JPM | macd | $267.21 | $285.07 | time exit (10 days) | 10 | +65.12 |
| 72 | JPM | macd | $291.56 | $281.93 | time exit (10 days) | 10 | -32.40 |
| 73 | JNJ | bollinger | $147.51 | $138.66 | stop-loss | 3 | -58.63 |
| 74 | JNJ | macd | $151.58 | $150.28 | time exit (10 days) | 10 | -8.32 |
| 75 | JNJ | macd | $147.45 | $149.18 | time exit (10 days) | 10 | +11.40 |
| 76 | JNJ | macd | $151.37 | $159.97 | time exit (10 days) | 10 | +55.21 |
| 77 | BTC-USD | rsi | $84,373.01 | $91,966.58 | take-profit | 2 | +87.33 |
| 78 | BTC-USD | macd | $89,961.73 | $84,564.02 | stop-loss | 3 | -58.84 |
| 79 | BTC-USD | macd | $84,343.11 | $87,471.70 | time exit (10 days) | 10 | +36.29 |
| 80 | BTC-USD | macd | $83,404.84 | $87,518.91 | time exit (10 days) | 10 | +48.13 |
| 81 | BTC-USD | macd | $106,446.01 | $107,802.33 | time exit (10 days) | 10 | +12.48 |
| 82 | BTC-USD | macd | $109,678.08 | $104,638.09 | time exit (10 days) | 10 | -45.36 |
| 83 | BTC-USD | macd | $110,257.23 | $103,641.80 | stop-loss | 3 | -58.88 |
| 84 | BTC-USD | macd | $106,960.00 | $109,232.07 | time exit (10 days) | 10 | +20.68 |
| 85 | BTC-USD | macd | $119,995.41 | $112,795.69 | stop-loss | 10 | -58.32 |
| 86 | BTC-USD | bollinger | $112,526.91 | $120,172.91 | time exit (10 days) | 10 | +65.76 |
| 87 | BTC-USD | macd | $119,306.76 | $114,274.74 | time exit (10 days) | 10 | -41.26 |
| 88 | ETH-USD | rsi | $2,237.91 | $2,439.32 | take-profit | 2 | +88.04 |
| 89 | ETH-USD | rsi | $1,861.15 | $2,028.66 | take-profit | 9 | +88.85 |
| 90 | ETH-USD | macd | $1,927.00 | $2,100.44 | take-profit | 7 | +89.65 |
| 91 | ETH-USD | macd | $1,622.77 | $1,768.83 | take-profit | 8 | +90.46 |
| 92 | ETH-USD | macd | $2,773.53 | $2,607.12 | stop-loss | 2 | -60.84 |
| 93 | ETH-USD | macd | $2,486.46 | $2,710.25 | take-profit | 9 | +90.70 |
| 94 | ETH-USD | macd | $2,571.34 | $2,802.75 | take-profit | 8 | +91.52 |
| 95 | ETH-USD | macd | $4,263.60 | $4,647.33 | take-profit | 4 | +92.33 |

### OOS-3 — rsi_highconf: no trades

### OOS-3 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $214.99 | $224.33 | time exit (10 days) | 10 | +43.44 |
| 2 | AAPL | rsi_volume | $232.71 | $218.75 | stop-loss | 5 | -60.25 |
| 3 | AAPL | rsi_volume | $221.04 | $240.94 | take-profit | 8 | +89.90 |
| 4 | GOOGL | rsi_volume | $147.62 | $160.91 | take-profit | 7 | +90.66 |
| 5 | TSLA | rsi_volume | $328.50 | $358.07 | take-profit | 2 | +91.49 |
| 6 | JPM | rsi_volume | $221.33 | $233.74 | time exit (10 days) | 10 | +57.49 |
| 7 | JNJ | rsi_volume | $144.60 | $147.56 | time exit (10 days) | 10 | +21.10 |
| 8 | JNJ | rsi_volume | $144.94 | $143.69 | time exit (10 days) | 10 | -8.93 |
| 9 | JNJ | rsi_volume | $138.23 | $137.69 | time exit (10 days) | 10 | -4.01 |
| 10 | BTC-USD | rsi_volume | $53,948.75 | $58,804.14 | take-profit | 7 | +92.74 |
| 11 | ETH-USD | rsi_volume | $2,223.88 | $2,424.04 | take-profit | 7 | +93.72 |

### OOS-3 — bollinger_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | JPM | bollinger_highconf | $196.29 | $202.05 | time exit (10 days) | 10 | +29.33 |

### OOS-3 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | bollinger_volume | $232.71 | $218.75 | stop-loss | 5 | -59.99 |
| 2 | SPY | bollinger_volume | $573.06 | $580.54 | time exit (10 days) | 10 | +12.98 |
| 3 | GOOGL | bollinger_volume | $156.06 | $146.69 | stop-loss | 4 | -59.73 |
| 4 | GOOGL | bollinger_volume | $147.62 | $160.91 | take-profit | 7 | +89.04 |
| 5 | TSLA | bollinger_volume | $328.50 | $358.07 | take-profit | 2 | +89.85 |
| 6 | JPM | bollinger_volume | $196.29 | $202.05 | time exit (10 days) | 10 | +29.54 |
| 7 | JPM | bollinger_volume | $221.33 | $233.74 | time exit (10 days) | 10 | +56.63 |
| 8 | JNJ | bollinger_volume | $144.60 | $147.56 | time exit (10 days) | 10 | +20.78 |
| 9 | JNJ | bollinger_volume | $140.03 | $139.02 | time exit (10 days) | 10 | -7.36 |
| 10 | BTC-USD | bollinger_volume | $53,948.75 | $58,804.14 | take-profit | 7 | +91.28 |
| 11 | ETH-USD | bollinger_volume | $2,223.88 | $2,424.04 | take-profit | 7 | +92.36 |
| 12 | ETH-USD | bollinger_volume | $2,884.57 | $2,711.49 | stop-loss | 1 | -62.12 |

### OOS-3 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi | $214.99 | $224.33 | time exit (10 days) | 10 | +43.44 |
| 2 | AAPL | macd | $226.31 | $224.92 | time exit (10 days) | 10 | -6.15 |
| 3 | AAPL | macd | $227.14 | $228.66 | time exit (10 days) | 10 | +6.72 |
| 4 | AAPL | macd | $226.64 | $241.26 | time exit (10 days) | 10 | +64.81 |
| 5 | AAPL | rsi | $232.71 | $218.75 | stop-loss | 5 | -60.65 |
| 6 | AAPL | rsi | $221.04 | $240.94 | take-profit | 8 | +90.48 |
| 7 | AAPL | macd | $237.64 | $235.42 | time exit (10 days) | 10 | -9.45 |
| 8 | MSFT | macd | $407.76 | $422.50 | time exit (10 days) | 10 | +36.62 |
| 9 | MSFT | macd | $420.86 | $405.06 | time exit (10 days) | 10 | -38.17 |
| 10 | MSFT | macd | $415.97 | $411.34 | time exit (10 days) | 10 | -11.27 |
| 11 | MSFT | macd | $422.18 | $442.89 | time exit (10 days) | 10 | +49.63 |
| 12 | MSFT | rsi | $417.60 | $422.68 | time exit (10 days) | 10 | +12.36 |
| 13 | MSFT | macd | $422.68 | $406.77 | time exit (10 days) | 10 | -38.31 |
| 14 | MSFT | rsi | $405.85 | $395.09 | time exit (10 days) | 10 | -26.89 |
| 15 | NVDA | macd | $118.78 | $121.08 | time exit (10 days) | 10 | +19.57 |
| 16 | NVDA | macd | $148.48 | $139.57 | stop-loss | 7 | -60.81 |
| 17 | NVDA | macd | $139.85 | $152.45 | take-profit | 8 | +90.71 |
| 18 | NVDA | macd | $140.46 | $132.04 | stop-loss | 4 | -60.94 |
| 19 | NVDA | macd | $133.22 | $125.23 | stop-loss | 10 | -60.60 |
| 20 | SPY | macd | $547.65 | $558.58 | time exit (10 days) | 10 | +20.03 |
| 21 | SPY | macd | $563.13 | $566.17 | time exit (10 days) | 10 | +5.42 |
| 22 | SPY | macd | $582.17 | $580.28 | time exit (10 days) | 10 | -3.28 |
| 23 | SPY | macd | $584.05 | $589.20 | time exit (10 days) | 10 | +8.87 |
| 24 | SPY | bollinger | $573.06 | $580.54 | time exit (10 days) | 10 | +13.15 |
| 25 | SPY | macd | $586.07 | $586.25 | time exit (10 days) | 10 | +0.32 |
| 26 | AMZN | macd | $189.07 | $195.78 | time exit (10 days) | 10 | +35.79 |
| 27 | AMZN | macd | $190.83 | $208.01 | take-profit | 7 | +91.12 |
| 28 | AMZN | macd | $197.93 | $215.75 | take-profit | 9 | +91.94 |
| 29 | AMZN | macd | $213.44 | $232.66 | take-profit | 9 | +92.79 |
| 30 | AMZN | macd | $235.01 | $236.17 | time exit (10 days) | 10 | +5.13 |
| 31 | GOOGL | bollinger | $156.06 | $146.69 | stop-loss | 4 | -62.43 |
| 32 | GOOGL | rsi | $147.62 | $160.91 | take-profit | 7 | +93.06 |
| 33 | GOOGL | macd | $156.96 | $164.69 | time exit (10 days) | 10 | +51.40 |
| 34 | GOOGL | macd | $163.81 | $165.56 | time exit (10 days) | 10 | +11.20 |
| 35 | GOOGL | macd | $165.56 | $180.47 | take-profit | 2 | +94.54 |
| 36 | GOOGL | macd | $174.35 | $190.04 | take-profit | 2 | +95.32 |
| 37 | GOOGL | macd | $199.04 | $187.10 | stop-loss | 8 | -64.11 |
| 38 | GOOGL | macd | $202.83 | $190.66 | stop-loss | 3 | -63.73 |
| 39 | META | macd | $529.81 | $568.72 | time exit (10 days) | 10 | +77.53 |
| 40 | META | macd | $581.02 | $546.16 | stop-loss | 7 | -63.80 |
| 41 | META | macd | $588.97 | $620.68 | time exit (10 days) | 10 | +56.91 |
| 42 | META | macd | $614.37 | $632.82 | time exit (10 days) | 10 | +31.92 |
| 43 | META | macd | $612.94 | $668.11 | take-profit | 5 | +95.94 |
| 44 | TSLA | rsi | $219.57 | $239.33 | take-profit | 7 | +96.80 |
| 45 | TSLA | rsi | $217.97 | $237.60 | take-profit | 2 | +97.74 |
| 46 | TSLA | macd | $260.48 | $244.85 | stop-loss | 7 | -65.71 |
| 47 | TSLA | macd | $389.22 | $424.25 | take-profit | 3 | +97.96 |
| 48 | TSLA | rsi | $328.50 | $358.07 | take-profit | 2 | +98.86 |
| 49 | JPM | bollinger | $196.29 | $202.05 | time exit (10 days) | 10 | +32.51 |
| 50 | JPM | macd | $202.65 | $214.25 | time exit (10 days) | 10 | +63.59 |
| 51 | JPM | macd | $237.37 | $231.33 | time exit (10 days) | 10 | -28.43 |
| 52 | JPM | rsi | $221.33 | $233.74 | time exit (10 days) | 10 | +62.51 |
| 53 | JPM | macd | $232.60 | $253.53 | take-profit | 9 | +100.91 |
| 54 | JNJ | rsi | $151.28 | $154.84 | time exit (10 days) | 10 | +26.62 |
| 55 | JNJ | macd | $155.46 | $151.66 | time exit (10 days) | 10 | -27.70 |
| 56 | JNJ | rsi | $144.60 | $147.56 | time exit (10 days) | 10 | +23.14 |
| 57 | JNJ | rsi | $144.94 | $143.69 | time exit (10 days) | 10 | -9.80 |
| 58 | JNJ | macd | $147.00 | $142.86 | time exit (10 days) | 10 | -31.88 |
| 59 | JNJ | bollinger | $140.03 | $139.02 | time exit (10 days) | 10 | -8.16 |
| 60 | JNJ | rsi | $138.23 | $137.69 | time exit (10 days) | 10 | -4.39 |
| 61 | JNJ | macd | $139.02 | $137.96 | time exit (10 days) | 10 | -8.60 |
| 62 | BTC-USD | rsi | $53,948.75 | $58,804.14 | take-profit | 7 | +100.99 |
| 63 | BTC-USD | macd | $58,127.01 | $63,358.45 | take-profit | 7 | +102.01 |
| 64 | BTC-USD | macd | $66,046.12 | $68,161.05 | time exit (10 days) | 10 | +36.59 |
| 65 | BTC-USD | macd | $69,907.76 | $76,199.46 | take-profit | 9 | +103.18 |
| 66 | BTC-USD | macd | $75,639.08 | $82,446.61 | take-profit | 5 | +104.16 |
| 67 | BTC-USD | macd | $106,029.72 | $99,667.94 | stop-loss | 3 | -69.98 |
| 68 | BTC-USD | rsi | $92,643.21 | $100,981.10 | take-profit | 7 | +104.22 |
| 69 | BTC-USD | macd | $98,314.96 | $92,416.06 | stop-loss | 4 | -70.20 |
| 70 | BTC-USD | macd | $100,504.49 | $104,714.65 | time exit (10 days) | 10 | +48.84 |
| 71 | ETH-USD | macd | $2,538.19 | $2,385.90 | stop-loss | 2 | -70.39 |
| 72 | ETH-USD | rsi | $2,223.88 | $2,424.04 | take-profit | 7 | +104.95 |
| 73 | ETH-USD | macd | $2,339.84 | $2,550.43 | take-profit | 9 | +105.88 |
| 74 | ETH-USD | rsi | $2,436.51 | $2,655.81 | take-profit | 4 | +106.84 |
| 75 | ETH-USD | macd | $2,628.90 | $2,471.17 | stop-loss | 9 | -71.86 |
| 76 | ETH-USD | macd | $2,657.37 | $2,497.93 | stop-loss | 2 | -71.43 |
| 77 | ETH-USD | macd | $2,895.59 | $3,156.19 | take-profit | 2 | +106.51 |
| 78 | ETH-USD | macd | $3,361.05 | $3,663.55 | take-profit | 6 | +107.48 |
| 79 | ETH-USD | rsi | $3,356.39 | $3,658.47 | take-profit | 5 | +108.45 |
| 80 | ETH-USD | macd | $3,605.01 | $3,388.71 | stop-loss | 4 | -72.94 |
| 81 | ETH-USD | macd | $3,474.11 | $3,265.66 | stop-loss | 1 | -72.50 |
| 82 | ETH-USD | macd | $3,327.41 | $3,127.76 | stop-loss | 6 | -72.07 |
| 83 | ETH-USD | macd | $3,298.27 | $3,100.37 | stop-loss | 2 | -71.64 |
| 84 | ETH-USD | bollinger | $2,884.57 | $2,711.49 | stop-loss | 1 | -71.20 |
| 85 | ETH-USD | rsi | $2,632.31 | $2,669.34 | time exit (10 days) | 10 | +16.60 |
| 86 | ETH-USD | rsi | $2,675.90 | $2,821.31 | time exit (10 days) | 10 | +64.20 |
| 87 | ETH-USD | macd | $2,726.09 | $2,562.53 | stop-loss | 10 | -71.26 |

### FRESH-1 — rsi_highconf: no trades

### FRESH-1 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | AAPL | rsi_volume | $217.78 | $204.72 | stop-loss | 1 | -59.94 |
| 3 | MSFT | rsi_volume | $381.90 | $408.61 | time exit (10 days) | 10 | +69.47 |
| 4 | MSFT | rsi_volume | $417.90 | $392.83 | stop-loss | 6 | -60.01 |
| 5 | MSFT | rsi_volume | $401.41 | $411.96 | time exit (10 days) | 10 | +26.12 |
| 6 | AMZN | rsi_volume | $167.90 | $157.83 | stop-loss | 1 | -59.78 |
| 7 | GOOGL | rsi_volume | $132.09 | $143.98 | take-profit | 10 | +89.16 |
| 8 | GOOGL | rsi_volume | $165.62 | $155.68 | stop-loss | 6 | -59.97 |
| 9 | GOOGL | rsi_volume | $165.28 | $155.36 | stop-loss | 1 | -59.63 |
| 10 | TSLA | rsi_volume | $173.80 | $166.63 | time exit (10 days) | 10 | -40.75 |
| 11 | JPM | rsi_volume | $171.70 | $182.09 | time exit (10 days) | 10 | +59.54 |
| 12 | JNJ | rsi_volume | $134.72 | $134.85 | time exit (10 days) | 10 | +0.93 |
| 13 | BTC-USD | rsi_volume | $56,034.32 | $61,077.41 | take-profit | 2 | +88.76 |
| 14 | ETH-USD | rsi_volume | $2,458.72 | $2,680.01 | take-profit | 2 | +89.86 |

### FRESH-1 — bollinger_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | JPM | bollinger_highconf | $190.16 | $204.32 | time exit (10 days) | 10 | +74.45 |
| 2 | BTC-USD | bollinger_highconf | $63,821.47 | $59,992.18 | stop-loss | 4 | -60.12 |
| 3 | ETH-USD | bollinger_highconf | $3,157.62 | $3,441.81 | take-profit | 1 | +90.12 |

### FRESH-1 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | bollinger_volume | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | MSFT | bollinger_volume | $381.90 | $408.61 | time exit (10 days) | 10 | +69.89 |
| 3 | SPY | bollinger_volume | $489.09 | $487.58 | time exit (10 days) | 10 | -3.10 |
| 4 | SPY | bollinger_volume | $519.29 | $540.15 | time exit (10 days) | 10 | +40.41 |
| 5 | AMZN | bollinger_volume | $167.90 | $157.83 | stop-loss | 1 | -60.57 |
| 6 | GOOGL | bollinger_volume | $132.09 | $143.98 | take-profit | 10 | +90.34 |
| 7 | GOOGL | bollinger_volume | $165.62 | $155.68 | stop-loss | 6 | -60.77 |
| 8 | TSLA | bollinger_volume | $157.11 | $147.68 | stop-loss | 3 | -60.43 |
| 9 | JPM | bollinger_volume | $171.70 | $182.09 | time exit (10 days) | 10 | +60.58 |
| 10 | JPM | bollinger_volume | $181.89 | $189.14 | time exit (10 days) | 10 | +40.15 |
| 11 | JPM | bollinger_volume | $190.16 | $204.32 | time exit (10 days) | 10 | +75.26 |
| 12 | JNJ | bollinger_volume | $134.72 | $134.85 | time exit (10 days) | 10 | +0.96 |
| 13 | BTC-USD | bollinger_volume | $63,821.47 | $59,992.18 | stop-loss | 4 | -60.89 |
| 14 | ETH-USD | bollinger_volume | $3,157.62 | $3,441.81 | take-profit | 1 | +91.11 |
| 15 | ETH-USD | bollinger_volume | $3,004.90 | $3,275.34 | take-profit | 2 | +91.92 |
| 16 | ETH-USD | bollinger_volume | $2,458.72 | $2,680.01 | take-profit | 2 | +92.76 |

### FRESH-1 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi | $173.21 | $171.85 | time exit (10 days) | 10 | -7.86 |
| 2 | AAPL | macd | $171.85 | $167.02 | time exit (10 days) | 10 | -28.06 |
| 3 | AAPL | macd | $168.06 | $183.19 | take-profit | 6 | +89.72 |
| 4 | AAPL | macd | $194.02 | $211.49 | take-profit | 5 | +90.52 |
| 5 | AAPL | macd | $195.03 | $212.59 | take-profit | 3 | +91.33 |
| 6 | AAPL | macd | $205.19 | $211.24 | time exit (10 days) | 10 | +30.16 |
| 7 | AAPL | macd | $218.19 | $226.72 | time exit (10 days) | 10 | +40.13 |
| 8 | AAPL | rsi | $217.78 | $204.72 | stop-loss | 1 | -61.82 |
| 9 | AAPL | macd | $219.88 | $224.61 | time exit (10 days) | 10 | +22.03 |
| 10 | MSFT | macd | $417.10 | $412.69 | time exit (10 days) | 10 | -10.86 |
| 11 | MSFT | rsi | $381.90 | $408.61 | time exit (10 days) | 10 | +71.73 |
| 12 | MSFT | macd | $405.64 | $417.97 | time exit (10 days) | 10 | +31.38 |
| 13 | MSFT | macd | $425.18 | $444.33 | time exit (10 days) | 10 | +46.64 |
| 14 | MSFT | rsi | $417.90 | $392.83 | stop-loss | 6 | -62.43 |
| 15 | MSFT | rsi | $401.41 | $411.96 | time exit (10 days) | 10 | +27.17 |
| 16 | MSFT | rsi | $398.99 | $410.31 | time exit (10 days) | 10 | +29.43 |
| 17 | MSFT | macd | $409.64 | $404.21 | time exit (10 days) | 10 | -13.78 |
| 18 | NVDA | macd | $86.16 | $91.10 | time exit (10 days) | 10 | +59.59 |
| 19 | NVDA | macd | $85.57 | $93.28 | take-profit | 9 | +94.07 |
| 20 | NVDA | macd | $115.82 | $126.25 | take-profit | 4 | +94.92 |
| 21 | SPY | macd | $498.50 | $507.22 | time exit (10 days) | 10 | +18.61 |
| 22 | SPY | macd | $500.40 | $503.93 | time exit (10 days) | 10 | +7.51 |
| 23 | SPY | macd | $505.55 | $498.36 | time exit (10 days) | 10 | -15.17 |
| 24 | SPY | macd | $508.17 | $503.14 | time exit (10 days) | 10 | -10.53 |
| 25 | SPY | bollinger | $489.09 | $487.58 | time exit (10 days) | 10 | -3.28 |
| 26 | SPY | macd | $496.63 | $514.27 | time exit (10 days) | 10 | +37.77 |
| 27 | SPY | macd | $519.33 | $530.60 | time exit (10 days) | 10 | +23.16 |
| 28 | SPY | macd | $540.47 | $534.97 | time exit (10 days) | 10 | -10.88 |
| 29 | SPY | bollinger | $519.29 | $540.15 | time exit (10 days) | 10 | +42.91 |
| 30 | SPY | macd | $529.86 | $544.04 | time exit (10 days) | 10 | +28.70 |
| 31 | AMZN | macd | $180.97 | $183.62 | time exit (10 days) | 10 | +15.75 |
| 32 | AMZN | macd | $185.07 | $173.97 | stop-loss | 10 | -64.59 |
| 33 | AMZN | macd | $186.21 | $184.70 | time exit (10 days) | 10 | -8.68 |
| 34 | AMZN | rsi | $182.02 | $186.89 | time exit (10 days) | 10 | +28.62 |
| 35 | AMZN | macd | $184.30 | $185.57 | time exit (10 days) | 10 | +7.39 |
| 36 | AMZN | rsi | $182.50 | $171.55 | stop-loss | 5 | -64.39 |
| 37 | AMZN | rsi | $167.90 | $157.83 | stop-loss | 1 | -63.98 |
| 38 | AMZN | macd | $177.59 | $172.12 | time exit (10 days) | 10 | -32.66 |
| 39 | GOOGL | rsi | $132.09 | $143.98 | take-profit | 10 | +95.12 |
| 40 | GOOGL | macd | $137.19 | $149.55 | take-profit | 4 | +96.05 |
| 41 | GOOGL | macd | $170.33 | $167.06 | time exit (10 days) | 10 | -20.65 |
| 42 | GOOGL | macd | $182.50 | $189.60 | time exit (10 days) | 10 | +41.76 |
| 43 | GOOGL | rsi | $165.62 | $155.68 | stop-loss | 6 | -64.69 |
| 44 | GOOGL | rsi | $165.28 | $155.36 | stop-loss | 1 | -64.32 |
| 45 | GOOGL | rsi | $162.31 | $164.25 | time exit (10 days) | 10 | +12.71 |
| 46 | GOOGL | macd | $161.61 | $162.03 | time exit (10 days) | 10 | +2.78 |
| 47 | META | macd | $522.89 | $491.52 | stop-loss | 8 | -64.01 |
| 48 | META | rsi | $426.54 | $464.93 | take-profit | 5 | +95.44 |
| 49 | META | macd | $468.61 | $463.83 | time exit (10 days) | 10 | -10.92 |
| 50 | META | macd | $535.89 | $503.73 | stop-loss | 5 | -64.14 |
| 51 | META | rsi | $462.23 | $503.83 | take-profit | 4 | +95.63 |
| 52 | META | macd | $484.50 | $455.43 | stop-loss | 1 | -64.33 |
| 53 | TSLA | rsi | $173.80 | $166.63 | time exit (10 days) | 10 | -43.96 |
| 54 | TSLA | macd | $172.82 | $162.45 | stop-loss | 10 | -63.68 |
| 55 | TSLA | bollinger | $157.11 | $147.68 | stop-loss | 3 | -63.32 |
| 56 | TSLA | macd | $170.18 | $185.50 | take-profit | 2 | +94.39 |
| 57 | TSLA | macd | $178.01 | $194.03 | take-profit | 7 | +95.21 |
| 58 | TSLA | rsi | $200.00 | $218.00 | take-profit | 5 | +96.08 |
| 59 | JPM | macd | $181.90 | $187.75 | time exit (10 days) | 10 | +34.65 |
| 60 | JPM | rsi | $171.70 | $182.09 | time exit (10 days) | 10 | +65.41 |
| 61 | JPM | macd | $183.63 | $187.56 | time exit (10 days) | 10 | +23.24 |
| 62 | JPM | bollinger | $181.89 | $189.14 | time exit (10 days) | 10 | +43.45 |
| 63 | JPM | macd | $188.10 | $198.43 | time exit (10 days) | 10 | +60.08 |
| 64 | JPM | bollinger | $190.16 | $204.32 | time exit (10 days) | 10 | +81.89 |
| 65 | JPM | macd | $202.01 | $212.19 | time exit (10 days) | 10 | +55.82 |
| 66 | JNJ | macd | $151.78 | $145.28 | time exit (10 days) | 10 | -47.70 |
| 67 | JNJ | bollinger | $146.20 | $147.11 | time exit (10 days) | 10 | +6.87 |
| 68 | JNJ | rsi | $147.11 | $138.28 | stop-loss | 8 | -66.59 |
| 69 | JNJ | rsi | $134.72 | $134.85 | time exit (10 days) | 10 | +1.04 |
| 70 | JNJ | macd | $139.49 | $138.71 | time exit (10 days) | 10 | -6.16 |
| 71 | JNJ | rsi | $136.71 | $137.08 | time exit (10 days) | 10 | +2.95 |
| 72 | JNJ | macd | $138.94 | $137.72 | time exit (10 days) | 10 | -9.71 |
| 73 | JNJ | macd | $137.72 | $145.44 | time exit (10 days) | 10 | +61.75 |
| 74 | JNJ | macd | $138.26 | $143.24 | time exit (10 days) | 10 | +39.93 |
| 75 | BTC-USD | bollinger | $63,821.47 | $59,992.18 | stop-loss | 4 | -66.63 |
| 76 | BTC-USD | macd | $64,031.13 | $66,267.49 | time exit (10 days) | 10 | +38.47 |
| 77 | BTC-USD | macd | $61,448.39 | $66,978.76 | take-profit | 5 | +99.55 |
| 78 | BTC-USD | macd | $71,082.82 | $66,817.85 | stop-loss | 6 | -66.96 |
| 79 | BTC-USD | rsi | $64,252.58 | $60,397.42 | stop-loss | 2 | -66.69 |
| 80 | BTC-USD | rsi | $61,604.80 | $57,908.51 | stop-loss | 7 | -66.16 |
| 81 | BTC-USD | macd | $57,899.46 | $63,110.42 | take-profit | 3 | +98.49 |
| 82 | BTC-USD | rsi | $56,034.32 | $61,077.41 | take-profit | 2 | +99.35 |
| 83 | BTC-USD | macd | $59,493.45 | $64,847.86 | take-profit | 4 | +100.66 |
| 84 | ETH-USD | bollinger | $3,157.62 | $3,441.81 | take-profit | 1 | +101.57 |
| 85 | ETH-USD | macd | $3,695.29 | $3,473.58 | stop-loss | 1 | -68.33 |
| 86 | ETH-USD | bollinger | $3,004.90 | $3,275.34 | take-profit | 2 | +101.87 |
| 87 | ETH-USD | macd | $3,219.91 | $3,026.72 | stop-loss | 7 | -68.53 |
| 88 | ETH-USD | macd | $3,117.58 | $2,930.52 | stop-loss | 6 | -68.13 |
| 89 | ETH-USD | macd | $3,037.06 | $3,310.40 | take-profit | 5 | +101.57 |
| 90 | ETH-USD | rsi | $2,929.39 | $3,193.04 | take-profit | 4 | +102.48 |
| 91 | ETH-USD | macd | $3,177.20 | $3,463.15 | take-profit | 2 | +103.40 |
| 92 | ETH-USD | rsi | $2,458.72 | $2,680.01 | take-profit | 2 | +104.34 |
| 93 | ETH-USD | rsi | $2,553.25 | $2,631.40 | time exit (10 days) | 10 | +35.80 |
| 94 | ETH-USD | macd | $2,662.91 | $2,769.39 | time exit (10 days) | 10 | +46.91 |

### FRESH-2 — rsi_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | ETH-USD | rsi_highconf | $2,233.56 | $2,296.04 | time exit (10 days) | 10 | +27.97 |

### FRESH-2 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $183.32 | $192.83 | time exit (10 days) | 10 | +51.85 |
| 2 | AAPL | rsi_volume | $181.42 | $185.78 | time exit (10 days) | 10 | +24.17 |
| 3 | SPY | rsi_volume | $410.88 | $420.79 | time exit (10 days) | 10 | +24.29 |
| 4 | SPY | rsi_volume | $409.54 | $414.90 | time exit (10 days) | 10 | +13.21 |
| 5 | TSLA | rsi_volume | $205.66 | $224.18 | take-profit | 2 | +91.07 |
| 6 | TSLA | rsi_volume | $219.91 | $206.72 | stop-loss | 4 | -61.21 |
| 7 | TSLA | rsi_volume | $209.14 | $196.59 | stop-loss | 2 | -60.87 |
| 8 | TSLA | rsi_volume | $185.10 | $201.77 | take-profit | 8 | +90.80 |
| 9 | JNJ | rsi_volume | $143.42 | $139.18 | time exit (10 days) | 10 | -30.06 |

### FRESH-2 — bollinger_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | GOOGL | bollinger_highconf | $124.43 | $130.60 | time exit (10 days) | 10 | +49.62 |

### FRESH-2 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AMZN | bollinger_volume | $121.39 | $132.31 | take-profit | 3 | +89.96 |
| 2 | GOOGL | bollinger_volume | $124.43 | $130.60 | time exit (10 days) | 10 | +50.07 |
| 3 | JNJ | bollinger_volume | $144.27 | $143.42 | time exit (10 days) | 10 | -5.98 |
| 4 | JNJ | bollinger_volume | $140.25 | $136.54 | time exit (10 days) | 10 | -26.80 |
| 5 | ETH-USD | bollinger_volume | $1,551.64 | $1,584.31 | time exit (10 days) | 10 | +21.28 |

### FRESH-2 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | macd | $171.34 | $173.49 | time exit (10 days) | 10 | +12.53 |
| 2 | AAPL | macd | $175.20 | $187.43 | time exit (10 days) | 10 | +69.89 |
| 3 | AAPL | macd | $193.35 | $191.27 | time exit (10 days) | 10 | -10.86 |
| 4 | AAPL | macd | $195.58 | $191.25 | time exit (10 days) | 10 | -22.28 |
| 5 | AAPL | rsi | $183.32 | $192.83 | time exit (10 days) | 10 | +52.10 |
| 6 | AAPL | rsi | $181.42 | $185.78 | time exit (10 days) | 10 | +24.29 |
| 7 | AAPL | macd | $189.25 | $177.90 | stop-loss | 10 | -60.74 |
| 8 | AAPL | rsi | $183.04 | $179.46 | time exit (10 days) | 10 | -19.71 |
| 9 | MSFT | macd | $319.77 | $319.19 | time exit (10 days) | 10 | -1.82 |
| 10 | MSFT | macd | $374.77 | $396.41 | time exit (10 days) | 10 | +57.99 |
| 11 | MSFT | macd | $405.40 | $403.79 | time exit (10 days) | 10 | -4.00 |
| 12 | NVDA | rsi | $42.11 | $43.91 | time exit (10 days) | 10 | +43.08 |
| 13 | NVDA | rsi | $42.34 | $46.16 | take-profit | 10 | +91.45 |
| 14 | NVDA | macd | $44.65 | $45.96 | time exit (10 days) | 10 | +30.05 |
| 15 | NVDA | macd | $44.87 | $48.91 | take-profit | 6 | +92.37 |
| 16 | NVDA | macd | $48.75 | $48.03 | time exit (10 days) | 10 | -15.27 |
| 17 | NVDA | macd | $52.10 | $56.79 | take-profit | 7 | +93.03 |
| 18 | SPY | rsi | $410.88 | $420.79 | time exit (10 days) | 10 | +25.15 |
| 19 | SPY | rsi | $409.54 | $414.90 | time exit (10 days) | 10 | +13.68 |
| 20 | SPY | macd | $416.90 | $405.49 | time exit (10 days) | 10 | -28.66 |
| 21 | SPY | macd | $415.43 | $434.20 | time exit (10 days) | 10 | +47.19 |
| 22 | SPY | macd | $447.58 | $461.41 | time exit (10 days) | 10 | +32.41 |
| 23 | SPY | macd | $468.13 | $476.94 | time exit (10 days) | 10 | +19.80 |
| 24 | AMZN | rsi | $127.00 | $128.13 | time exit (10 days) | 10 | +9.38 |
| 25 | AMZN | macd | $131.83 | $123.92 | stop-loss | 10 | -63.31 |
| 26 | AMZN | macd | $128.56 | $120.85 | stop-loss | 1 | -62.90 |
| 27 | AMZN | bollinger | $121.39 | $132.31 | take-profit | 3 | +93.78 |
| 28 | AMZN | macd | $132.71 | $142.59 | time exit (10 days) | 10 | +78.31 |
| 29 | AMZN | macd | $154.07 | $148.47 | time exit (10 days) | 10 | -38.52 |
| 30 | AMZN | macd | $154.62 | $161.26 | time exit (10 days) | 10 | +45.34 |
| 31 | AMZN | macd | $155.34 | $169.32 | take-profit | 10 | +95.43 |
| 32 | GOOGL | macd | $136.28 | $134.32 | time exit (10 days) | 10 | -15.41 |
| 33 | GOOGL | bollinger | $124.43 | $130.60 | time exit (10 days) | 10 | +53.01 |
| 34 | GOOGL | macd | $130.60 | $137.18 | time exit (10 days) | 10 | +54.12 |
| 35 | GOOGL | macd | $134.52 | $137.61 | time exit (10 days) | 10 | +24.79 |
| 36 | GOOGL | macd | $140.94 | $150.44 | time exit (10 days) | 10 | +72.91 |
| 37 | META | macd | $303.91 | $318.10 | time exit (10 days) | 10 | +50.84 |
| 38 | META | macd | $312.80 | $336.74 | time exit (10 days) | 10 | +83.71 |
| 39 | META | macd | $331.74 | $343.00 | time exit (10 days) | 10 | +37.41 |
| 40 | META | macd | $366.96 | $389.45 | time exit (10 days) | 10 | +67.80 |
| 41 | TSLA | macd | $260.05 | $244.45 | stop-loss | 9 | -66.76 |
| 42 | TSLA | rsi | $212.42 | $199.67 | stop-loss | 3 | -66.39 |
| 43 | TSLA | rsi | $205.66 | $224.18 | take-profit | 2 | +99.01 |
| 44 | TSLA | macd | $219.27 | $206.11 | stop-loss | 4 | -66.58 |
| 45 | TSLA | macd | $251.05 | $248.48 | time exit (10 days) | 10 | -11.29 |
| 46 | TSLA | rsi | $219.91 | $206.72 | stop-loss | 4 | -66.07 |
| 47 | TSLA | rsi | $209.14 | $196.59 | stop-loss | 2 | -65.71 |
| 48 | TSLA | rsi | $191.59 | $180.09 | stop-loss | 4 | -65.33 |
| 49 | TSLA | rsi | $185.10 | $201.77 | take-profit | 8 | +97.44 |
| 50 | TSLA | macd | $189.56 | $191.97 | time exit (10 days) | 10 | +13.88 |
| 51 | JPM | macd | $139.02 | $137.48 | time exit (10 days) | 10 | -12.14 |
| 52 | JPM | macd | $137.48 | $136.82 | time exit (10 days) | 10 | -5.23 |
| 53 | JPM | rsi | $133.53 | $136.92 | time exit (10 days) | 10 | +27.72 |
| 54 | JPM | macd | $135.85 | $132.31 | time exit (10 days) | 10 | -28.48 |
| 55 | JPM | macd | $135.20 | $143.84 | time exit (10 days) | 10 | +69.75 |
| 56 | JPM | macd | $166.42 | $164.53 | time exit (10 days) | 10 | -12.50 |
| 57 | JPM | macd | $169.82 | $174.94 | time exit (10 days) | 10 | +33.05 |
| 58 | JNJ | rsi | $145.10 | $149.60 | time exit (10 days) | 10 | +34.14 |
| 59 | JNJ | macd | $150.59 | $144.27 | time exit (10 days) | 10 | -46.31 |
| 60 | JNJ | bollinger | $144.27 | $143.42 | time exit (10 days) | 10 | -6.48 |
| 61 | JNJ | rsi | $142.81 | $140.25 | time exit (10 days) | 10 | -19.70 |
| 62 | JNJ | macd | $145.58 | $139.02 | time exit (10 days) | 10 | -49.44 |
| 63 | JNJ | rsi | $143.42 | $139.18 | time exit (10 days) | 10 | -32.25 |
| 64 | JNJ | bollinger | $140.25 | $136.54 | time exit (10 days) | 10 | -28.78 |
| 65 | JNJ | rsi | $139.18 | $138.06 | time exit (10 days) | 10 | -8.76 |
| 66 | JNJ | rsi | $136.54 | $136.64 | time exit (10 days) | 10 | +0.80 |
| 67 | JNJ | macd | $138.97 | $137.55 | time exit (10 days) | 10 | -11.10 |
| 68 | JNJ | macd | $148.07 | $148.50 | time exit (10 days) | 10 | +3.12 |
| 69 | BTC-USD | macd | $28,519.47 | $31,086.22 | take-profit | 7 | +97.54 |
| 70 | BTC-USD | macd | $37,313.97 | $35,075.13 | stop-loss | 4 | -65.60 |
| 71 | BTC-USD | macd | $39,476.33 | $43,029.21 | take-profit | 3 | +97.70 |
| 72 | BTC-USD | macd | $46,970.50 | $44,152.27 | stop-loss | 4 | -65.66 |
| 73 | BTC-USD | rsi | $40,077.07 | $43,684.02 | take-profit | 6 | +98.11 |
| 74 | BTC-USD | macd | $43,288.25 | $45,301.57 | time exit (10 days) | 10 | +51.14 |
| 75 | ETH-USD | bollinger | $1,551.64 | $1,584.31 | time exit (10 days) | 10 | +23.27 |
| 76 | ETH-USD | macd | $1,607.99 | $1,593.86 | time exit (10 days) | 10 | -9.73 |
| 77 | ETH-USD | macd | $1,604.67 | $1,749.09 | take-profit | 3 | +99.58 |
| 78 | ETH-USD | macd | $2,193.69 | $2,391.13 | take-profit | 6 | +100.48 |
| 79 | ETH-USD | macd | $2,347.57 | $2,206.71 | stop-loss | 6 | -67.58 |
| 80 | ETH-USD | macd | $2,355.84 | $2,214.49 | stop-loss | 1 | -67.17 |
| 81 | ETH-USD | macd | $2,582.10 | $2,427.18 | stop-loss | 8 | -66.77 |
| 82 | ETH-USD | rsi | $2,233.56 | $2,296.04 | time exit (10 days) | 10 | +30.95 |
| 83 | ETH-USD | macd | $2,372.20 | $2,585.70 | take-profit | 6 | +99.83 |

### FRESH-3 — rsi_highconf: no trades

### FRESH-3 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $171.68 | $185.36 | time exit (10 days) | 10 | +79.69 |
| 2 | SPY | rsi_volume | $368.09 | $378.91 | time exit (10 days) | 10 | +29.64 |
| 3 | SPY | rsi_volume | $419.28 | $432.79 | time exit (10 days) | 10 | +32.57 |
| 4 | TSLA | rsi_volume | $173.44 | $189.06 | take-profit | 7 | +91.34 |
| 5 | TSLA | rsi_volume | $162.55 | $152.80 | stop-loss | 3 | -61.38 |
| 6 | TSLA | rsi_volume | $219.22 | $238.95 | take-profit | 3 | +91.55 |
| 7 | JPM | rsi_volume | $138.45 | $136.30 | time exit (10 days) | 10 | -15.91 |
| 8 | JNJ | rsi_volume | $137.18 | $138.12 | time exit (10 days) | 10 | +7.01 |
| 9 | BTC-USD | rsi_volume | $20,187.24 | $22,004.10 | take-profit | 2 | +92.11 |
| 10 | BTC-USD | rsi_volume | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -22.30 |
| 11 | BTC-USD | rsi_volume | $26,031.66 | $25,800.72 | time exit (10 days) | 10 | -9.15 |
| 12 | ETH-USD | rsi_volume | $1,429.16 | $1,557.79 | take-profit | 2 | +92.83 |
| 13 | ETH-USD | rsi_volume | $1,684.93 | $1,657.51 | time exit (10 days) | 10 | -16.94 |
| 14 | ETH-USD | rsi_volume | $1,633.89 | $1,628.49 | time exit (10 days) | 10 | -3.44 |

### FRESH-3 — bollinger_highconf: no trades

### FRESH-3 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | NVDA | bollinger_volume | $42.26 | $46.07 | take-profit | 7 | +90.20 |
| 2 | SPY | bollinger_volume | $368.09 | $378.91 | time exit (10 days) | 10 | +29.67 |
| 3 | SPY | bollinger_volume | $419.28 | $432.79 | time exit (10 days) | 10 | +32.61 |
| 4 | TSLA | bollinger_volume | $173.44 | $189.06 | take-profit | 7 | +91.43 |
| 5 | TSLA | bollinger_volume | $162.55 | $152.80 | stop-loss | 3 | -61.44 |
| 6 | TSLA | bollinger_volume | $219.22 | $238.95 | take-profit | 3 | +91.64 |
| 7 | JPM | bollinger_volume | $115.48 | $119.62 | time exit (10 days) | 10 | +36.79 |
| 8 | JPM | bollinger_volume | $138.45 | $136.30 | time exit (10 days) | 10 | -15.99 |
| 9 | BTC-USD | bollinger_volume | $20,187.24 | $22,004.10 | take-profit | 2 | +92.48 |
| 10 | BTC-USD | bollinger_volume | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -22.36 |
| 11 | ETH-USD | bollinger_volume | $1,429.16 | $1,557.79 | take-profit | 2 | +93.28 |
| 12 | ETH-USD | bollinger_volume | $1,684.93 | $1,657.51 | time exit (10 days) | 10 | -17.02 |

### FRESH-3 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | macd | $153.35 | $159.76 | time exit (10 days) | 10 | +41.79 |
| 2 | AAPL | macd | $166.87 | $169.54 | time exit (10 days) | 10 | +16.06 |
| 3 | AAPL | macd | $170.79 | $172.59 | time exit (10 days) | 10 | +10.62 |
| 4 | AAPL | macd | $172.48 | $178.29 | time exit (10 days) | 10 | +33.91 |
| 5 | AAPL | macd | $174.65 | $181.25 | time exit (10 days) | 10 | +38.18 |
| 6 | AAPL | macd | $185.30 | $186.99 | time exit (10 days) | 10 | +9.25 |
| 7 | AAPL | rsi | $175.36 | $174.03 | time exit (10 days) | 10 | -7.69 |
| 8 | AAPL | rsi | $171.68 | $185.36 | time exit (10 days) | 10 | +80.83 |
| 9 | MSFT | macd | $258.25 | $272.91 | time exit (10 days) | 10 | +58.02 |
| 10 | MSFT | macd | $296.58 | $301.71 | time exit (10 days) | 10 | +17.80 |
| 11 | MSFT | macd | $310.57 | $327.03 | time exit (10 days) | 10 | +54.57 |
| 12 | MSFT | macd | $317.79 | $318.64 | time exit (10 days) | 10 | +2.77 |
| 13 | MSFT | macd | $339.41 | $332.04 | time exit (10 days) | 10 | -22.50 |
| 14 | MSFT | macd | $337.10 | $327.54 | time exit (10 days) | 10 | -29.32 |
| 15 | MSFT | macd | $342.22 | $321.69 | stop-loss | 2 | -61.82 |
| 16 | MSFT | rsi | $309.63 | $320.26 | time exit (10 days) | 10 | +35.17 |
| 17 | NVDA | macd | $25.46 | $27.30 | time exit (10 days) | 10 | +74.27 |
| 18 | NVDA | macd | $28.12 | $29.12 | time exit (10 days) | 10 | +36.78 |
| 19 | NVDA | macd | $28.59 | $31.17 | take-profit | 9 | +93.78 |
| 20 | NVDA | macd | $28.86 | $31.46 | take-profit | 3 | +94.38 |
| 21 | NVDA | macd | $45.33 | $46.61 | time exit (10 days) | 10 | +29.87 |
| 22 | NVDA | bollinger | $42.26 | $46.07 | take-profit | 7 | +95.67 |
| 23 | SPY | rsi | $368.09 | $378.91 | time exit (10 days) | 10 | +31.47 |
| 24 | SPY | macd | $381.94 | $391.28 | time exit (10 days) | 10 | +26.25 |
| 25 | SPY | macd | $401.39 | $409.71 | time exit (10 days) | 10 | +22.29 |
| 26 | SPY | macd | $402.15 | $415.34 | time exit (10 days) | 10 | +35.36 |
| 27 | SPY | macd | $426.49 | $436.48 | time exit (10 days) | 10 | +25.34 |
| 28 | SPY | macd | $432.03 | $434.85 | time exit (10 days) | 10 | +7.07 |
| 29 | SPY | rsi | $419.28 | $432.79 | time exit (10 days) | 10 | +34.96 |
| 30 | AMZN | macd | $96.20 | $100.25 | time exit (10 days) | 10 | +45.83 |
| 31 | AMZN | macd | $104.30 | $103.65 | time exit (10 days) | 10 | -6.81 |
| 32 | AMZN | macd | $110.19 | $116.75 | time exit (10 days) | 10 | +65.04 |
| 33 | AMZN | macd | $134.68 | $126.60 | stop-loss | 8 | -65.93 |
| 34 | AMZN | macd | $135.36 | $127.24 | stop-loss | 5 | -65.53 |
| 35 | AMZN | macd | $139.57 | $131.20 | stop-loss | 10 | -65.11 |
| 36 | GOOGL | macd | $93.08 | $101.47 | take-profit | 3 | +97.23 |
| 37 | GOOGL | macd | $110.70 | $120.67 | take-profit | 6 | +98.11 |
| 38 | GOOGL | macd | $124.24 | $131.33 | time exit (10 days) | 10 | +62.73 |
| 39 | GOOGL | macd | $128.05 | $128.44 | time exit (10 days) | 10 | +3.35 |
| 40 | META | macd | $195.87 | $203.40 | time exit (10 days) | 10 | +42.47 |
| 41 | META | macd | $238.04 | $231.59 | time exit (10 days) | 10 | -30.07 |
| 42 | META | macd | $244.51 | $266.52 | take-profit | 9 | +99.63 |
| 43 | META | macd | $279.16 | $284.26 | time exit (10 days) | 10 | +20.41 |
| 44 | META | macd | $306.41 | $288.02 | stop-loss | 8 | -67.12 |
| 45 | META | macd | $315.58 | $296.64 | stop-loss | 10 | -66.73 |
| 46 | META | rsi | $282.39 | $293.08 | time exit (10 days) | 10 | +41.86 |
| 47 | TSLA | rsi | $173.44 | $189.06 | take-profit | 7 | +99.92 |
| 48 | TSLA | macd | $191.81 | $180.30 | stop-loss | 8 | -67.17 |
| 49 | TSLA | rsi | $162.55 | $152.80 | stop-loss | 3 | -66.74 |
| 50 | TSLA | macd | $170.06 | $180.14 | time exit (10 days) | 10 | +65.56 |
| 51 | TSLA | macd | $282.48 | $265.53 | stop-loss | 3 | -66.76 |
| 52 | TSLA | rsi | $219.22 | $238.95 | take-profit | 3 | +99.53 |
| 53 | JPM | bollinger | $115.48 | $119.62 | time exit (10 days) | 10 | +39.96 |
| 54 | JPM | macd | $118.18 | $128.34 | time exit (10 days) | 10 | +96.24 |
| 55 | JPM | macd | $128.76 | $128.68 | time exit (10 days) | 10 | -0.70 |
| 56 | JPM | macd | $129.95 | $132.53 | time exit (10 days) | 10 | +22.39 |
| 57 | JPM | macd | $134.55 | $142.87 | time exit (10 days) | 10 | +69.97 |
| 58 | JPM | rsi | $138.45 | $136.30 | time exit (10 days) | 10 | -17.66 |
| 59 | JNJ | rsi | $137.18 | $138.12 | time exit (10 days) | 10 | +7.77 |
| 60 | JNJ | rsi | $144.37 | $140.73 | time exit (10 days) | 10 | -28.66 |
| 61 | JNJ | rsi | $143.01 | $144.21 | time exit (10 days) | 10 | +9.50 |
| 62 | JNJ | rsi | $140.73 | $146.54 | time exit (10 days) | 10 | +46.86 |
| 63 | JNJ | macd | $144.33 | $149.63 | time exit (10 days) | 10 | +41.84 |
| 64 | JNJ | rsi | $144.78 | $157.82 | take-profit | 7 | +103.09 |
| 65 | JNJ | macd | $153.51 | $155.57 | time exit (10 days) | 10 | +15.53 |
| 66 | BTC-USD | rsi | $20,187.24 | $22,004.10 | take-profit | 2 | +103.92 |
| 67 | BTC-USD | macd | $24,746.07 | $26,973.23 | take-profit | 3 | +104.90 |
| 68 | BTC-USD | macd | $30,235.06 | $28,420.96 | stop-loss | 9 | -70.57 |
| 69 | BTC-USD | rsi | $26,930.64 | $26,334.82 | time exit (10 days) | 10 | -25.86 |
| 70 | BTC-USD | rsi | $26,890.13 | $27,745.88 | time exit (10 days) | 10 | +37.14 |
| 71 | BTC-USD | macd | $26,868.35 | $27,238.78 | time exit (10 days) | 10 | +16.11 |
| 72 | BTC-USD | macd | $27,238.78 | $25,604.46 | stop-loss | 4 | -70.28 |
| 73 | BTC-USD | macd | $26,510.68 | $28,896.63 | take-profit | 4 | +104.74 |
| 74 | BTC-USD | macd | $29,765.49 | $27,979.56 | stop-loss | 9 | -70.54 |
| 75 | BTC-USD | rsi | $26,664.55 | $26,089.69 | time exit (10 days) | 10 | -25.18 |
| 76 | BTC-USD | rsi | $26,031.66 | $25,800.72 | time exit (10 days) | 10 | -10.35 |
| 77 | ETH-USD | rsi | $1,429.16 | $1,557.79 | take-profit | 2 | +104.93 |
| 78 | ETH-USD | macd | $1,680.31 | $1,831.54 | take-profit | 5 | +105.88 |
| 79 | ETH-USD | rsi | $1,812.59 | $1,893.08 | time exit (10 days) | 10 | +52.71 |
| 80 | ETH-USD | macd | $1,854.38 | $1,907.26 | time exit (10 days) | 10 | +34.00 |
| 81 | ETH-USD | macd | $1,792.12 | $1,933.19 | time exit (10 days) | 10 | +94.11 |
| 82 | ETH-USD | macd | $2,006.51 | $1,886.12 | stop-loss | 4 | -72.30 |
| 83 | ETH-USD | macd | $1,850.75 | $1,739.71 | stop-loss | 7 | -71.87 |
| 84 | ETH-USD | rsi | $1,684.93 | $1,657.51 | time exit (10 days) | 10 | -19.38 |
| 85 | ETH-USD | rsi | $1,633.89 | $1,628.49 | time exit (10 days) | 10 | -3.93 |

### FRESH-4 — rsi_highconf: no trades

### FRESH-4 — rsi_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi_volume | $123.83 | $131.07 | time exit (10 days) | 10 | +58.47 |
| 2 | MSFT | rsi_volume | $236.64 | $232.98 | time exit (10 days) | 10 | -15.55 |
| 3 | MSFT | rsi_volume | $215.75 | $235.17 | take-profit | 8 | +90.40 |
| 4 | META | rsi_volume | $135.08 | $132.52 | time exit (10 days) | 10 | -19.18 |
| 5 | META | rsi_volume | $92.28 | $100.59 | take-profit | 7 | +91.13 |
| 6 | META | rsi_volume | $95.80 | $104.44 | take-profit | 3 | +92.01 |
| 7 | TSLA | rsi_volume | $242.40 | $227.86 | stop-loss | 4 | -61.77 |
| 8 | TSLA | rsi_volume | $219.35 | $206.19 | stop-loss | 3 | -61.41 |
| 9 | TSLA | rsi_volume | $167.87 | $182.98 | take-profit | 2 | +91.58 |
| 10 | TSLA | rsi_volume | $137.80 | $129.53 | stop-loss | 2 | -61.61 |
| 11 | TSLA | rsi_volume | $112.71 | $122.85 | take-profit | 1 | +91.80 |
| 12 | JNJ | rsi_volume | $151.59 | $147.88 | time exit (10 days) | 10 | -25.21 |

### FRESH-4 — bollinger_highconf

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | BTC-USD | bollinger_highconf | $21,819.04 | $23,782.75 | take-profit | 6 | +89.94 |

### FRESH-4 — bollinger_volume

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | MSFT | bollinger_volume | $215.75 | $235.17 | take-profit | 8 | +90.01 |
| 2 | NVDA | bollinger_volume | $11.63 | $10.93 | stop-loss | 3 | -60.58 |
| 3 | SPY | bollinger_volume | $345.90 | $341.82 | time exit (10 days) | 10 | -11.82 |
| 4 | AMZN | bollinger_volume | $102.44 | $96.29 | stop-loss | 1 | -60.14 |
| 5 | META | bollinger_volume | $92.28 | $100.59 | take-profit | 7 | +89.71 |
| 6 | TSLA | bollinger_volume | $242.40 | $227.86 | stop-loss | 4 | -60.27 |
| 7 | TSLA | bollinger_volume | $197.08 | $185.26 | stop-loss | 2 | -59.90 |
| 8 | TSLA | bollinger_volume | $160.95 | $151.29 | stop-loss | 3 | -59.58 |
| 9 | TSLA | bollinger_volume | $137.80 | $129.53 | stop-loss | 2 | -59.22 |
| 10 | JPM | bollinger_volume | $96.44 | $95.67 | time exit (10 days) | 10 | -7.87 |
| 11 | JNJ | bollinger_volume | $151.59 | $147.88 | time exit (10 days) | 10 | -23.99 |
| 12 | BTC-USD | bollinger_volume | $21,819.04 | $23,782.75 | take-profit | 6 | +87.97 |
| 13 | ETH-USD | bollinger_volume | $1,168.26 | $1,226.97 | time exit (10 days) | 10 | +49.57 |

### FRESH-4 — combined

| # | Symbol | Source | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---|---|---:|
| 1 | AAPL | rsi | $137.73 | $146.59 | time exit (10 days) | 10 | +64.34 |
| 2 | AAPL | macd | $139.68 | $152.26 | take-profit | 9 | +90.63 |
| 3 | AAPL | macd | $147.07 | $141.69 | time exit (10 days) | 10 | -37.18 |
| 4 | AAPL | rsi | $129.98 | $122.18 | stop-loss | 8 | -60.72 |
| 5 | AAPL | rsi | $123.83 | $131.07 | time exit (10 days) | 10 | +58.80 |
| 6 | AAPL | rsi | $122.83 | $133.88 | take-profit | 7 | +91.03 |
| 7 | AAPL | macd | $127.87 | $139.37 | take-profit | 9 | +91.82 |
| 8 | MSFT | rsi | $236.64 | $232.98 | time exit (10 days) | 10 | -15.92 |
| 9 | MSFT | macd | $232.98 | $219.00 | stop-loss | 6 | -61.70 |
| 10 | MSFT | macd | $229.87 | $224.65 | time exit (10 days) | 10 | -23.22 |
| 11 | MSFT | macd | $235.15 | $240.19 | time exit (10 days) | 10 | +21.87 |
| 12 | MSFT | macd | $249.34 | $234.38 | stop-loss | 4 | -61.31 |
| 13 | MSFT | rsi | $215.75 | $235.17 | take-profit | 8 | +91.44 |
| 14 | MSFT | macd | $232.17 | $235.55 | time exit (10 days) | 10 | +14.92 |
| 15 | NVDA | rsi | $13.33 | $12.53 | stop-loss | 3 | -61.89 |
| 16 | NVDA | macd | $12.69 | $11.93 | stop-loss | 1 | -61.13 |
| 17 | NVDA | bollinger | $11.63 | $10.93 | stop-loss | 3 | -60.89 |
| 18 | NVDA | macd | $16.87 | $15.85 | stop-loss | 4 | -60.76 |
| 19 | NVDA | macd | $17.48 | $16.43 | stop-loss | 4 | -60.00 |
| 20 | NVDA | bollinger | $13.99 | $15.25 | take-profit | 7 | +89.76 |
| 21 | NVDA | rsi | $14.22 | $15.51 | take-profit | 2 | +91.36 |
| 22 | NVDA | macd | $15.86 | $17.29 | take-profit | 4 | +91.72 |
| 23 | SPY | bollinger | $345.90 | $341.82 | time exit (10 days) | 10 | -12.06 |
| 24 | SPY | macd | $358.03 | $336.55 | stop-loss | 6 | -61.32 |
| 25 | SPY | macd | $347.47 | $360.77 | time exit (10 days) | 10 | +38.88 |
| 26 | SPY | rsi | $362.96 | $361.86 | time exit (10 days) | 10 | -3.10 |
| 27 | SPY | macd | $369.95 | $381.72 | time exit (10 days) | 10 | +32.44 |
| 28 | AMZN | macd | $120.95 | $113.69 | stop-loss | 3 | -61.39 |
| 29 | AMZN | macd | $116.36 | $109.38 | stop-loss | 8 | -60.98 |
| 30 | AMZN | bollinger | $102.44 | $96.29 | stop-loss | 1 | -60.67 |
| 31 | AMZN | rsi | $90.53 | $98.68 | take-profit | 3 | +90.43 |
| 32 | AMZN | rsi | $98.49 | $92.58 | stop-loss | 4 | -60.82 |
| 33 | AMZN | rsi | $88.25 | $96.20 | take-profit | 5 | +90.75 |
| 34 | AMZN | rsi | $85.19 | $83.12 | time exit (10 days) | 10 | -24.70 |
| 35 | AMZN | macd | $85.82 | $93.55 | take-profit | 6 | +91.34 |
| 36 | GOOGL | macd | $100.68 | $94.64 | stop-loss | 7 | -61.40 |
| 37 | GOOGL | macd | $95.50 | $95.14 | time exit (10 days) | 10 | -3.85 |
| 38 | GOOGL | rsi | $88.18 | $85.39 | time exit (10 days) | 10 | -32.18 |
| 39 | GOOGL | rsi | $85.21 | $90.27 | time exit (10 days) | 10 | +60.19 |
| 40 | GOOGL | rsi | $85.39 | $93.08 | take-profit | 10 | +91.84 |
| 41 | GOOGL | macd | $87.19 | $95.04 | take-profit | 8 | +92.61 |
| 42 | META | rsi | $135.08 | $132.52 | time exit (10 days) | 10 | -19.64 |
| 43 | META | macd | $137.66 | $129.40 | stop-loss | 4 | -62.17 |
| 44 | META | macd | $132.77 | $124.80 | stop-loss | 4 | -61.80 |
| 45 | META | rsi | $92.28 | $100.59 | take-profit | 7 | +92.22 |
| 46 | META | rsi | $95.80 | $104.44 | take-profit | 3 | +93.11 |
| 47 | META | macd | $110.81 | $110.35 | time exit (10 days) | 10 | -4.31 |
| 48 | META | macd | $119.12 | $129.85 | take-profit | 6 | +93.84 |
| 49 | TSLA | macd | $304.42 | $286.15 | stop-loss | 8 | -63.08 |
| 50 | TSLA | rsi | $242.40 | $227.86 | stop-loss | 4 | -62.66 |
| 51 | TSLA | rsi | $222.96 | $209.58 | stop-loss | 3 | -62.32 |
| 52 | TSLA | rsi | $219.35 | $206.19 | stop-loss | 3 | -61.93 |
| 53 | TSLA | macd | $222.42 | $209.07 | stop-loss | 8 | -61.58 |
| 54 | TSLA | bollinger | $197.08 | $185.26 | stop-loss | 2 | -61.17 |
| 55 | TSLA | rsi | $167.87 | $182.98 | take-profit | 2 | +91.25 |
| 56 | TSLA | macd | $182.86 | $171.89 | stop-loss | 9 | -61.36 |
| 57 | TSLA | bollinger | $160.95 | $151.29 | stop-loss | 3 | -61.02 |
| 58 | TSLA | rsi | $137.80 | $129.53 | stop-loss | 2 | -60.65 |
| 59 | TSLA | rsi | $112.71 | $122.85 | take-profit | 1 | +90.38 |
| 60 | TSLA | rsi | $110.34 | $103.72 | stop-loss | 1 | -60.81 |
| 61 | TSLA | macd | $119.77 | $130.56 | take-profit | 5 | +90.77 |
| 62 | JPM | bollinger | $96.44 | $95.67 | time exit (10 days) | 10 | -8.16 |
| 63 | JPM | macd | $98.54 | $92.62 | stop-loss | 4 | -60.99 |
| 64 | JPM | macd | $99.66 | $108.63 | take-profit | 3 | +90.90 |
| 65 | JPM | rsi | $119.08 | $124.24 | time exit (10 days) | 10 | +44.11 |
| 66 | JPM | macd | $123.12 | $125.36 | time exit (10 days) | 10 | +18.61 |
| 67 | JPM | macd | $128.80 | $129.46 | time exit (10 days) | 10 | +5.22 |
| 68 | JPM | macd | $130.27 | $128.17 | time exit (10 days) | 10 | -16.55 |
| 69 | JPM | macd | $131.45 | $130.85 | time exit (10 days) | 10 | -4.65 |
| 70 | JNJ | macd | $147.83 | $148.18 | time exit (10 days) | 10 | +2.39 |
| 71 | JNJ | macd | $147.41 | $153.81 | time exit (10 days) | 10 | +44.41 |
| 72 | JNJ | macd | $157.28 | $160.61 | time exit (10 days) | 10 | +21.78 |
| 73 | JNJ | macd | $161.93 | $152.22 | stop-loss | 8 | -61.79 |
| 74 | JNJ | rsi | $151.59 | $147.88 | time exit (10 days) | 10 | -25.07 |
| 75 | JNJ | rsi | $151.13 | $145.67 | time exit (10 days) | 10 | -36.93 |
| 76 | JNJ | rsi | $147.88 | $145.13 | time exit (10 days) | 10 | -18.94 |
| 77 | BTC-USD | macd | $19,426.72 | $19,416.57 | time exit (10 days) | 10 | -0.53 |
| 78 | BTC-USD | macd | $19,382.90 | $19,567.01 | time exit (10 days) | 10 | +9.65 |
| 79 | BTC-USD | macd | $19,268.09 | $20,770.44 | time exit (10 days) | 10 | +79.17 |
| 80 | BTC-USD | rsi | $15,787.28 | $16,967.13 | time exit (10 days) | 10 | +76.57 |
| 81 | BTC-USD | macd | $16,604.46 | $17,130.49 | time exit (10 days) | 10 | +32.67 |
| 82 | BTC-USD | macd | $16,919.80 | $16,836.74 | time exit (10 days) | 10 | -5.08 |
| 83 | BTC-USD | macd | $16,679.86 | $18,181.04 | take-profit | 9 | +93.07 |
| 84 | BTC-USD | bollinger | $21,819.04 | $23,782.75 | take-profit | 6 | +93.87 |
| 85 | BTC-USD | macd | $24,565.60 | $23,091.67 | stop-loss | 7 | -63.23 |
| 86 | ETH-USD | macd | $1,327.98 | $1,291.34 | time exit (10 days) | 10 | -28.90 |
| 87 | ETH-USD | rsi | $1,108.35 | $1,208.11 | take-profit | 3 | +94.03 |
| 88 | ETH-USD | macd | $1,205.90 | $1,271.65 | time exit (10 days) | 10 | +57.47 |
| 89 | ETH-USD | bollinger | $1,168.26 | $1,226.97 | time exit (10 days) | 10 | +53.26 |
| 90 | ETH-USD | macd | $1,218.96 | $1,256.53 | time exit (10 days) | 10 | +32.83 |
| 91 | ETH-USD | macd | $1,214.66 | $1,323.98 | take-profit | 7 | +96.16 |
| 92 | ETH-USD | macd | $1,694.78 | $1,593.10 | stop-loss | 7 | -64.68 |

