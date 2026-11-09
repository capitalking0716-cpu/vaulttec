# VaultTec — Phase 4e Trend-Following Test Report

Generated: 2026-11-09T12:48:40.464896 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests an entry rule on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Trend-following test on the three FRESH windows (FRESH-1/2/3) from Phase 4d, using the cached real Yahoo Finance histories only — no new fetch. Entry: buy when close > SMA-20 and SMA-20 > SMA-50, history up to the trade day only, no look-ahead. Exits: baseline (3% stop / 4.5% target / 10 days), wide-5 (5% / 7.5% / 10 days), wide-6 (6% / 9% / 10 days). Every trade through the real PaperTradingEngine and Risk Engine, balanced profile, $10,000 virtual cash, long-only, 5-day walk-forward steps.
- Entry: Buy when close > 20-day SMA AND 20-day SMA > 50-day SMA, on history up to the trade day only. No trade when either average is not yet defined.
- Data: yfinance (delayed real market data, free — Yahoo Finance) — cached copies in data/fresh-cache/
- Verdict rule: A variant 'holds up' when its pooled fresh-window paper P&L is > $0 AND its pooled win rate is > 40% (the 1.5:1 break-even) AND it is positive in at least 2 of the 3 fresh windows.

## Pooled fresh-window verdict — 3 fresh windows

### Trend-following (buy uptrend: close > SMA-20 > SMA-50)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows | Holds up |
|---|---:|---:|---:|---:|:---:|:---:|
| baseline | 422 | 53.3% | $2,396.87 | $5.68 | 3/3 | yes |
| wide-5 | 422 | 61.8% | $5,442.28 | $12.90 | 3/3 | yes |
| wide-6 | 422 | 61.8% | $5,163.64 | $12.24 | 2/3 | yes |

## Verdict

- Best variant by pooled fresh P&L: **wide-5** ($5,442.28).
- Variants holding up on fresh data: ['baseline', 'wide-5', 'wide-6'].

## Limits — read this before trusting the result

None of FRESH-1/2/3 is a falling window like OOS-2 (Feb-Aug 2025), so this run cannot prove trend-following does better in a falling market — that needs OOS-2, whose histories are not cached and would need a fresh Yahoo fetch. Three windows are still past prices: nothing here proves future profits, and live paper trades over real days plus a compliance/legal review are still required before any real money is considered.

## FRESH-1 — 2024-03-04 → 2024-09-01 (fresh — never used for selection)

- History: 12 symbols fetched from cache; failed: none

### Trend-following (buy uptrend: close > SMA-20 > SMA-50)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 120 | 49.2% | $422.30 | $3.52 | $35.88 | $-27.78 | -2.55% | {'time exit (10 days)': 29, 'take-profit': 38, 'stop-loss': 53} | 0 |
| wide-5 | 120 | 53.3% | $438.64 | $3.66 | $42.39 | $-40.62 | -4.19% | {'time exit (10 days)': 64, 'take-profit': 20, 'stop-loss': 36} | 0 |
| wide-6 | 120 | 51.7% | $-3.74 | $-0.03 | $43.72 | $-46.80 | -7.38% | {'time exit (10 days)': 71, 'take-profit': 13, 'stop-loss': 36} | 0 |

- baseline per symbol: {'AAPL': 11, 'MSFT': 11, 'NVDA': 11, 'SPY': 13, 'AMZN': 9, 'GOOGL': 15, 'META': 7, 'TSLA': 8, 'JPM': 16, 'JNJ': 6, 'BTC-USD': 8, 'ETH-USD': 5}
- wide-5 per symbol: {'AAPL': 11, 'MSFT': 11, 'NVDA': 11, 'SPY': 13, 'AMZN': 9, 'GOOGL': 15, 'META': 7, 'TSLA': 8, 'JPM': 16, 'JNJ': 6, 'BTC-USD': 8, 'ETH-USD': 5}
- wide-6 per symbol: {'AAPL': 11, 'MSFT': 11, 'NVDA': 11, 'SPY': 13, 'AMZN': 9, 'GOOGL': 15, 'META': 7, 'TSLA': 8, 'JPM': 16, 'JNJ': 6, 'BTC-USD': 8, 'ETH-USD': 5}

## FRESH-2 — 2023-09-06 → 2024-03-04 (fresh — never used for selection)

- History: 12 symbols fetched from cache; failed: none

### Trend-following (buy uptrend: close > SMA-20 > SMA-50)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 139 | 54.0% | $997.03 | $7.17 | $37.44 | $-28.30 | -2.08% | {'time exit (10 days)': 36, 'take-profit': 48, 'stop-loss': 55} | 0 |
| wide-5 | 139 | 61.9% | $2,115.68 | $15.22 | $51.47 | $-43.61 | -3.06% | {'time exit (10 days)': 69, 'stop-loss': 37, 'take-profit': 33} | 0 |
| wide-6 | 139 | 63.3% | $2,219.40 | $15.97 | $54.37 | $-50.30 | -2.59% | {'time exit (10 days)': 83, 'stop-loss': 32, 'take-profit': 24} | 0 |

- baseline per symbol: {'AAPL': 6, 'MSFT': 13, 'NVDA': 11, 'SPY': 12, 'AMZN': 13, 'GOOGL': 11, 'META': 15, 'TSLA': 7, 'JPM': 10, 'JNJ': 4, 'BTC-USD': 21, 'ETH-USD': 16}
- wide-5 per symbol: {'AAPL': 6, 'MSFT': 13, 'NVDA': 11, 'SPY': 12, 'AMZN': 13, 'GOOGL': 11, 'META': 15, 'TSLA': 7, 'JPM': 10, 'JNJ': 4, 'BTC-USD': 21, 'ETH-USD': 16}
- wide-6 per symbol: {'AAPL': 6, 'MSFT': 13, 'NVDA': 11, 'SPY': 12, 'AMZN': 13, 'GOOGL': 11, 'META': 15, 'TSLA': 7, 'JPM': 10, 'JNJ': 4, 'BTC-USD': 21, 'ETH-USD': 16}

## FRESH-3 — 2023-03-10 → 2023-09-06 (fresh — never used for selection)

- History: 12 symbols fetched from cache; failed: none

