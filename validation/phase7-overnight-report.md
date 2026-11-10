# VaultTec — Phase 7 Overnight Test Report

Generated: 2026-11-10T02:57:46.340525 (UTC)

> Risk disclosure: trading involves substantial risk of loss. This report tests entry rules on past prices — it does not promise profits. Past performance does not guarantee future results.

## How it was run

- Phase 7 overnight test, paper only. Five items, all wide-6 (6% stop / 9% target, 1.5:1, 10-day exit), every trade through the real PaperTradingEngine and Risk Engine, balanced profile, long-only. Signals from history up to the trade day only — no look-ahead. (1) Combined portfolio (mean-reversion wide-6 + MACD, one shared $10,000) vs each leg alone on two NEW fresh windows, FRESH-5 (2022-03-14 -> 2022-09-12, falling/bear) and FRESH-6 (2021-09-13 -> 2022-03-14), same 12 symbols as Phase 6. (2) Crypto-only (BTC-USD, ETH-USD, SOL-USD if it fetches cleanly), wide-6 mean-reversion and MACD on fresh windows FRESH-1..6, weekend bars included. (3) RSI + Bollinger wide-6 on six additional liquid symbols (AMD, NFLX, AVGO, COST, HD, V) over FRESH-1/2/3. (4) MACD trend-following on the 2022 bear window alone (FRESH-5), taken from the item 1 run. (5) Small capital: the window tests repeated with $20, $50 and $100 starting cash (plus the $10,000 control re-run), RSI wide-6, Bollinger wide-6 and MACD on FRESH-1/2/3 and FRESH-5/6. Data: delayed real yfinance history, disk cache first, fetched only where not cached; failed fetches are recorded and the symbol is skipped, never replaced. In cache-only mode no fetch is attempted at all — items that need one are recorded as blocked, not as failures of the strategy.
- Data: yfinance (delayed real market data, free — Yahoo Finance), disk cache data/fresh-cache/ first

## New windows (never used for selection)

- **FRESH-5**: 2022-03-14 → 2022-09-12
- **FRESH-6**: 2021-09-13 → 2022-03-14

FRESH-5 ends the day FRESH-4 starts (2022-09-12); FRESH-6 ends the day FRESH-5 starts (2022-03-14). Neither overlaps OOS-1/2/3, the Phase 4 window, or FRESH-1/2/3/4, or each other.

## Headline verdicts

- **Item 1 — combined on the new fresh windows: NOT TESTED** (FRESH-5/6 need a Yahoo fetch that was not attempted).
- **Item 2 — crypto-only: PARTIAL — RSI holds up; Bollinger holds up; MACD holds up.**
- **Item 3 — wider symbols: NOT TESTED** (none of the new symbols is cached).
- **Item 4 — MACD in the 2022 bear window (FRESH-5): NOT TESTED** (FRESH-5 did not run).
- **Item 5 — small capital ($20 / $50 / $100): PARTIAL — see the small-cap section below for dollars-and-cents results.**

## Item 1 — Combined portfolio on the NEW fresh windows (FRESH-5/6)

Same 12 symbols as Phase 6. Verdict rule: Holds up = pooled FRESH-5/6 P&L > $0 AND pooled win rate > 40% AND positive in BOTH windows. Expectancy holds up in the falling market (FRESH-5) when combined expectancy is >= $0 and within $5/trade of the worst leg's FRESH-5 expectancy.

- **Status: BLOCKED** — FRESH-5/6 need a Yahoo fetch — not attempted in cache-only mode.

No window ran, so there is no pooled table and no combined-vs-legs comparison here — $0.00 from nothing would not be a result.

For comparison, Phase 6 on FRESH-1/2/3/4 (quoted, not re-run): combined $5,575.29 (354 trades, expectancy $15.75); RSI wide-6 $1,878.13; Bollinger wide-6 $1,046.71.

### FRESH-5 — 2022-03-14 → 2022-09-12

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: AAPL, MSFT, NVDA, SPY, AMZN, GOOGL, META, TSLA, JPM, JNJ, BTC-USD, ETH-USD

### FRESH-6 — 2021-09-13 → 2022-03-14

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: AAPL, MSFT, NVDA, SPY, AMZN, GOOGL, META, TSLA, JPM, JNJ, BTC-USD, ETH-USD

