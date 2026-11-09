# VaultTec / VaultAI

**AI Trading & Investment Intelligence Platform — Company #3.**
The heart of the family trust: the engine that grows the trust's money.

A Jarvis-style AI assistant that coaches users through their first few trades, then — only with their authorisation and strictly inside their profile settings — automates trading. Paper trading first. Always.

> **Risk disclosure:** Trading involves substantial risk of loss. VaultTec does not promise guaranteed profits and does not advertise unverified accuracy. Past performance does not guarantee future performance. **Phase 1 is paper trading only — virtual money, no live brokerage, no real money, no leverage, no options.**

## The coaching-to-automation flow

1. **Learn** — set your profile: goals, capital, risk tolerance, max loss.
2. **Coached paper trading** — the Coach walks you through your first few trades, step by step, in plain language. You approve every trade.
3. **Graduation check** — after your first coached trades, review what you learned. You opt in to the next stage; it is never automatic.
4. **Supervised automation (paper only)** — automation proposes and places paper trades only inside your profile limits, with a kill-switch you can hit at any time.
5. **Live trading** — Phase 4+, only after 30–50 paper trades and validation, starting small ($25–$50). Not in this build.

Automation never bypasses risk controls or your authorisation. A trade that fails a risk check is blocked and logged.

## Quick start (Windows-first, Python 3.11+)

```bash
cd vaulttec
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

On macOS/Linux, activate with `source .venv/bin/activate`.

## Project layout

```
app.py                  Streamlit dashboard (UI only)
vaulttec/
  config/settings.py    Settings, tiers, safety limits
  db/                   SQLite database + models
  market/               Market data provider (OHLCV, sample + yfinance fallback) + indicators (SMA, EMA, RSI, MACD, Bollinger, ATR, volume)
  analytics/            Signal generation + scanner + signal history + backtests + historical analysis
  risk/                 Risk engine — position sizing, stops, limits
  portfolio/            Holdings, P&L, trade journal
  paper_trading/        Virtual cash, virtual orders — no real money
  coach/                Coaching checklist + plain-language walkthroughs
  automation/           Profile-driven automation + kill-switch + audit log
  ai_assistant/         Jarvis-style assistant (expanded rule-based in Phase 2; LLM-ready via llm_hook.py, no LLM connected)
tests/                  pytest unit tests
data/                   SQLite database + sample data (git-ignored)
```

No module except `app.py` imports Streamlit. No module imports a broker.

## Design

Obsidian black / industrial charcoal / metallic gold / vault amber. Underground financial intelligence bunker — clean, no cheesy hacker neon.

## Safety rules (non-negotiable)

- Paper trade 30–50 trades before any live consideration.
- Start small: $25–$50, then $50–$100.
- No leverage. No options in the initial strategy.
- Every trade needs a stop-loss.
- Never promise guaranteed profits. Disclose risks clearly.

## Phase 3 validation — run it yourself

```bash
python -m vaulttec.analytics.validation
```

Walk-forward paper-trading validation over offline sample history:
**40 trades placed, 24 wins / 16 losses (60.0%), +$490.49 (+4.90%) paper P&L.**
Full trade-by-trade report: `validation/phase3-paper-validation-report.md`
(+ JSON). Honest caveat: the sample data is a random walk, so this
proves the machinery works — not that the strategy will make money.

## Phase 4 Step 1 — real-market validation (done 2026-11-09)

Same 40-trade walk-forward, same 3% stop / 4.5% target / 10-day exit,
same Risk Engine checks — but on delayed real market history from
yfinance (free), all 12 symbols, no failures:

```bash
python -m vaulttec.analytics.validation --provider yfinance --days 180 \
  --target 40 --stem phase4-real-market-validation-report --backtests