### Trend-following (buy uptrend: close > SMA-20 > SMA-50)

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Exits | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| baseline | 163 | 55.8% | $977.54 | $6.00 | $34.53 | $-30.07 | -2.53% | {'take-profit': 51, 'time exit (10 days)': 48, 'stop-loss': 64} | 0 |
| wide-5 | 163 | 68.1% | $2,887.96 | $17.72 | $45.29 | $-41.14 | -2.14% | {'time exit (10 days)': 99, 'stop-loss': 29, 'take-profit': 35} | 0 |
| wide-6 | 163 | 68.1% | $2,947.98 | $18.09 | $47.41 | $-44.52 | -2.35% | {'time exit (10 days)': 118, 'stop-loss': 21, 'take-profit': 24} | 0 |

- baseline per symbol: {'AAPL': 19, 'MSFT': 17, 'NVDA': 18, 'SPY': 15, 'AMZN': 14, 'GOOGL': 15, 'META': 19, 'TSLA': 7, 'JPM': 11, 'JNJ': 9, 'BTC-USD': 12, 'ETH-USD': 7}
- wide-5 per symbol: {'AAPL': 19, 'MSFT': 17, 'NVDA': 18, 'SPY': 15, 'AMZN': 14, 'GOOGL': 15, 'META': 19, 'TSLA': 7, 'JPM': 11, 'JNJ': 9, 'BTC-USD': 12, 'ETH-USD': 7}
- wide-6 per symbol: {'AAPL': 19, 'MSFT': 17, 'NVDA': 18, 'SPY': 15, 'AMZN': 14, 'GOOGL': 15, 'META': 19, 'TSLA': 7, 'JPM': 11, 'JNJ': 9, 'BTC-USD': 12, 'ETH-USD': 7}

## Trades (every trade, in order) — wide-6