## Item 2 — Crypto-only (BTC-USD, ETH-USD, SOL-USD if clean)

Fresh windows FRESH-1..6, weekend bars included (crypto trades 24/7). Reported separately from stocks. Verdict rule: Holds up = pooled crypto P&L > $0 AND pooled win rate > 40% AND positive in at least 4 of the 6 fresh windows.

- SOL-USD fetched cleanly on every window: **NO — see failures below**.

- **Status: PARTIAL** — Ran 4 of 6 windows on the coins cached (BTC, ETH); FRESH-5/6 and SOL need a Yahoo fetch.

### Pooled crypto (FRESH-1..6)

| Variant | Trades | Win rate | P&L | Expectancy / trade | Positive windows |
|---|---:|---:|---:|---:|:---:|
| rsi_wide6 | 19 | 63.2% | $648.93 | $34.15 | 4/4 |
| bollinger_wide6 | 12 | 75.0% | $606.89 | $50.57 | 4/4 |
| macd | 46 | 56.5% | $792.96 | $17.24 | 4/4 |

### Per-coin pooled results (all six fresh windows)

#### RSI wide-6 (baseline, re-run)

| Symbol | Trades | Win rate | P&L | Expectancy / trade |
|---|---:|---:|---:|---:|
| BTC-USD | 10 | 50.0% | $202.98 | $20.30 |
| ETH-USD | 9 | 77.8% | $445.95 | $49.55 |

#### Bollinger wide-6 (baseline, re-run)

| Symbol | Trades | Win rate | P&L | Expectancy / trade |
|---|---:|---:|---:|---:|
| BTC-USD | 4 | 50.0% | $98.40 | $24.60 |
| ETH-USD | 8 | 87.5% | $508.49 | $63.56 |

#### MACD trend-following, wide-6 exits

| Symbol | Trades | Win rate | P&L | Expectancy / trade |
|---|---:|---:|---:|---:|
| BTC-USD | 23 | 60.9% | $507.68 | $22.07 |
| ETH-USD | 23 | 52.2% | $285.28 | $12.40 |

### Crypto FRESH-1 — 2024-03-04 → 2024-09-01

- History: 2 symbols fetched; failed: none

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 6 | 66.7% | $180.81 | $30.14 | $75.02 | $-59.63 | -1.19% | 0 |
| bollinger_wide6 | 5 | 80.0% | $302.92 | $60.58 | $90.66 | $-59.74 | -0.60% | 0 |
| macd | 11 | 63.6% | $285.23 | $25.93 | $75.58 | $-60.96 | -1.79% | 0 |

### Crypto FRESH-2 — 2023-09-06 → 2024-03-04

- History: 2 symbols fetched; failed: none

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 2 | 100.0% | $118.03 | $59.02 | $59.02 | $0.00 | 0.00% | 0 |
| bollinger_wide6 | 1 | 100.0% | $21.05 | $21.05 | $21.05 | $0.00 | 0.00% | 0 |
| macd | 12 | 50.0% | $186.37 | $15.53 | $83.36 | $-52.30 | -1.79% | 0 |

### Crypto FRESH-3 — 2023-03-10 → 2023-09-06

- History: 2 symbols fetched; failed: none

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 9 | 44.4% | $184.74 | $20.53 | $64.42 | $-14.59 | -0.30% | 0 |
| bollinger_wide6 | 4 | 50.0% | $142.28 | $35.57 | $90.27 | $-19.13 | -0.22% | 0 |
| macd | 11 | 54.5% | $89.09 | $8.10 | $65.36 | $-60.62 | -1.20% | 0 |

### Crypto FRESH-4 — 2022-09-12 → 2023-03-10

- History: 2 symbols fetched; failed: none

| Variant | Trades | Win rate | P&L | Expectancy | Avg win | Avg loss | Max DD | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 2 | 100.0% | $165.35 | $82.67 | $82.68 | $0.00 | 0.00% | 0 |
| bollinger_wide6 | 2 | 100.0% | $140.64 | $70.32 | $70.32 | $0.00 | 0.00% | 0 |
| macd | 12 | 58.3% | $232.27 | $19.36 | $55.52 | $-31.28 | -0.87% | 0 |

