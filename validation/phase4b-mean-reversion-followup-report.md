# VaultTec — Phase 4b Mean-Reversion Follow-Up Report

Generated: 2026-11-09T05:15:19.728577 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests a hypothesis on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Out-of-sample test of the Bollinger and RSI mean-reversion hypothesis from Phase 4: three earlier, non-overlapping 180-calendar-day windows ending before the Phase 4 window starts, delayed real market history from yfinance (free), 40 days of warm-up history before each window. Two variants per strategy per window — A: risk-managed validation (3% stop / 4.5% target / 10-day exit through the Risk Engine, $10,000 virtual cash, balanced profile, long-only); B: native backtest exactly as in backtest.py (RSI sell > 70, Bollinger sell at upper band, no fixed stop/target). Signals use history up to the trade day only — no look-ahead. The Phase 4 window is re-run and labelled in-sample.
- Data: yfinance (delayed real market data, free — Yahoo Finance)

## Pooled out-of-sample verdict (the headline test)

### RSI mean-reversion (buy RSI < 30, sell RSI > 70) — out-of-sample, 3 windows pooled

- Variant A (risk-managed, 3% stop / 4.5% target): 67 trades, 32 wins, 47.8% win rate, total paper P&L $341.61 (+1.14% across the 3 windows). Per window: {'OOS-1': 267.2, 'OOS-2': -398.34, 'OOS-3': 472.75}.
- Variant B (native backtest): 40 trades total, mean return per window {'OOS-1': 8.04, 'OOS-2': 12.16, 'OOS-3': 12.73}, mean of window means +10.98%, positive in 3 of 3 windows.

### Bollinger mean-reversion (buy lower band, sell upper band) — out-of-sample, 3 windows pooled

- Variant A (risk-managed, 3% stop / 4.5% target): 40 trades, 17 wins, 42.5% win rate, total paper P&L $27.76 (+0.09% across the 3 windows). Per window: {'OOS-1': 74.28, 'OOS-2': -238.19, 'OOS-3': 191.67}.
- Variant B (native backtest): 38 trades total, mean return per window {'OOS-1': 7.5, 'OOS-2': 24.5, 'OOS-3': 6.84}, mean of window means +12.95%, positive in 3 of 3 windows.

## Reading the two variants — why they disagree

Variant B (native backtest) and Variant A (risk-managed) test the same entries with different exits, and the exits are the whole story. Variant B has **no stop-loss**: it holds through whatever fall follows the entry until the exit signal (RSI > 70 or the upper band). In a falling window like OOS-2 that means riding prices down and back up again — the backtest still wins because prices eventually recovered, but it never records the fall in between: its drawdown is measured only on completed trades, and its 'mean total return' sums per-trade percentage moves with no position sizing, so one big crypto move (e.g. ETH +76.83% in OOS-2) counts the same as a whole portfolio. Variant A has a **3% stop**: in that same falling window it was stopped out 18 times out of 21 RSI trades (14.3% win rate) because prices kept falling past the stop before recovering. So the honest reading is: the mean-reversion *bounce* is real enough to show up in all three out-of-sample windows in Variant B, but the *risk-managed version of it* — the only version VaultTec is allowed to trade — is weak and regime-dependent, roughly break-even pooled. The next question is not 'does mean reversion work' but 'is there an exit that keeps the bounce and survives a falling market' — for example a wider stop, a time-based exit, or a trend filter that skips oversold buys while the market is in a downtrend. That is a new hypothesis to test, not a conclusion.

## OOS-1 — 2025-08-27 → 2026-02-23 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Variant A: 25 trades (25 triggers), 14 wins / 11 losses, 56.0% win rate, paper P&L $267.20 (+2.67%), avg win $43.09, avg loss $-30.56, max drawdown -0.74%, exits {'stop-loss': 11, 'take-profit': 13, 'time exit (10 days)': 1}, blocked by risk 0.
- Variant B: 15 trades, mean total return +8.04%, mean win rate 80.0%, mean max drawdown -4.12%, symbols with trades 10.
- Variant A per symbol: {'AAPL': 3, 'MSFT': 2, 'SPY': 1, 'AMZN': 1, 'GOOGL': 1, 'META': 4, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 7, 'ETH-USD': 4}
- Variant B per symbol: AAPL: 1 trades, +2.64%, 100.0% win; MSFT: 0 trades, +0.00%, 0.0% win; NVDA: 1 trades, +3.45%, 100.0% win; SPY: 1 trades, +3.48%, 100.0% win; AMZN: 2 trades, +26.53%, 100.0% win; GOOGL: 2 trades, +21.16%, 100.0% win; META: 2 trades, +13.05%, 50.0% win; TSLA: 1 trades, +16.22%, 100.0% win; JPM: 0 trades, +0.00%, 0.0% win; JNJ: 2 trades, +13.69%, 100.0% win; BTC-USD: 2 trades, +2.58%, 50.0% win; ETH-USD: 1 trades, -22.44%, 0.0% win