### FRESH-1 — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $185.66 | $188.49 | time exit (10 days) | 10 | +15.24 |
| 2 | AAPL | $190.53 | $194.02 | time exit (10 days) | 10 | +18.33 |
| 3 | AAPL | $188.49 | $205.47 | take-profit | 10 | +90.37 |
| 4 | AAPL | $194.02 | $211.49 | take-profit | 5 | +91.15 |
| 5 | AAPL | $211.06 | $212.08 | time exit (10 days) | 10 | +4.95 |
| 6 | AAPL | $207.70 | $224.20 | time exit (10 days) | 10 | +81.19 |
| 7 | AAPL | $212.08 | $228.36 | time exit (10 days) | 10 | +79.08 |
| 8 | AAPL | $224.20 | $222.19 | time exit (10 days) | 10 | -9.32 |
| 9 | AAPL | $228.36 | $214.66 | stop-loss | 9 | -62.23 |
| 10 | AAPL | $222.19 | $217.78 | time exit (10 days) | 10 | -20.47 |
| 11 | AAPL | $224.17 | $227.10 | time exit (10 days) | 10 | +13.43 |
| 12 | MSFT | $409.35 | $413.39 | time exit (10 days) | 10 | +10.16 |
| 13 | MSFT | $414.79 | $418.14 | time exit (10 days) | 10 | +8.34 |
| 14 | MSFT | $413.39 | $406.66 | time exit (10 days) | 10 | -16.81 |
| 15 | MSFT | $418.14 | $393.05 | stop-loss | 8 | -61.83 |
| 16 | MSFT | $421.74 | $433.42 | time exit (10 days) | 10 | +28.37 |
| 17 | MSFT | $416.67 | $437.98 | time exit (10 days) | 10 | +52.53 |
| 18 | MSFT | $433.42 | $445.01 | time exit (10 days) | 10 | +27.60 |
| 19 | MSFT | $437.98 | $459.46 | time exit (10 days) | 10 | +50.76 |
| 20 | MSFT | $445.01 | $445.69 | time exit (10 days) | 10 | +1.60 |
| 21 | MSFT | $459.46 | $431.89 | stop-loss | 8 | -62.42 |
| 22 | MSFT | $445.69 | $418.95 | stop-loss | 9 | -62.04 |
| 23 | NVDA | $85.53 | $93.23 | take-profit | 9 | +92.53 |
| 24 | NVDA | $88.20 | $96.15 | take-profit | 5 | +93.43 |
| 25 | NVDA | $94.73 | $89.05 | stop-loss | 2 | -62.76 |
| 26 | NVDA | $95.11 | $103.68 | take-profit | 2 | +93.66 |
| 27 | NVDA | $114.50 | $107.63 | stop-loss | 2 | -62.96 |
| 28 | NVDA | $122.09 | $133.08 | take-profit | 8 | +93.88 |
| 29 | NVDA | $124.85 | $136.10 | take-profit | 5 | +94.81 |
| 30 | NVDA | $130.42 | $122.59 | stop-loss | 2 | -63.75 |
| 31 | NVDA | $123.65 | $134.78 | take-profit | 9 | +95.05 |
| 32 | NVDA | $125.48 | $117.95 | stop-loss | 8 | -63.94 |
| 33 | NVDA | $128.88 | $121.15 | stop-loss | 3 | -63.53 |
| 34 | SPY | $495.08 | $504.86 | time exit (10 days) | 10 | +20.79 |
| 35 | SPY | $498.15 | $503.96 | time exit (10 days) | 10 | +12.30 |
| 36 | SPY | $504.86 | $504.43 | time exit (10 days) | 10 | -0.91 |
| 37 | SPY | $503.96 | $489.09 | time exit (10 days) | 10 | -31.15 |
| 38 | SPY | $504.43 | $491.15 | time exit (10 days) | 10 | -27.70 |
| 39 | SPY | $516.12 | $519.34 | time exit (10 days) | 10 | +6.55 |
| 40 | SPY | $511.01 | $525.83 | time exit (10 days) | 10 | +30.46 |
| 41 | SPY | $519.34 | $531.31 | time exit (10 days) | 10 | +24.29 |
| 42 | SPY | $525.83 | $532.41 | time exit (10 days) | 10 | +13.20 |
| 43 | SPY | $531.31 | $540.47 | time exit (10 days) | 10 | +18.22 |
| 44 | SPY | $532.41 | $545.68 | time exit (10 days) | 10 | +26.39 |
| 45 | SPY | $540.47 | $534.97 | time exit (10 days) | 10 | -10.81 |
| 46 | SPY | $545.68 | $530.53 | time exit (10 days) | 10 | -29.45 |
| 47 | AMZN | $179.71 | $185.67 | time exit (10 days) | 10 | +35.08 |
| 48 | AMZN | $180.69 | $183.32 | time exit (10 days) | 10 | +15.45 |
| 49 | AMZN | $185.67 | $174.53 | stop-loss | 8 | -63.76 |
| 50 | AMZN | $183.32 | $172.32 | stop-loss | 7 | -63.38 |
| 51 | AMZN | $188.76 | $183.15 | time exit (10 days) | 10 | -31.21 |
| 52 | AMZN | $187.07 | $182.02 | time exit (10 days) | 10 | -28.26 |
| 53 | AMZN | $197.85 | $194.49 | time exit (10 days) | 10 | -17.73 |
| 54 | AMZN | $200.00 | $188.00 | stop-loss | 8 | -62.54 |
| 55 | AMZN | $194.49 | $182.82 | stop-loss | 4 | -62.16 |
| 56 | GOOGL | $153.10 | $152.94 | time exit (10 days) | 10 | -1.10 |
| 57 | GOOGL | $155.12 | $156.77 | time exit (10 days) | 10 | +10.93 |
| 58 | GOOGL | $152.94 | $166.71 | take-profit | 8 | +92.77 |
| 59 | GOOGL | $156.77 | $170.89 | take-profit | 3 | +93.69 |
| 60 | GOOGL | $161.25 | $168.73 | time exit (10 days) | 10 | +48.71 |
| 61 | GOOGL | $169.64 | $176.17 | time exit (10 days) | 10 | +40.61 |
| 62 | GOOGL | $168.73 | $174.24 | time exit (10 days) | 10 | +34.53 |
| 63 | GOOGL | $176.17 | $173.76 | time exit (10 days) | 10 | -14.55 |
| 64 | GOOGL | $174.24 | $176.32 | time exit (10 days) | 10 | +12.65 |
| 65 | GOOGL | $173.76 | $174.84 | time exit (10 days) | 10 | +6.62 |
| 66 | GOOGL | $176.32 | $183.87 | time exit (10 days) | 10 | +45.51 |
| 67 | GOOGL | $174.84 | $189.02 | time exit (10 days) | 10 | +86.53 |
| 68 | GOOGL | $183.87 | $183.54 | time exit (10 days) | 10 | -1.95 |
| 69 | GOOGL | $189.02 | $177.68 | stop-loss | 9 | -64.51 |
| 70 | GOOGL | $183.54 | $172.52 | stop-loss | 8 | -64.15 |
| 71 | META | $492.79 | $493.17 | time exit (10 days) | 10 | +0.82 |
| 72 | META | $498.78 | $512.54 | time exit (10 days) | 10 | +29.32 |
| 73 | META | $493.17 | $495.54 | time exit (10 days) | 10 | +5.11 |
| 74 | META | $512.54 | $481.79 | stop-loss | 8 | -63.95 |
| 75 | META | $497.96 | $535.89 | time exit (10 days) | 10 | +80.70 |
| 76 | META | $515.69 | $495.15 | time exit (10 days) | 10 | -42.52 |
| 77 | META | $535.89 | $503.73 | stop-loss | 5 | -63.81 |
| 78 | TSLA | $186.60 | $175.40 | stop-loss | 2 | -63.44 |
| 79 | TSLA | $177.29 | $193.25 | take-profit | 9 | +94.58 |
| 80 | TSLA | $181.57 | $197.91 | take-profit | 5 | +95.40 |
| 81 | TSLA | $197.42 | $215.20 | take-profit | 3 | +96.33 |
| 82 | TSLA | $251.52 | $236.43 | stop-loss | 5 | -64.75 |
| 83 | TSLA | $248.23 | $233.34 | stop-loss | 8 | -64.35 |
| 84 | TSLA | $239.20 | $224.85 | stop-loss | 3 | -63.97 |
| 85 | TSLA | $216.12 | $203.15 | stop-loss | 8 | -63.61 |
| 86 | JPM | $177.77 | $183.94 | time exit (10 days) | 10 | +36.55 |
| 87 | JPM | $181.90 | $187.75 | time exit (10 days) | 10 | +34.01 |
| 88 | JPM | $183.94 | $187.22 | time exit (10 days) | 10 | +18.92 |
| 89 | JPM | $187.75 | $176.49 | stop-loss | 8 | -63.74 |
| 90 | JPM | $187.22 | $175.99 | stop-loss | 3 | -63.37 |
| 91 | JPM | $182.47 | $182.10 | time exit (10 days) | 10 | -2.11 |
| 92 | JPM | $182.09 | $191.36 | time exit (10 days) | 10 | +53.46 |
| 93 | JPM | $189.47 | $187.33 | time exit (10 days) | 10 | -11.94 |
| 94 | JPM | $188.14 | $181.89 | time exit (10 days) | 10 | -34.98 |
| 95 | JPM | $188.67 | $195.56 | time exit (10 days) | 10 | +38.37 |
| 96 | JPM | $189.14 | $195.70 | time exit (10 days) | 10 | +36.55 |
| 97 | JPM | $195.56 | $200.32 | time exit (10 days) | 10 | +25.76 |
| 98 | JPM | $195.70 | $202.67 | time exit (10 days) | 10 | +37.77 |
| 99 | JPM | $200.32 | $188.30 | stop-loss | 10 | -63.86 |
| 100 | JPM | $202.67 | $190.51 | stop-loss | 5 | -63.47 |
| 101 | JPM | $204.32 | $214.66 | time exit (10 days) | 10 | +53.19 |
| 102 | JNJ | $150.37 | $144.77 | time exit (10 days) | 10 | -39.38 |
| 103 | JNJ | $145.44 | $154.32 | time exit (10 days) | 10 | +64.28 |
| 104 | JNJ | $151.03 | $151.02 | time exit (10 days) | 10 | -0.10 |
| 105 | JNJ | $154.32 | $149.86 | time exit (10 days) | 10 | -30.64 |
| 106 | JNJ | $151.02 | $154.32 | time exit (10 days) | 10 | +23.11 |
| 107 | JNJ | $149.86 | $157.13 | time exit (10 days) | 10 | +51.36 |
| 108 | BTC-USD | $68,330.41 | $64,230.59 | stop-loss | 1 | -63.55 |
| 109 | BTC-USD | $68,498.88 | $64,388.95 | stop-loss | 10 | -63.29 |
| 110 | BTC-USD | $71,396.59 | $67,112.80 | stop-loss | 1 | -62.97 |
| 111 | BTC-USD | $69,892.83 | $65,699.26 | stop-loss | 4 | -62.48 |
| 112 | BTC-USD | $71,631.36 | $67,333.48 | stop-loss | 4 | -61.89 |
| 113 | BTC-USD | $68,296.22 | $69,342.59 | time exit (10 days) | 10 | +15.80 |
| 114 | BTC-USD | $67,751.60 | $68,241.19 | time exit (10 days) | 10 | +7.44 |
| 115 | BTC-USD | $69,342.59 | $65,182.03 | stop-loss | 7 | -61.99 |
| 116 | ETH-USD | $3,630.43 | $3,412.61 | stop-loss | 1 | -61.69 |
| 117 | ETH-USD | $3,915.42 | $3,680.49 | stop-loss | 6 | -61.32 |
| 118 | ETH-USD | $3,883.14 | $3,650.15 | stop-loss | 1 | -60.95 |
| 119 | ETH-USD | $3,840.26 | $3,678.63 | time exit (10 days) | 10 | -42.49 |
| 120 | ETH-USD | $3,780.90 | $3,554.04 | stop-loss | 9 | -60.32 |