### FRESH-5 — 2022-03-14 → 2022-09-12

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: BTC-USD, ETH-USD, SOL-USD

### FRESH-6 — 2021-09-13 → 2022-03-14

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: BTC-USD, ETH-USD, SOL-USD

## Item 3 — Wider symbols (RSI + Bollinger wide-6, FRESH-1/2/3)

AMZN, TSLA and JPM were named in the brief as wider-symbol examples, but they are already in the original 12-symbol universe, so they are not new here. The six symbols run are the genuinely new liquid names: AMD, NFLX, AVGO, COST, HD and V.

Verdict rule: Holds up = pooled new-symbol P&L > $0 AND pooled win rate > 40% AND at least 4 of the 6 new symbols individually positive.

- **Status: BLOCKED** — None of the six new symbols is cached — a Yahoo fetch is needed.

No wider-symbol window ran — no pooled table and no per-symbol table; there is nothing to average yet.

### FRESH-1 — 2024-03-04 → 2024-09-01

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: AMD, NFLX, AVGO, COST, HD, V

### FRESH-2 — 2023-09-06 → 2024-03-04

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: AMD, NFLX, AVGO, COST, HD, V

### FRESH-3 — 2023-03-10 → 2023-09-06

- NOT TESTED: No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- Symbols not attempted: AMD, NFLX, AVGO, COST, HD, V

## Item 4 — MACD trend-following in the 2022 bear window (FRESH-5)

Taken from the item 1 run (same method, same data — not re-run). Verdict rule: Holds up in the bear window = FRESH-5 P&L > $0 AND FRESH-5 win rate > 40%. Beats mean-reversion = FRESH-5 P&L greater than BOTH mean-reversion wide-6 FRESH-5 figures.

- **Status: BLOCKED** — FRESH-5 did not run — no cached history, and the Yahoo fetch needs the user's approval tap.

## Item 5 — Small capital: $20 / $50 / $100 (plus the $10,000 control)

Each window starts fresh with the same capital — pooled P&L is the sum across separate pots, so pnl_per_window_usd is the honest per-pot figure. Position cap is 10% of the pot; quantity is floored to 4 decimals, so a symbol whose sized quantity rounds to zero is skipped as too small.

- **Status: PARTIAL** — Ran 3 of 5 windows; FRESH-5/6 need a Yahoo fetch.

### $10,000.00 pot — pooled across 3 windows

| Variant | Trades | Win rate | P&L (all pots added) | P&L per window | Expectancy / trade | Too small | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 73 | 61.6% | $1,226.24 | $408.75 | $16.80 | 0 | 0 |
| bollinger_wide6 | 36 | 63.9% | $1,043.47 | $347.82 | $28.99 | 0 | 0 |
| macd | 174 | 60.9% | $2,899.45 | $966.48 | $16.66 | 0 | 0 |

#### Per-window detail — $10,000.00 pot

- FRESH-1: rsi_wide6: 27 trades, $298.22; bollinger_wide6: 18 trades, $499.89; macd: 59 trades, $1,128.53
- FRESH-2: rsi_wide6: 22 trades, $296.06; bollinger_wide6: 5 trades, $128.53; macd: 56 trades, $733.55
- FRESH-3: rsi_wide6: 24 trades, $631.96; bollinger_wide6: 13 trades, $415.05; macd: 59 trades, $1,037.37
- FRESH-5: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- FRESH-6: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.

### $100.00 pot — pooled across 3 windows

| Variant | Trades | Win rate | P&L (all pots added) | P&L per window | Expectancy / trade | Too small | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 73 | 61.6% | $12.12 | $4.04 | $0.17 | 0 | 0 |
| bollinger_wide6 | 36 | 63.9% | $10.67 | $3.56 | $0.30 | 0 | 0 |
| macd | 174 | 60.9% | $27.58 | $9.19 | $0.16 | 0 | 0 |

#### Per-window detail — $100.00 pot