### Bollinger mean-reversion (buy lower band, sell upper band)

- Variant A: 15 trades (15 triggers), 7 wins / 8 losses, 46.7% win rate, paper P&L $74.28 (+0.74%), avg win $45.08, avg loss $-30.16, max drawdown -1.19%, exits {'stop-loss': 8, 'take-profit': 7}, blocked by risk 0.
- Variant B: 13 trades, mean total return +7.50%, mean win rate 85.0%, mean max drawdown -2.56%, symbols with trades 10.
- Variant A per symbol: {'AAPL': 1, 'MSFT': 2, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'META': 2, 'TSLA': 2, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- Variant B per symbol: AAPL: 1 trades, +1.03%, 100.0% win; MSFT: 0 trades, +0.00%, 0.0% win; NVDA: 1 trades, +10.69%, 100.0% win; SPY: 1 trades, +4.93%, 100.0% win; AMZN: 1 trades, +10.90%, 100.0% win; GOOGL: 1 trades, +8.45%, 100.0% win; META: 3 trades, +22.70%, 100.0% win; TSLA: 1 trades, +21.86%, 100.0% win; JPM: 1 trades, +9.40%, 100.0% win; JNJ: 0 trades, +0.00%, 0.0% win; BTC-USD: 2 trades, -0.80%, 50.0% win; ETH-USD: 1 trades, -14.15%, 0.0% win

## OOS-2 — 2025-02-28 → 2025-08-27 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Variant A: 21 trades (21 triggers), 3 wins / 18 losses, 14.3% win rate, paper P&L $-398.34 (-3.98%), avg win $43.68, avg loss $-29.41, max drawdown -4.69%, exits {'take-profit': 3, 'stop-loss': 18}, blocked by risk 0.
- Variant B: 14 trades, mean total return +12.16%, mean win rate 95.5%, mean max drawdown -0.57%, symbols with trades 11.
- Variant A per symbol: {'AAPL': 2, 'MSFT': 1, 'NVDA': 2, 'SPY': 2, 'AMZN': 2, 'GOOGL': 2, 'META': 2, 'TSLA': 3, 'JPM': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- Variant B per symbol: AAPL: 2 trades, +20.97%, 100.0% win; MSFT: 1 trades, +18.22%, 100.0% win; NVDA: 1 trades, +15.29%, 100.0% win; SPY: 1 trades, +11.06%, 100.0% win; AMZN: 0 trades, +0.00%, 0.0% win; GOOGL: 1 trades, +18.38%, 100.0% win; META: 1 trades, +1.84%, 100.0% win; TSLA: 1 trades, +19.21%, 100.0% win; JPM: 1 trades, +2.85%, 100.0% win; JNJ: 1 trades, +1.63%, 100.0% win; BTC-USD: 2 trades, +25.47%, 100.0% win; ETH-USD: 2 trades, -1.20%, 50.0% win

### Bollinger mean-reversion (buy lower band, sell upper band)

- Variant A: 13 trades (13 triggers), 2 wins / 11 losses, 15.4% win rate, paper P&L $-238.19 (-2.38%), avg win $43.60, avg loss $-29.58, max drawdown -2.96%, exits {'stop-loss': 11, 'take-profit': 2}, blocked by risk 0.
- Variant B: 16 trades, mean total return +24.50%, mean win rate 100.0%, mean max drawdown 0.00%, symbols with trades 11.
- Variant A per symbol: {'AAPL': 1, 'MSFT': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 1, 'GOOGL': 2, 'META': 1, 'JPM': 1, 'JNJ': 1, 'BTC-USD': 2, 'ETH-USD': 1}
- Variant B per symbol: AAPL: 2 trades, +11.13%, 100.0% win; MSFT: 1 trades, +18.22%, 100.0% win; NVDA: 1 trades, +27.63%, 100.0% win; SPY: 1 trades, +13.39%, 100.0% win; AMZN: 1 trades, +16.94%, 100.0% win; GOOGL: 1 trades, +15.87%, 100.0% win; META: 1 trades, +12.30%, 100.0% win; TSLA: 0 trades, +0.00%, 0.0% win; JPM: 1 trades, +28.57%, 100.0% win; JNJ: 1 trades, +8.45%, 100.0% win; BTC-USD: 3 trades, +40.21%, 100.0% win; ETH-USD: 3 trades, +76.83%, 100.0% win

## OOS-3 — 2024-09-01 → 2025-02-28 (out-of-sample)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Variant A: 21 trades (21 triggers), 15 wins / 6 losses, 71.4% win rate, paper P&L $472.75 (+4.73%), avg win $40.50, avg loss $-22.47, max drawdown -0.30%, exits {'take-profit': 12, 'stop-loss': 4, 'time exit (10 days)': 5}, blocked by risk 0.
- Variant B: 11 trades, mean total return +12.73%, mean win rate 92.9%, mean max drawdown -0.24%, symbols with trades 7.
- Variant A per symbol: {'AAPL': 3, 'MSFT': 2, 'GOOGL': 1, 'TSLA': 3, 'JPM': 1, 'JNJ': 4, 'BTC-USD': 2, 'ETH-USD': 5}
- Variant B per symbol: AAPL: 2 trades, +11.53%, 100.0% win; MSFT: 1 trades, +4.54%, 100.0% win; NVDA: 0 trades, +0.00%, 0.0% win; SPY: 0 trades, +0.00%, 0.0% win; AMZN: 0 trades, +0.00%, 0.0% win; GOOGL: 0 trades, +0.00%, 0.0% win; META: 0 trades, +0.00%, 0.0% win; TSLA: 1 trades, +31.65%, 100.0% win; JPM: 1 trades, +2.31%, 100.0% win; JNJ: 2 trades, +0.66%, 50.0% win; BTC-USD: 2 trades, +22.38%, 100.0% win; ETH-USD: 2 trades, +16.06%, 100.0% win

### Bollinger mean-reversion (buy lower band, sell upper band)

- Variant A: 12 trades (12 triggers), 8 wins / 4 losses, 66.7% win rate, paper P&L $191.67 (+1.92%), avg win $36.20, avg loss $-24.49, max drawdown -0.47%, exits {'stop-loss': 3, 'time exit (10 days)': 4, 'take-profit': 5}, blocked by risk 0.
- Variant B: 9 trades, mean total return +6.84%, mean win rate 75.0%, mean max drawdown -2.48%, symbols with trades 8.
- Variant A per symbol: {'AAPL': 1, 'SPY': 1, 'GOOGL': 2, 'TSLA': 1, 'JPM': 2, 'JNJ': 2, 'BTC-USD': 1, 'ETH-USD': 2}
- Variant B per symbol: AAPL: 1 trades, +5.99%, 100.0% win; MSFT: 2 trades, +11.33%, 100.0% win; NVDA: 0 trades, +0.00%, 0.0% win; SPY: 1 trades, +3.94%, 100.0% win; AMZN: 0 trades, +0.00%, 0.0% win; GOOGL: 0 trades, +0.00%, 0.0% win; META: 1 trades, +10.75%, 100.0% win; TSLA: 1 trades, +32.47%, 100.0% win; JPM: 1 trades, +10.11%, 100.0% win; JNJ: 1 trades, -2.41%, 0.0% win; BTC-USD: 0 trades, +0.00%, 0.0% win; ETH-USD: 1 trades, -17.46%, 0.0% win

## Phase-4 window (in-sample) — 2026-02-23 → 2026-11-06 (in-sample — the window the hypothesis was picked from)

- History: 12 symbols fetched; failed: none

### RSI mean-reversion (buy RSI < 30, sell RSI > 70)

- Variant A: 18 trades (18 triggers), 13 wins / 5 losses, 72.2% win rate, paper P&L $435.99 (+4.36%), avg win $43.03, avg loss $-24.69, max drawdown -0.30%, exits {'take-profit': 12, 'stop-loss': 4, 'time exit (10 days)': 2}, blocked by risk 0.
- Variant B: 10 trades, mean total return +12.40%, mean win rate 87.5%, mean max drawdown -0.08%, symbols with trades 8.
- Variant A per symbol: {'AAPL': 2, 'MSFT': 1, 'AMZN': 4, 'GOOGL': 4, 'META': 3, 'TSLA': 2, 'JPM': 1, 'JNJ': 1}
- Variant B per symbol: AAPL: 2 trades, +25.54%, 100.0% win; MSFT: 1 trades, +5.72%, 100.0% win; NVDA: 0 trades, +0.00%, 0.0% win; SPY: 0 trades, +0.00%, 0.0% win; AMZN: 1 trades, +7.13%, 100.0% win; GOOGL: 1 trades, -0.67%, 0.0% win; META: 2 trades, +35.98%, 100.0% win; TSLA: 1 trades, +7.06%, 100.0% win; JPM: 0 trades, +0.00%, 0.0% win; JNJ: 1 trades, +5.68%, 100.0% win; BTC-USD: 1 trades, +12.79%, 100.0% win; ETH-USD: 0 trades, +0.00%, 0.0% win

### Bollinger mean-reversion (buy lower band, sell upper band)

- Variant A: 11 trades (11 triggers), 8 wins / 3 losses, 72.7% win rate, paper P&L $241.97 (+2.42%), avg win $41.66, avg loss $-30.45, max drawdown -0.30%, exits {'take-profit': 7, 'time exit (10 days)': 1, 'stop-loss': 3}, blocked by risk 0.
- Variant B: 10 trades, mean total return +11.29%, mean win rate 100.0%, mean max drawdown 0.00%, symbols with trades 9.
- Variant A per symbol: {'AAPL': 1, 'NVDA': 1, 'SPY': 1, 'AMZN': 2, 'GOOGL': 2, 'META': 1, 'TSLA': 2, 'JNJ': 1}
- Variant B per symbol: AAPL: 1 trades, +16.29%, 100.0% win; MSFT: 1 trades, +9.60%, 100.0% win; NVDA: 0 trades, +0.00%, 0.0% win; SPY: 1 trades, +5.74%, 100.0% win; AMZN: 2 trades, +22.00%, 100.0% win; GOOGL: 1 trades, +5.28%, 100.0% win; META: 1 trades, +21.27%, 100.0% win; TSLA: 1 trades, +13.50%, 100.0% win; JPM: 1 trades, +1.56%, 100.0% win; JNJ: 1 trades, +6.39%, 100.0% win; BTC-USD: 0 trades, +0.00%, 0.0% win; ETH-USD: 0 trades, +0.00%, 0.0% win

## What this does and does not prove

Out-of-sample results are the honest test of the mean-reversion hypothesis: the strategies were picked because they looked good on the Phase 4 window, so that window cannot confirm them. A result that holds across all three earlier windows would support further testing; a result that fades or reverses means the Phase 4 backtest numbers were a one-window artefact. Nothing here proves future profits: past performance does not guarantee future results, and live paper trades over real days plus a compliance/legal review are still required before any real money is considered. Method note: the in-sample native backtests here start at row 60 of each history (the validation warm-up), while Phase 4's backtest suite ran on the full history — so in-sample trade counts here (RSI 10, Bollinger 10) are lower than Phase 4's (20, 24); mean returns are still directly comparable.

## Variant A trades (every trade, in order, per window)

### OOS-1 — RSI mean-reversion (buy RSI < 30, sell RSI > 70)

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

### OOS-1 — Bollinger mean-reversion (buy lower band, sell upper band)

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

### OOS-2 — RSI mean-reversion (buy RSI < 30, sell RSI > 70)

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

### OOS-2 — Bollinger mean-reversion (buy lower band, sell upper band)

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

### OOS-3 — RSI mean-reversion (buy RSI < 30, sell RSI > 70)

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

### OOS-3 — Bollinger mean-reversion (buy lower band, sell upper band)

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

### Phase-4 window (in-sample) — RSI mean-reversion (buy RSI < 30, sell RSI > 70)

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

### Phase-4 window (in-sample) — Bollinger mean-reversion (buy lower band, sell upper band)

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