### FRESH-2 — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $185.75 | $187.66 | time exit (10 days) | 10 | +10.31 |
| 2 | AAPL | $189.01 | $191.93 | time exit (10 days) | 10 | +15.49 |
| 3 | AAPL | $187.66 | $195.72 | time exit (10 days) | 10 | +43.05 |
| 4 | AAPL | $191.93 | $192.34 | time exit (10 days) | 10 | +2.15 |
| 5 | AAPL | $195.72 | $190.21 | time exit (10 days) | 10 | -28.37 |
| 6 | AAPL | $192.34 | $180.80 | stop-loss | 8 | -60.23 |
| 7 | MSFT | $332.87 | $354.89 | time exit (10 days) | 10 | +66.02 |
| 8 | MSFT | $338.15 | $361.94 | time exit (10 days) | 10 | +70.69 |
| 9 | MSFT | $354.89 | $369.95 | time exit (10 days) | 10 | +42.95 |
| 10 | MSFT | $361.94 | $370.99 | time exit (10 days) | 10 | +25.40 |
| 11 | MSFT | $369.95 | $363.20 | time exit (10 days) | 10 | -18.59 |
| 12 | MSFT | $370.99 | $358.28 | time exit (10 days) | 10 | -34.84 |
| 13 | MSFT | $368.18 | $382.11 | time exit (10 days) | 10 | +38.34 |
| 14 | MSFT | $366.86 | $390.56 | time exit (10 days) | 10 | +65.72 |
| 15 | MSFT | $382.11 | $400.05 | time exit (10 days) | 10 | +48.06 |
| 16 | MSFT | $390.56 | $397.01 | time exit (10 days) | 10 | +16.98 |
| 17 | MSFT | $400.05 | $397.83 | time exit (10 days) | 10 | -5.72 |
| 18 | MSFT | $397.01 | $394.50 | time exit (10 days) | 10 | -6.52 |
| 19 | MSFT | $397.83 | $399.94 | time exit (10 days) | 10 | +5.47 |
| 20 | NVDA | $48.74 | $46.63 | time exit (10 days) | 10 | -44.62 |
| 21 | NVDA | $48.57 | $45.66 | stop-loss | 7 | -61.44 |
| 22 | NVDA | $48.21 | $49.38 | time exit (10 days) | 10 | +24.72 |
| 23 | NVDA | $48.85 | $52.10 | time exit (10 days) | 10 | +68.00 |
| 24 | NVDA | $49.38 | $53.82 | take-profit | 6 | +92.49 |
| 25 | NVDA | $52.10 | $56.79 | take-profit | 7 | +93.36 |
| 26 | NVDA | $56.22 | $61.28 | take-profit | 6 | +94.24 |
| 27 | NVDA | $59.70 | $65.07 | take-profit | 8 | +95.02 |
| 28 | NVDA | $62.59 | $68.23 | take-profit | 4 | +95.99 |
| 29 | NVDA | $68.03 | $74.16 | take-profit | 4 | +96.97 |
| 30 | NVDA | $71.92 | $67.60 | stop-loss | 4 | -65.17 |
| 31 | SPY | $438.82 | $441.92 | time exit (10 days) | 10 | +7.61 |
| 32 | SPY | $440.15 | $455.21 | time exit (10 days) | 10 | +36.92 |
| 33 | SPY | $441.92 | $457.72 | time exit (10 days) | 10 | +38.73 |
| 34 | SPY | $455.21 | $460.25 | time exit (10 days) | 10 | +12.04 |
| 35 | SPY | $457.72 | $459.56 | time exit (10 days) | 10 | +4.37 |
| 36 | SPY | $460.25 | $459.88 | time exit (10 days) | 10 | -0.87 |
| 37 | SPY | $459.56 | $469.50 | time exit (10 days) | 10 | +23.54 |
| 38 | SPY | $459.88 | $475.33 | time exit (10 days) | 10 | +36.64 |
| 39 | SPY | $469.50 | $478.33 | time exit (10 days) | 10 | +20.59 |
| 40 | SPY | $475.33 | $478.42 | time exit (10 days) | 10 | +7.12 |
| 41 | SPY | $478.33 | $481.45 | time exit (10 days) | 10 | +7.16 |
| 42 | SPY | $478.42 | $490.22 | time exit (10 days) | 10 | +27.07 |
| 43 | AMZN | $144.85 | $136.16 | stop-loss | 4 | -66.03 |
| 44 | AMZN | $143.20 | $146.09 | time exit (10 days) | 10 | +22.08 |
| 45 | AMZN | $146.71 | $146.88 | time exit (10 days) | 10 | +1.27 |
| 46 | AMZN | $146.09 | $147.42 | time exit (10 days) | 10 | +9.98 |
| 47 | AMZN | $146.88 | $153.84 | time exit (10 days) | 10 | +52.00 |
| 48 | AMZN | $147.42 | $151.94 | time exit (10 days) | 10 | +33.81 |
| 49 | AMZN | $153.84 | $144.61 | stop-loss | 8 | -66.36 |
| 50 | AMZN | $151.94 | $153.16 | time exit (10 days) | 10 | +8.83 |
| 51 | AMZN | $153.16 | $159.00 | time exit (10 days) | 10 | +41.95 |
| 52 | AMZN | $156.02 | $170.07 | take-profit | 8 | +99.46 |
| 53 | AMZN | $159.00 | $173.31 | take-profit | 8 | +100.29 |
| 54 | AMZN | $169.15 | $168.59 | time exit (10 days) | 10 | -3.72 |
| 55 | AMZN | $168.64 | $173.16 | time exit (10 days) | 10 | +30.13 |
| 56 | GOOGL | $135.42 | $127.30 | stop-loss | 9 | -67.59 |
| 57 | GOOGL | $133.97 | $136.66 | time exit (10 days) | 10 | +22.53 |
| 58 | GOOGL | $139.23 | $130.87 | stop-loss | 10 | -67.37 |
| 59 | GOOGL | $136.66 | $128.46 | stop-loss | 5 | -66.95 |
| 60 | GOOGL | $135.64 | $139.10 | time exit (10 days) | 10 | +28.30 |
| 61 | GOOGL | $139.10 | $137.53 | time exit (10 days) | 10 | -12.52 |
| 62 | GOOGL | $138.37 | $141.15 | time exit (10 days) | 10 | +22.29 |
| 63 | GOOGL | $137.53 | $145.65 | time exit (10 days) | 10 | +65.70 |
| 64 | GOOGL | $141.15 | $150.03 | time exit (10 days) | 10 | +70.45 |
| 65 | GOOGL | $145.65 | $136.91 | stop-loss | 8 | -67.63 |
| 66 | GOOGL | $150.03 | $141.03 | stop-loss | 1 | -67.19 |
| 67 | META | $302.68 | $313.96 | time exit (10 days) | 10 | +41.48 |
| 68 | META | $324.71 | $305.23 | stop-loss | 7 | -67.02 |
| 69 | META | $313.96 | $295.13 | stop-loss | 6 | -66.61 |
| 70 | META | $316.75 | $338.25 | time exit (10 days) | 10 | +74.94 |
| 71 | META | $329.55 | $324.05 | time exit (10 days) | 10 | -18.56 |
| 72 | META | $338.25 | $317.96 | stop-loss | 6 | -66.55 |
| 73 | META | $330.01 | $350.60 | time exit (10 days) | 10 | +68.81 |
| 74 | META | $350.73 | $355.26 | time exit (10 days) | 10 | +14.33 |
| 75 | META | $350.60 | $363.97 | time exit (10 days) | 10 | +42.37 |
| 76 | META | $355.26 | $381.55 | time exit (10 days) | 10 | +82.55 |
| 77 | META | $363.97 | $396.73 | take-profit | 9 | +101.12 |
| 78 | META | $381.55 | $415.89 | take-profit | 8 | +102.05 |
| 79 | META | $396.26 | $431.93 | take-profit | 3 | +102.96 |
| 80 | META | $450.41 | $464.08 | time exit (10 days) | 10 | +35.04 |
| 81 | META | $455.75 | $479.94 | time exit (10 days) | 10 | +61.43 |
| 82 | TSLA | $262.59 | $246.83 | stop-loss | 2 | -69.85 |
| 83 | TSLA | $261.16 | $245.49 | stop-loss | 10 | -69.41 |
| 84 | TSLA | $262.99 | $247.21 | stop-loss | 4 | -69.00 |
| 85 | TSLA | $242.64 | $254.50 | time exit (10 days) | 10 | +55.87 |
| 86 | TSLA | $251.05 | $248.48 | time exit (10 days) | 10 | -11.76 |
| 87 | TSLA | $254.50 | $239.23 | stop-loss | 7 | -68.85 |
| 88 | TSLA | $248.48 | $233.57 | stop-loss | 6 | -68.44 |
| 89 | JPM | $143.88 | $147.13 | time exit (10 days) | 10 | +25.62 |
| 90 | JPM | $146.46 | $153.88 | time exit (10 days) | 10 | +57.58 |
| 91 | JPM | $147.13 | $157.18 | time exit (10 days) | 10 | +78.05 |
| 92 | JPM | $153.88 | $159.61 | time exit (10 days) | 10 | +42.81 |
| 93 | JPM | $157.18 | $162.41 | time exit (10 days) | 10 | +38.44 |
| 94 | JPM | $159.61 | $158.61 | time exit (10 days) | 10 | -7.29 |
| 95 | JPM | $162.41 | $159.55 | time exit (10 days) | 10 | -20.39 |
| 96 | JPM | $166.42 | $164.53 | time exit (10 days) | 10 | -13.15 |
| 97 | JPM | $165.32 | $170.80 | time exit (10 days) | 10 | +38.25 |
| 98 | JPM | $164.53 | $174.08 | time exit (10 days) | 10 | +67.22 |
| 99 | JNJ | $145.20 | $145.08 | time exit (10 days) | 10 | -1.00 |
| 100 | JNJ | $145.08 | $148.58 | time exit (10 days) | 10 | +28.06 |
| 101 | JNJ | $149.52 | $147.93 | time exit (10 days) | 10 | -12.39 |
| 102 | JNJ | $148.58 | $146.96 | time exit (10 days) | 10 | -12.73 |
| 103 | BTC-USD | $27,983.75 | $26,873.32 | time exit (10 days) | 10 | -46.19 |
| 104 | BTC-USD | $27,946.60 | $28,519.47 | time exit (10 days) | 10 | +23.77 |
| 105 | BTC-USD | $28,519.47 | $31,086.22 | take-profit | 7 | +104.47 |
| 106 | BTC-USD | $29,918.41 | $32,611.07 | take-profit | 2 | +105.55 |
| 107 | BTC-USD | $34,156.65 | $35,049.36 | time exit (10 days) | 10 | +30.89 |
| 108 | BTC-USD | $34,667.78 | $37,787.89 | take-profit | 9 | +106.71 |
| 109 | BTC-USD | $35,049.36 | $37,880.58 | time exit (10 days) | 10 | +96.54 |
| 110 | BTC-USD | $37,313.97 | $35,075.13 | stop-loss | 4 | -72.31 |
| 111 | BTC-USD | $37,880.58 | $35,607.75 | stop-loss | 1 | -71.82 |
| 112 | BTC-USD | $37,476.96 | $37,712.75 | time exit (10 days) | 10 | +7.50 |
| 113 | BTC-USD | $37,796.79 | $41,198.50 | take-profit | 9 | +107.15 |
| 114 | BTC-USD | $37,712.75 | $41,106.90 | take-profit | 4 | +108.27 |
| 115 | BTC-USD | $44,080.65 | $41,435.81 | stop-loss | 6 | -72.73 |
| 116 | BTC-USD | $43,779.70 | $41,152.92 | stop-loss | 1 | -72.24 |
| 117 | BTC-USD | $41,929.76 | $43,613.14 | time exit (10 days) | 10 | +48.14 |
| 118 | BTC-USD | $43,652.25 | $42,156.90 | time exit (10 days) | 10 | -41.27 |
| 119 | BTC-USD | $43,613.14 | $40,996.35 | stop-loss | 9 | -71.96 |
| 120 | BTC-USD | $44,179.92 | $48,156.11 | take-profit | 7 | +107.36 |
| 121 | BTC-USD | $46,139.73 | $43,371.35 | stop-loss | 3 | -72.25 |
| 122 | BTC-USD | $49,742.44 | $50,731.95 | time exit (10 days) | 10 | +23.75 |
| 123 | BTC-USD | $52,122.55 | $56,813.59 | take-profit | 9 | +107.89 |
| 124 | ETH-USD | $1,816.46 | $1,979.95 | take-profit | 9 | +108.93 |
| 125 | ETH-USD | $1,894.16 | $2,064.63 | take-profit | 4 | +109.90 |
| 126 | ETH-USD | $2,078.29 | $1,953.59 | stop-loss | 4 | -73.93 |
| 127 | ETH-USD | $2,060.41 | $1,936.78 | stop-loss | 2 | -73.48 |
| 128 | ETH-USD | $2,022.24 | $2,052.56 | time exit (10 days) | 10 | +18.25 |
| 129 | ETH-USD | $2,084.41 | $2,272.01 | take-profit | 9 | +109.73 |
| 130 | ETH-USD | $2,052.56 | $2,237.30 | take-profit | 4 | +110.74 |
| 131 | ETH-USD | $2,293.84 | $2,156.21 | stop-loss | 8 | -74.47 |
| 132 | ETH-USD | $2,352.46 | $2,211.31 | stop-loss | 1 | -74.03 |
| 133 | ETH-USD | $2,219.34 | $2,272.56 | time exit (10 days) | 10 | +29.41 |
| 134 | ETH-USD | $2,272.56 | $2,136.21 | stop-loss | 9 | -73.77 |
| 135 | ETH-USD | $2,292.07 | $2,154.54 | stop-loss | 4 | -73.31 |
| 136 | ETH-USD | $2,344.83 | $2,555.86 | take-profit | 1 | +109.32 |
| 137 | ETH-USD | $2,472.24 | $2,323.91 | stop-loss | 8 | -73.53 |
| 138 | ETH-USD | $2,489.50 | $2,340.13 | stop-loss | 3 | -73.09 |
| 139 | ETH-USD | $2,879.00 | $3,138.11 | take-profit | 8 | +108.98 |