- FRESH-1: rsi_wide6: 27 trades, $3.00; bollinger_wide6: 18 trades, $5.19; macd: 59 trades, $10.04
- FRESH-2: rsi_wide6: 22 trades, $2.78; bollinger_wide6: 5 trades, $1.28; macd: 56 trades, $7.04
- FRESH-3: rsi_wide6: 24 trades, $6.34; bollinger_wide6: 13 trades, $4.20; macd: 59 trades, $10.50
- FRESH-5: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- FRESH-6: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.

### $50.00 pot — pooled across 3 windows

| Variant | Trades | Win rate | P&L (all pots added) | P&L per window | Expectancy / trade | Too small | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 70 | 60.0% | $6.05 | $2.02 | $0.09 | 3 | 0 |
| bollinger_wide6 | 35 | 62.9% | $5.43 | $1.81 | $0.16 | 1 | 0 |
| macd | 169 | 60.4% | $13.15 | $4.38 | $0.08 | 5 | 0 |
- rsi_wide6 too small by symbol: {'BTC-USD': 3}.
- bollinger_wide6 too small by symbol: {'BTC-USD': 1}.
- macd too small by symbol: {'BTC-USD': 5}.

#### Per-window detail — $50.00 pot

- FRESH-1: rsi_wide6: 24 trades, $1.61 (3 too small); bollinger_wide6: 17 trades, $2.77 (1 too small); macd: 54 trades, $4.29 (5 too small)
- FRESH-2: rsi_wide6: 22 trades, $1.39; bollinger_wide6: 5 trades, $0.64; macd: 56 trades, $3.45
- FRESH-3: rsi_wide6: 24 trades, $3.05; bollinger_wide6: 13 trades, $2.02; macd: 59 trades, $5.41
- FRESH-5: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- FRESH-6: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.

### $20.00 pot — pooled across 3 windows

| Variant | Trades | Win rate | P&L (all pots added) | P&L per window | Expectancy / trade | Too small | Blocked |
|---|---:|---:|---:|---:|---:|---:|---:|
| rsi_wide6 | 65 | 61.5% | $2.32 | $0.77 | $0.04 | 8 | 0 |
| bollinger_wide6 | 34 | 64.7% | $2.18 | $0.73 | $0.06 | 2 | 0 |
| macd | 158 | 60.8% | $4.99 | $1.66 | $0.03 | 16 | 0 |
- rsi_wide6 too small by symbol: {'BTC-USD': 8}.
- bollinger_wide6 too small by symbol: {'BTC-USD': 2}.
- macd too small by symbol: {'BTC-USD': 16}.

#### Per-window detail — $20.00 pot

- FRESH-1: rsi_wide6: 24 trades, $0.63 (3 too small); bollinger_wide6: 17 trades, $1.06 (1 too small); macd: 54 trades, $1.73 (5 too small)
- FRESH-2: rsi_wide6: 21 trades, $0.41 (1 too small); bollinger_wide6: 5 trades, $0.26; macd: 51 trades, $1.21 (5 too small)
- FRESH-3: rsi_wide6: 20 trades, $1.28 (4 too small); bollinger_wide6: 12 trades, $0.86 (1 too small); macd: 53 trades, $2.05 (6 too small)
- FRESH-5: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.
- FRESH-6: NOT TESTED — No cached history for this window — Yahoo fetch needs the user's approval tap and was not attempted.

Reading the small pots honestly: pooled P&L adds up separate pots, so the 'P&L per window' column is the honest figure — what one pot of that size did on average in one six-month window. A $20 pot trades at most $2.00 per trade (10% cap), so even a good window moves it by cents, not dollars.

## Fetch failures

- None — every requested symbol fetched on every window.

## Reading it honestly

Nothing here proves future profits: past performance does not guarantee future results. FRESH-5 and FRESH-6 are genuinely new windows, but they are still past prices — two more windows do not prove the next window, and nothing here changes the need for live paper trades over real days plus a compliance/legal review before real money is ever considered. The combined portfolio trades far more often than any single leg (MACD is checked every bar, mean-reversion on a 5-day grid), so its trade count is not comparable with the legs — P&L, win rate and expectancy per trade are the comparison.

## Trades (every trade, in order) — item 1, FRESH-5/6

Trade-by-trade rows for the combined portfolio and MACD on the two new windows. Every trade for every variant in every item is in the JSON report.