```

**Result: 40 trades placed, 16 wins / 24 losses (40.0%), -$92.40 (-0.92%) paper P&L.**
Exits: 23 stop-loss / 12 take-profit / 5 time exits. 0 blocked by risk.
At 1.5:1 risk/reward the break-even win rate is exactly 40% — so the
signal method shows **no edge on real data in this window**: it roughly
breaks even, slightly negative. The Phase 3 60% was a sample-data
artefact, as that report warned. The backtest suite on the same real
history is more interesting: mean-reversion strategies did best
(Bollinger +17.71% mean return, RSI +12.44%, both ~81–83% win rate,
small drawdowns; MACD +8.38%, SMA +1.46%) — a hypothesis to test on
other windows, not proof. Full report:
`validation/phase4-real-market-validation-report.md` (+ JSON).
**Next step: live paper trades over real days — do NOT move to real
money on this result.** Real money also needs a compliance/legal
review and Neko's approval.

## Phase 4b — mean-reversion follow-up (done 2026-11-09)

The Phase 4 backtests suggested Bollinger (+17.71%) and RSI (+12.44%)
mean reversion. Tested out-of-sample on three earlier, non-overlapping
180-day windows (all ending before the Phase 4 window), delayed real
yfinance history, 12 symbols, no failures — two variants each:

```bash
python -m vaulttec.analytics.mean_reversion
```

- **Native backtest (no stop, hold to RSI > 70 / upper band): the
  hypothesis replicates.** Mean of window means: RSI **+10.98%**
  (Phase 4 in-sample +12.44%), Bollinger **+12.95%** (+17.71%),
  positive in 3 of 3 windows each, 40 / 38 trades.
- **Risk-managed validation (3% stop / 4.5% target / 10-day exit,
  Risk Engine): weak and regime-dependent.** Pooled over 3 windows:
  RSI 67 trades, 47.8% win, **+$341.61** (+1.14%); Bollinger 40 trades,
  42.5% win, **+$27.76** (+0.09%). Per window RSI: +$267 / −$398 / +$473;
  Bollinger: +$74 / −$238 / +$192. The falling OOS-2 window (Feb–Aug 2025)
  stopped RSI out 18 of 21 times (14.3% win) — the 3% stop gets whipsawed
  while hold-through recovers, so the bounce is real but the only
  tradeable version of it is roughly break-even. **Verdict: keep testing
  this direction, but the next test must be an exit that keeps the bounce
  and survives a falling market (wider stop, time exit, or a downtrend
  filter) — not real money.** Full report:
  `validation/phase4b-mean-reversion-followup-report.md` (+ JSON).
  75 tests pass (65 + 10 new Phase 4b tests, stubs only, no network).

## Phase 4c — exit test (done 2026-11-09)

Can a better exit raise the win rate? Same three out-of-sample
windows as Phase 4b, same 12 symbols, delayed real yfinance history,
70 days of warm-up so the SMA-50 filter is defined on day one:

```bash
python -m vaulttec.analytics.exit_test
```

- **Wider stop is the clear direction.** Pooled OOS, RSI: wide-5
  (5% stop / 7.5% target) 67 trades, 59.7% win, **+$1,517.23**
  (expectancy +$22.65/trade), OOS-2 −$41.05 — misses survival by
  $41; wide-6 (6% / 9%) 67 trades, 59.7% win, **+$1,441.19**,
  OOS-2 +$63.26 — the only RSI variant worth keeping by the rules
  fixed before the run (pooled P&L > $0 AND OOS-2 P&L >= $0).
  Bollinger: wide-5 40 trades, 65.0% win, **+$888.92**, OOS-2
  +$352.19; wide-6 40 trades, 65.0% win, **+$880.48**, OOS-2
  +$482.00.
- **The downtrend filter throws away winners too.** RSI filter:
  32 trades (35 of 67 triggers skipped), +$267.68, OOS-2 −$208.42
  — still fails the falling window. Bollinger filter: 17 trades,
  +$191.95, OOS-2 +$14.55 on just 2 trades. Combined (wide-5 +
  filter, chosen after seeing the base results — post-hoc) is worse
  than wide-5 alone for both strategies (RSI +$532.13, Bollinger
  +$376.36).
- **Time-5d and signal-exit are mixed.** RSI time-5d +$417.33,
  OOS-2 −$348.71; Bollinger time-5d −$115.00. RSI signal-exit
  +$843.58 at only 41.8% win (expectancy beat win rate — a few big
  winners carried it) but OOS-2 −$439.76; Bollinger signal-exit
  −$103.42. Baseline reproduced Phase 4b exactly, so the machinery
  is consistent. **Verdict: keep the wider stop, drop the filter as
  a standalone fix, do NOT move to real money** — wide-5 vs wide-6
  differ by noise in OOS-2 for RSI, and seven variants on the same
  three windows means the best-looking one is partly best by chance.
  Next: wide-stop variants on a FRESH window, then live paper trades
  over real days. Full report:
  `validation/phase4c-exit-test-report.md` (+ JSON).
  89 tests pass (75 + 14 new Phase 4c tests, stubs only, no network).

## Phase 4d — fresh-window test (done 2026-11-09)

Was the wider stop real, or Phase 4c selection luck? Only wide-5
and wide-6, for both RSI and Bollinger mean-reversion, plus the
baseline as a control, on three fresh 180-calendar-day windows never
used for selection (FRESH-1: 2024-03-04 → 2024-09-01; FRESH-2:
2023-09-06 → 2024-03-04; FRESH-3: 2023-03-10 → 2023-09-06), same
12 symbols, delayed real yfinance history, 70 days warm-up, no
look-ahead, real PaperTradingEngine + Risk Engine, $10,000 virtual
cash, long-only, 10-day exit:

```bash
python -m vaulttec.analytics.fresh_window
```

- **The wider stop held up on fresh data.** Pooled fresh, RSI:
  wide-6 (6% / 9%) 73 trades, 61.6% win, **+$1,226.24**
  (expectancy +$16.80/trade), positive 3/3 windows; wide-5 (5% /
  7.5%) 73 trades, 58.9% win, **+$936.61**, positive 3/3.
  Bollinger: wide-6 36 trades, 63.9% win, **+$1,043.47**
  (expectancy +$28.99/trade), positive 3/3; wide-5 36 trades,
  58.3% win, **+$678.66**, positive 3/3. Wide-6 is best on fresh
  data for both strategies. Per window, RSI wide-6: +$298.22 /
  +$296.06 / +$631.96; Bollinger wide-6: +$499.89 / +$128.53 /
  +$415.05.
- **Baseline split by strategy.** RSI baseline (3% / 4.5%) also
  held up on fresh data: 73 trades, 52.1% win, +$425.03, positive
  2/3 windows (FRESH-1 was −$72.53). Bollinger baseline did not:
  36 trades, 38.9% win, −$66.99, positive 1/3 windows. So the
  wider stop is what rescues Bollinger, while RSI was already
  positive with the tight stop on these windows — the wide stop
  roughly triples its fresh P&L anyway.
- **Verdict: the wider stop survived a genuinely new test, but do
  NOT move to real money.** Fresh windows are still past prices:
  three more windows do not prove the next one, trade counts are
  small (especially Bollinger, 36 trades), and no falling-window
  stress test like OOS-2 was in the fresh set. Next: live paper
  trades over real days, then a compliance/legal review. Full
  report: `validation/phase4d-fresh-window-report.md` (+ JSON).
  98 tests pass (89 + 9 new Phase 4d tests, stubs only, no network).

## Phase 5 — trend-following & stress test (done 2026-11-09)

Two paper-only tests (`vaulttec/analytics/trend_and_stress.py`,
report `validation/phase5-trend-and-stress-report.md` + JSON).
This is a validation step, not the commercial Phase 5 in the
roadmap below.

```bash
python -m vaulttec.analytics.trend_and_stress
```

- **(a) Trend-following complement.** SMA crossover (SMA-10 cross
  above SMA-30) and MACD crossover (MACD cross above its signal
  line), exactly as defined in `analytics/backtest.py`, with wide-6
  exits (6% stop / 9% target, 10-day exit) on the same windows as
  before (OOS-1/2/3, the Phase 4 window, FRESH-1/2/3), same 12
  symbols, delayed real yfinance history, no look-ahead, real
  PaperTradingEngine + Risk Engine, $10,000 virtual cash,
  long-only. Entries are checked every bar, not every 5 days,
  because a crossover is a single-bar event a 5-day step would
  miss. **Neither trend strategy beats mean-reversion in the
  falling OOS-2 window** (pre-set rule: beat both RSI wide-6
  +$63.26 and Bollinger wide-6 +$482.00): SMA +$305.05 (27 trades,
  51.9% win) beats RSI but not Bollinger; MACD +$223.23 (68 trades,
  51.5% win) also beats RSI but not Bollinger. Pooled OOS: SMA
  +$314.89 (84 trades, 50.0%), MACD +$1,432.96 (191 trades, 52.4%)
  — MACD misses beating RSI's pooled +$1,441.19 by $8.23. Pooled
  fresh is the bright spot: MACD +$2,899.45 (174 trades, 60.9%
  win, positive 3/3 windows) beats both mean-reversion fresh
  figures (RSI +$1,226.24, Bollinger +$1,043.47); SMA fresh
  +$351.50 (73 trades, 58.9%) beats neither.
- **(b) Stress test on one more fresh window.** Wide-6
  mean-reversion on FRESH-4 (2022-09-12 → 2023-03-10, ends the day
  FRESH-3 starts, overlaps nothing used before), baseline and
  wide-5 as controls. **RSI wide-6 holds up: 32 trades, 50.0% win,
  +$651.89** (best variant; baseline +$424.31, wide-5 +$302.41).
  **Bollinger wide-6 does not: 14 trades, 35.7% win, +$3.24** —
  essentially break-even, below the 40% break-even win rate, on a
  small trade count; Bollinger baseline was best there (+$123.22,
  50.0% win). Single window only, so this is weaker evidence than
  the Phase 4d three-window hold-up.
- **Verdict: keep wide-6 mean-reversion as the lead, keep MACD
  trend-following as a complement worth watching — do NOT move to
  real money.** Trend-following does not solve the falling window
  (Bollinger mean-reversion was better there), and MACD's fresh
  strength against its OOS mediocrity is itself a regime warning.
  Related work: a parallel Phase 4e run tested a different trend
  entry (close > SMA-20 > SMA-50, a persistent state) on
  FRESH-1/2/3 only, from cache — wide-6 422 trades, 61.8% win,
  +$5,163.64 pooled fresh — but it did not cover OOS-2 either.
  Next: live paper trades over real days, then a compliance/legal
  review. 141 tests pass (124 + 13 new Phase 5 tests + 4 Phase 4e
  tests, stubs only, no network).

## Roadmap

- **Phase 1 — Foundation (done):** skeleton, dashboard, SQLite, sample data, risk engine, paper trading, coach, profile/automation settings.
- **Phase 2 — Intelligence (done):** expanded rule-based assistant (LLM-ready hook, no LLM connected), EMA/MACD/Bollinger/ATR/volume indicators with plain-language explanations, market scanner (12-symbol universe, stocks + crypto), explainable multi-check signals, signal history + accuracy tracking, historical analysis, yfinance with offline sample fallback.
- **Phase 3 — Risk & Testing (done — this build):** side-aware risk engine with boundary fixes, paper engine wired to concentration + daily-loss limits, 4-strategy backtest suite with drawdowns, 40-trade walk-forward validation (+$490.49 paper, 60% win rate on sample data), kill-switch and graduation gate verified end to end. 60 tests pass.
- **Phase 4 Step 1 — Real-market validation (done 2026-11-09):** same 40-trade walk-forward on delayed real yfinance history — 16 wins / 24 losses (40.0%), -$92.40 (-0.92%) paper P&L; no edge for the signal method in this window (break-even is 40% at 1.5:1). Backtests: Bollinger +17.71% / RSI +12.44% mean return — hypothesis only. 65 tests pass. Next: live paper trades over real days; brokerage integration NOT started and NOT authorised.
- **Phase 4b — Mean-reversion follow-up (done 2026-11-09):** Bollinger/RSI tested out-of-sample on three earlier 180-day windows — native backtest replicates (RSI +10.98%, Bollinger +12.95% mean of window means, positive 3/3 windows), risk-managed version roughly break-even pooled (RSI +$341.61, Bollinger +$27.76) and bad in the falling OOS-2 window. Keep testing the direction with a better exit; do NOT move to real money. 75 tests pass.
- **Phase 4c — Exit test (done 2026-11-09):** wider stop is the clear direction — RSI wide-5 +$1,517.23 (59.7% win, OOS-2 −$41.05) and wide-6 +$1,441.19 (59.7% win, OOS-2 +$63.26, the only RSI variant worth keeping); Bollinger wide-5 +$888.92 and wide-6 +$880.48, both survive OOS-2. The downtrend filter throws away winners too (combined wide-5+filter worse than wide-5 alone); time-5d and signal-exit are mixed. Keep the wider stop, test it on a FRESH window next; do NOT move to real money. 89 tests pass.
- **Phase 4d — Fresh-window test (done 2026-11-09):** the wider stop held up on three fresh windows never used for selection — RSI wide-6 +$1,226.24 (61.6% win, 3/3 windows), wide-5 +$936.61 (58.9%, 3/3); Bollinger wide-6 +$1,043.47 (63.9%, 3/3), wide-5 +$678.66 (58.3%, 3/3). RSI baseline also held up (+$425.03); Bollinger baseline did not (−$66.99). Still past prices only — next is live paper trades over real days, then a compliance/legal review; do NOT move to real money. 98 tests pass.
- **Live paper trading (set up 2026-11-09, running):** wide-6 traded one day at a time on delayed real yfinance prices as they arrive — `vaulttec/live_paper_trading.py`, state in `live_paper/state.json`, log in `live_paper/trades.jsonl`, report in `live_paper/live-paper-report.md`, runbook in `live_paper/RUNBOOK.md`. Daily command: `.venv/bin/python -m vaulttec.live_paper_trading` (recommended weekdays 17:00 EST, after the close). Idempotent per day, completed-bars only (no look-ahead), holidays/no-data days skipped, fetch failures recorded never replaced with sample data, kill-switch via `live_paper/STOP`. Paper only — no broker, no real money. 111 tests pass (98 + 13 new live-paper tests, stubs only, no network).
- **Challenge Trial (built 2026-11-09, paper only):** the free tier becomes a $20 Challenge Trial — the $20 is the user's own starting capital, VaultTec takes nothing from it. 30 paper trades in 1 month (win or lose — finishing is the pass, no course, no Academy — trading platform, not a school), AI proposes each trade with its evidence and the user decides YES or NO; every decision is logged in the journal with the outcome, and YES/NO accuracy is shown once trades resolve. Wide-6 risk rules (6% stop / 9% target) through the real PaperTradingEngine + Risk Engine — no second paper engine. Graduation shows "Challenge complete — ready for live trading" with live trading labelled NOT yet available (needs a compliance/legal check). No payments, no Stripe, no broker, no live trading. `vaulttec/challenge/`, dashboard section in `app.py`. 124 tests pass (112 + 12 new challenge tests, stubs only, no network).
- **Phase 4e — Trend-following, SMA-state entry (done 2026-11-09, parallel run):** buy when close > SMA-20 > SMA-50 (a persistent state, 5-day steps) on FRESH-1/2/3 only, from cache — wide-6 422 trades, 61.8% win, +$5,163.64 pooled fresh; baseline +$2,396.87, wide-5 +$5,442.28. Did not cover OOS-2, so it cannot answer the falling-window question. Report: `validation/phase4e-trend-following-report.md` (+ JSON).
- **Phase 5 — Trend-following & stress test (done 2026-11-09, validation step, not the commercial Phase 5):** SMA-10/30 and MACD crossover trend-following with wide-6 exits on OOS-1/2/3, the Phase 4 window, and FRESH-1/2/3 — neither beats mean-reversion in the falling OOS-2 window (SMA +$305.05, MACD +$223.23, vs Bollinger wide-6 +$482.00; both beat RSI wide-6 +$63.26). MACD pooled fresh +$2,899.45 (174 trades, 60.9%, 3/3 windows) beats both mean-reversion fresh figures; MACD pooled OOS +$1,432.96 misses RSI's +$1,441.19 by $8.23. Stress test on FRESH-4 (2022-09-12 → 2023-03-10): RSI wide-6 holds up (+$651.89, 32 trades, 50.0% win); Bollinger wide-6 does not (+$3.24, 14 trades, 35.7% win — below the 40% break-even). Keep wide-6 mean-reversion as the lead, MACD as a complement worth watching; do NOT move to real money. Report: `validation/phase5-trend-and-stress-report.md` (+ JSON). 141 tests pass.
- **Private live trading for Neko only (built 2026-11-09, paper first):** `vaulttec/private_live/` — Alpaca connector (paper first, live locked off by three locks), wide-6, approval-first, bracket orders, kill-switch. 161 tests pass.
- **My Private Trading phone panel (built 2026-11-09):** the private module wired into the Streamlit app (`vaulttec/private_live/panel.py` + a "🔒 My Private Trading" section in `app.py`, after Live paper trading) — phone-first layout, status card, Scan (proposals only), per-proposal APPROVE / REJECT, kill-switch, live-gate check. Hidden until a login password is set (`VAULTTEC_LOGIN_PASSWORD`); live can never be enabled from the UI. Phone access needs the hosted deploy — see DEPLOY.md Step 4. 168 tests pass (161 + 7 new panel tests, stubs only, no network).
- **Phase 4 — Brokerage (not started, not authorised yet):** Alpaca-style API, authorisation, safeguards, limited live trading only after validation + Neko's approval.
- **Phase 5 — Commercial (not started):** memberships, billing, support, referrals — and the Polsia sales site, built only after the app is complete.

## Architecture

See [vaulttec-architecture.md](vaulttec-architecture.md) and the master brief in `../vaulttec-master-brief.md`.