### FRESH-3 — wide-6

| # | Symbol | Entry | Exit | Reason | Days | P&L ($) |
|---:|---|---|---|---|---:|---:|
| 1 | AAPL | $152.51 | $162.26 | time exit (10 days) | 10 | +63.90 |
| 2 | AAPL | $157.68 | $159.43 | time exit (10 days) | 10 | +11.17 |
| 3 | AAPL | $162.26 | $162.58 | time exit (10 days) | 10 | +2.01 |
| 4 | AAPL | $159.43 | $162.68 | time exit (10 days) | 10 | +20.53 |
| 5 | AAPL | $162.58 | $166.87 | time exit (10 days) | 10 | +26.64 |
| 6 | AAPL | $162.68 | $170.72 | time exit (10 days) | 10 | +50.04 |
| 7 | AAPL | $166.87 | $169.54 | time exit (10 days) | 10 | +16.28 |
| 8 | AAPL | $170.72 | $171.64 | time exit (10 days) | 10 | +5.51 |
| 9 | AAPL | $169.54 | $174.70 | time exit (10 days) | 10 | +31.00 |
| 10 | AAPL | $171.64 | $176.58 | time exit (10 days) | 10 | +29.41 |
| 11 | AAPL | $174.70 | $180.62 | time exit (10 days) | 10 | +34.77 |
| 12 | AAPL | $176.58 | $181.26 | time exit (10 days) | 10 | +27.27 |
| 13 | AAPL | $180.62 | $186.47 | time exit (10 days) | 10 | +33.42 |
| 14 | AAPL | $181.26 | $189.00 | time exit (10 days) | 10 | +44.20 |
| 15 | AAPL | $186.47 | $187.74 | time exit (10 days) | 10 | +7.07 |
| 16 | AAPL | $189.00 | $190.30 | time exit (10 days) | 10 | +7.18 |
| 17 | AAPL | $187.74 | $190.38 | time exit (10 days) | 10 | +14.62 |
| 18 | AAPL | $190.30 | $188.36 | time exit (10 days) | 10 | -10.60 |
| 19 | AAPL | $190.38 | $178.96 | stop-loss | 7 | -62.49 |
| 20 | MSFT | $271.86 | $280.49 | time exit (10 days) | 10 | +32.85 |
| 21 | MSFT | $272.97 | $281.55 | time exit (10 days) | 10 | +32.63 |
| 22 | MSFT | $280.49 | $280.98 | time exit (10 days) | 10 | +1.81 |
| 23 | MSFT | $281.55 | $274.14 | time exit (10 days) | 10 | -27.44 |
| 24 | MSFT | $280.98 | $297.29 | time exit (10 days) | 10 | +60.32 |
| 25 | MSFT | $297.29 | $301.08 | time exit (10 days) | 10 | +13.34 |
| 26 | MSFT | $300.29 | $313.17 | time exit (10 days) | 10 | +44.88 |
| 27 | MSFT | $301.08 | $322.95 | time exit (10 days) | 10 | +76.34 |
| 28 | MSFT | $313.17 | $325.35 | time exit (10 days) | 10 | +41.19 |
| 29 | MSFT | $322.95 | $325.95 | time exit (10 days) | 10 | +9.88 |
| 30 | MSFT | $325.35 | $325.24 | time exit (10 days) | 10 | -0.38 |
| 31 | MSFT | $325.95 | $327.47 | time exit (10 days) | 10 | +4.96 |
| 32 | MSFT | $325.24 | $332.76 | time exit (10 days) | 10 | +24.61 |
| 33 | MSFT | $327.47 | $334.11 | time exit (10 days) | 10 | +21.63 |
| 34 | MSFT | $332.76 | $338.22 | time exit (10 days) | 10 | +17.55 |
| 35 | MSFT | $334.11 | $322.47 | time exit (10 days) | 10 | -37.30 |
| 36 | MSFT | $338.22 | $317.92 | stop-loss | 10 | -64.02 |
| 37 | NVDA | $25.64 | $27.69 | time exit (10 days) | 10 | +84.63 |
| 38 | NVDA | $26.69 | $27.49 | time exit (10 days) | 10 | +31.86 |
| 39 | NVDA | $27.69 | $26.92 | time exit (10 days) | 10 | -29.78 |
| 40 | NVDA | $27.49 | $26.96 | time exit (10 days) | 10 | -20.68 |
| 41 | NVDA | $26.92 | $28.82 | time exit (10 days) | 10 | +75.46 |
| 42 | NVDA | $28.82 | $28.86 | time exit (10 days) | 10 | +1.55 |
| 43 | NVDA | $29.06 | $31.67 | take-profit | 8 | +96.58 |
| 44 | NVDA | $28.86 | $31.46 | take-profit | 3 | +97.64 |
| 45 | NVDA | $31.08 | $33.88 | take-profit | 3 | +98.68 |
| 46 | NVDA | $39.98 | $37.59 | stop-loss | 6 | -66.11 |
| 47 | NVDA | $38.53 | $42.00 | take-profit | 6 | +98.78 |
| 48 | NVDA | $40.90 | $40.99 | time exit (10 days) | 10 | +2.53 |
| 49 | NVDA | $42.91 | $40.34 | stop-loss | 3 | -66.42 |
| 50 | NVDA | $40.99 | $44.69 | take-profit | 10 | +99.34 |
| 51 | NVDA | $41.97 | $45.75 | take-profit | 5 | +99.93 |
| 52 | NVDA | $45.84 | $45.76 | time exit (10 days) | 10 | -1.87 |
| 53 | NVDA | $45.38 | $44.38 | time exit (10 days) | 10 | -24.71 |
| 54 | NVDA | $45.76 | $43.01 | stop-loss | 9 | -67.19 |
| 55 | SPY | $396.33 | $397.83 | time exit (10 days) | 10 | +4.21 |
| 56 | SPY | $395.07 | $395.18 | time exit (10 days) | 10 | +0.30 |
| 57 | SPY | $397.83 | $395.44 | time exit (10 days) | 10 | -6.69 |
| 58 | SPY | $395.18 | $400.97 | time exit (10 days) | 10 | +16.28 |
| 59 | SPY | $395.44 | $402.30 | time exit (10 days) | 10 | +19.31 |
| 60 | SPY | $400.97 | $409.82 | time exit (10 days) | 10 | +24.60 |
| 61 | SPY | $402.30 | $418.08 | time exit (10 days) | 10 | +43.81 |
| 62 | SPY | $409.82 | $417.98 | time exit (10 days) | 10 | +22.33 |
| 63 | SPY | $418.08 | $419.38 | time exit (10 days) | 10 | +3.49 |
| 64 | SPY | $417.98 | $422.52 | time exit (10 days) | 10 | +12.20 |
| 65 | SPY | $419.38 | $432.03 | time exit (10 days) | 10 | +33.96 |
| 66 | SPY | $422.52 | $434.55 | time exit (10 days) | 10 | +32.14 |
| 67 | SPY | $432.03 | $434.85 | time exit (10 days) | 10 | +7.38 |
| 68 | SPY | $434.55 | $431.34 | time exit (10 days) | 10 | -8.37 |
| 69 | SPY | $434.85 | $428.52 | time exit (10 days) | 10 | -16.47 |
| 70 | AMZN | $102.17 | $106.21 | time exit (10 days) | 10 | +44.70 |
| 71 | AMZN | $102.74 | $102.05 | time exit (10 days) | 10 | -7.62 |
| 72 | AMZN | $106.21 | $105.83 | time exit (10 days) | 10 | -4.06 |
| 73 | AMZN | $105.83 | $115.36 | take-profit | 7 | +102.08 |
| 74 | AMZN | $111.20 | $121.21 | take-profit | 9 | +102.97 |
| 75 | AMZN | $115.01 | $125.37 | take-profit | 8 | +103.96 |
| 76 | AMZN | $121.66 | $126.66 | time exit (10 days) | 10 | +47.86 |
| 77 | AMZN | $126.61 | $124.83 | time exit (10 days) | 10 | -16.44 |
| 78 | AMZN | $126.66 | $129.04 | time exit (10 days) | 10 | +21.94 |
| 79 | AMZN | $124.83 | $128.36 | time exit (10 days) | 10 | +33.08 |
| 80 | AMZN | $129.04 | $134.30 | time exit (10 days) | 10 | +47.82 |
| 81 | AMZN | $128.36 | $129.96 | time exit (10 days) | 10 | +14.68 |
| 82 | AMZN | $134.30 | $126.24 | stop-loss | 9 | -70.78 |
| 83 | AMZN | $138.56 | $131.84 | time exit (10 days) | 10 | -56.86 |
| 84 | GOOGL | $102.75 | $104.97 | time exit (10 days) | 10 | +25.18 |
| 85 | GOOGL | $105.44 | $104.97 | time exit (10 days) | 10 | -5.18 |
| 86 | GOOGL | $104.97 | $106.19 | time exit (10 days) | 10 | +13.57 |
| 87 | GOOGL | $104.97 | $106.75 | time exit (10 days) | 10 | +19.83 |
| 88 | GOOGL | $106.19 | $115.75 | take-profit | 8 | +105.52 |
| 89 | GOOGL | $106.75 | $116.37 | take-profit | 3 | +106.52 |
| 90 | GOOGL | $115.41 | $122.50 | time exit (10 days) | 10 | +73.28 |
| 91 | GOOGL | $123.87 | $126.11 | time exit (10 days) | 10 | +21.70 |
| 92 | GOOGL | $122.50 | $122.66 | time exit (10 days) | 10 | +1.53 |
| 93 | GOOGL | $126.11 | $119.41 | time exit (10 days) | 10 | -63.91 |
| 94 | GOOGL | $122.66 | $115.30 | stop-loss | 9 | -71.82 |
| 95 | GOOGL | $123.37 | $128.18 | time exit (10 days) | 10 | +46.41 |
| 96 | GOOGL | $127.24 | $128.70 | time exit (10 days) | 10 | +13.71 |
| 97 | GOOGL | $128.47 | $128.56 | time exit (10 days) | 10 | +0.86 |
| 98 | GOOGL | $128.70 | $134.89 | time exit (10 days) | 10 | +57.54 |
| 99 | META | $193.75 | $209.93 | time exit (10 days) | 10 | +100.28 |
| 100 | META | $204.06 | $212.71 | time exit (10 days) | 10 | +51.37 |
| 101 | META | $209.93 | $216.78 | time exit (10 days) | 10 | +39.69 |
| 102 | META | $212.71 | $210.77 | time exit (10 days) | 10 | -11.14 |
| 103 | META | $216.78 | $236.29 | take-profit | 8 | +109.70 |
| 104 | META | $240.87 | $236.59 | time exit (10 days) | 10 | -21.87 |
| 105 | META | $231.06 | $245.96 | time exit (10 days) | 10 | +79.20 |
| 106 | META | $236.59 | $257.89 | take-profit | 9 | +111.24 |
| 107 | META | $245.96 | $268.10 | take-profit | 7 | +112.22 |
| 108 | META | $260.03 | $268.75 | time exit (10 days) | 10 | +42.20 |
| 109 | META | $268.55 | $278.97 | time exit (10 days) | 10 | +48.99 |
| 110 | META | $268.75 | $282.58 | time exit (10 days) | 10 | +65.24 |
| 111 | META | $278.97 | $289.22 | time exit (10 days) | 10 | +46.81 |
| 112 | META | $282.58 | $308.02 | take-profit | 10 | +115.09 |
| 113 | META | $289.22 | $315.25 | take-profit | 9 | +116.10 |
| 114 | META | $310.44 | $291.81 | stop-loss | 6 | -78.10 |
| 115 | META | $299.65 | $310.22 | time exit (10 days) | 10 | +45.64 |
| 116 | META | $308.75 | $302.84 | time exit (10 days) | 10 | -24.87 |
| 117 | META | $310.22 | $291.61 | stop-loss | 9 | -77.74 |
| 118 | TSLA | $190.41 | $207.55 | take-profit | 5 | +115.96 |
| 119 | TSLA | $221.31 | $241.23 | take-profit | 3 | +116.99 |
| 120 | TSLA | $258.71 | $243.19 | stop-loss | 8 | -78.67 |
| 121 | TSLA | $259.46 | $243.89 | stop-loss | 3 | -78.23 |
| 122 | TSLA | $256.24 | $279.30 | take-profit | 3 | +116.61 |
| 123 | TSLA | $276.54 | $262.90 | time exit (10 days) | 10 | -64.49 |
| 124 | TSLA | $277.90 | $261.23 | stop-loss | 5 | -78.04 |
| 125 | JPM | $130.63 | $122.79 | stop-loss | 3 | -77.60 |
| 126 | JPM | $127.70 | $128.91 | time exit (10 days) | 10 | +12.22 |
| 127 | JPM | $127.17 | $131.39 | time exit (10 days) | 10 | +42.71 |
| 128 | JPM | $128.91 | $131.66 | time exit (10 days) | 10 | +27.56 |
| 129 | JPM | $131.39 | $128.21 | time exit (10 days) | 10 | -31.28 |
| 130 | JPM | $131.66 | $133.40 | time exit (10 days) | 10 | +17.01 |
| 131 | JPM | $133.40 | $145.41 | take-profit | 10 | +116.36 |
| 132 | JPM | $138.67 | $145.33 | time exit (10 days) | 10 | +62.62 |
| 133 | JPM | $145.45 | $145.64 | time exit (10 days) | 10 | +1.70 |
| 134 | JPM | $145.33 | $143.04 | time exit (10 days) | 10 | -20.65 |
| 135 | JPM | $145.64 | $138.45 | time exit (10 days) | 10 | -64.57 |
| 136 | JNJ | $149.90 | $148.03 | time exit (10 days) | 10 | -16.27 |
| 137 | JNJ | $148.10 | $146.86 | time exit (10 days) | 10 | -10.91 |
| 138 | JNJ | $148.03 | $144.37 | time exit (10 days) | 10 | -32.13 |
| 139 | JNJ | $148.56 | $144.78 | time exit (10 days) | 10 | -33.01 |
| 140 | JNJ | $153.51 | $155.57 | time exit (10 days) | 10 | +17.38 |
| 141 | JNJ | $158.35 | $156.96 | time exit (10 days) | 10 | -11.33 |
| 142 | JNJ | $155.57 | $158.64 | time exit (10 days) | 10 | +25.55 |
| 143 | JNJ | $156.96 | $150.51 | time exit (10 days) | 10 | -53.25 |
| 144 | JNJ | $158.64 | $149.12 | stop-loss | 4 | -77.42 |
| 145 | BTC-USD | $27,767.24 | $28,033.56 | time exit (10 days) | 10 | +12.28 |
| 146 | BTC-USD | $27,494.71 | $28,168.09 | time exit (10 days) | 10 | +31.38 |
| 147 | BTC-USD | $28,033.56 | $28,333.05 | time exit (10 days) | 10 | +13.75 |
| 148 | BTC-USD | $28,168.09 | $30,703.23 | take-profit | 10 | +115.86 |
| 149 | BTC-USD | $28,333.05 | $30,883.03 | take-profit | 5 | +116.79 |
| 150 | BTC-USD | $30,485.70 | $28,656.56 | stop-loss | 6 | -78.65 |
| 151 | BTC-USD | $29,248.49 | $27,493.58 | stop-loss | 9 | -78.09 |
| 152 | BTC-USD | $28,847.71 | $27,116.85 | stop-loss | 6 | -77.72 |
| 153 | BTC-USD | $30,086.25 | $30,292.54 | time exit (10 days) | 10 | +8.83 |
| 154 | BTC-USD | $31,156.44 | $31,476.05 | time exit (10 days) | 10 | +13.20 |
| 155 | BTC-USD | $30,292.54 | $29,856.56 | time exit (10 days) | 10 | -18.53 |
| 156 | BTC-USD | $31,476.05 | $29,587.49 | stop-loss | 5 | -77.24 |
| 157 | ETH-USD | $1,743.76 | $1,871.01 | time exit (10 days) | 10 | +93.46 |
| 158 | ETH-USD | $1,792.74 | $1,859.39 | time exit (10 days) | 10 | +47.96 |
| 159 | ETH-USD | $1,871.01 | $2,039.41 | take-profit | 10 | +116.55 |
| 160 | ETH-USD | $1,859.39 | $2,026.74 | take-profit | 5 | +117.60 |
| 161 | ETH-USD | $2,101.64 | $1,975.54 | stop-loss | 5 | -79.10 |
| 162 | ETH-USD | $1,936.40 | $1,820.22 | stop-loss | 5 | -78.62 |
| 163 | ETH-USD | $2,006.51 | $1,886.12 | stop-loss | 4 | -78.15 |

