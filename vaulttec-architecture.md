# VaultTec / VaultAI — Technical Architecture (Phase 1: Foundation)

**Company #3 in the 5-companies goal. Role: the heart of the family trust — the engine that grows the trust's money.**
**Status:** Phase 1 foundation only. Paper trading only. No live brokerage, no real money, no leverage, no options.
**Version:** 3.0 — 2026-11-08 (Phase 3: Risk & Testing)
**Source brief:** `../vaulttec-master-brief.md`

> **Risk disclosure (read first):** Trading involves substantial risk of loss and is not suitable for every investor. VaultTec does not promise guaranteed profits, does not advertise unverified accuracy, and must never present a signal, prediction, or backtest as a guarantee of future results. Past performance does not guarantee future performance. All Phase 1 trading is simulated paper trading with virtual money only.

---

## 1. What VaultTec is

An AI-powered financial intelligence and trading platform — a personal financial command center with a Jarvis-style AI assistant — that helps everyday investors:

- analyse markets, make informed decisions, manage portfolios, and
- **eventually** execute authorised trading strategies, only after paper-trading validation.

It combines artificial intelligence, predictive analytics, portfolio and risk management, automated market monitoring, financial education, and membership-based access into one modular platform.

## 2. The coaching-to-automation flow (core product idea, added 2026-11-08)

This is what makes VaultTec different from a stock-picking app. The user journey is deliberately staged:

```
Stage 0 — LEARN (profile + education)
  User sets profile: goals, capital, risk tolerance, time horizon,
  preferred markets (stocks / crypto), max loss they can accept.
  No trading yet.

Stage 1 — COACHED PAPER TRADING (first few trades)
  The Coach walks the user through each trade step by step:
  why this opportunity, what the risk is, position size, stop-loss,
  take-profit, what could go wrong — in plain language.
  The user approves every trade. Nothing executes without approval.
  Goal: the user understands *why*, not just *what*.

Stage 2 — GRADUATION CHECK
  After a set number of coached paper trades (target: first 5–10),
  the Coach reviews what the user got right / wrong, and checks
  understanding with a short review. The user must confirm they
  understand risk, stop-losses, and position sizing before moving on.
  Graduation is never automatic — the user opts in.

Stage 3 — SUPERVISED AUTOMATION (paper only in Phase 1)
  Automation proposes and (only with explicit authorisation) places
  paper trades strictly inside the user's profile settings:
  risk tolerance, max position size, daily loss limit, allowed
  symbols/markets, max exposure. Every automated trade is logged,
  explainable ("why this trade"), and reversible.
  The user can pause / shut down automation at any time
  (emergency kill-switch).

Stage 4 — LIVE TRADING (Phase 4+, NOT in Phase 1)
  Only after 30–50 paper trades, backtesting, and demonstrated
  performance. Small capital only ($25–$50 to start, then $50–$100),
  no leverage, no options, same risk controls, same authorisation.
  Requires brokerage integration, compliance review, and legal advice.
  Not built in Phase 1.
```

**Hard rules that apply at every stage:**
- Automation never bypasses risk controls or user authorisation.
- Automation never trades beyond the user's profile settings.
- A trade that fails a risk check is blocked and logged, not executed.
- The user can always pause automation instantly.
- No guaranteed profits, no unverified accuracy claims — ever.

## 3. Technology choices

| Layer | Choice | Why |
|---|---|---|
| OS | Windows-first | Neko's primary machine; code is cross-platform Python so it also runs on Linux/macOS |
| Language | Python 3.11+ | Ecosystem for finance, ML, and Streamlit |
| UI | Streamlit | Fast, Python-native dashboard; no separate frontend build |
| Database (Phase 1) | SQLite (`data/vaulttec.db`) | Zero setup, file-based, enough for one user + paper trades; migrate to PostgreSQL at commercial launch |
| Market data (Phase 1) | Sample / cached data + `yfinance` (free, delayed) | No paid API, no broker needed. Real-time / licensed data is a Phase 2 decision |
| Brokerage | **None in Phase 1** | Paper trading only. Alpaca-style API is a Phase 4 integration point, behind an adapter interface |
| AI assistant (Phase 1) | Rule-based analyst + explanations (starter) | Real LLM integration is Phase 2; the interface (`ai_assistant/`) is defined now so the model can be swapped in |
| Charts | Streamlit native charts + Plotly (optional) | Simple, no extra build step |
| Config / secrets | `.env` (never committed) | API keys, if any, live only in `.env` |
| Repo | GitHub-ready | `README.md`, `requirements.txt`, `.gitignore`, modular package layout |

## 4. Module map

```
vaulttec/
├── app.py                     # Streamlit entry point (dashboard)
├── requirements.txt
├── README.md
├── .gitignore
├── vaulttec/
│   ├── __init__.py
│   ├── config/
│   │   └── settings.py        # App settings, paths, membership tiers, safety limits
│   ├── db/
│   │   ├── database.py        # SQLite connection + schema init
│   │   └── models.py          # Dataclasses: UserProfile, Trade, Signal, Holding
│   ├── market/
│   │   ├── data.py            # Market data provider interface + sample provider
│   │   └── indicators.py      # SMA, RSI, volume, trend (pure functions, testable)
│   ├── analytics/
│   │   ├── signals.py         # Signal generation from indicators (explainable)
│   │   └── backtest.py        # Simple backtest harness (Phase 2/3, stubbed now)
│   ├── risk/
│   │   └── engine.py          # Position sizing, stop-loss, exposure, daily loss limits
│   ├── portfolio/
│   │   └── manager.py         # Holdings, P&L, allocation, trade journal
│   ├── paper_trading/
│   │   └── engine.py          # Virtual cash, virtual orders, fills, ledger — no real money
│   ├── coach/
│   │   └── coach.py           # Coaching checklist, plain-language trade walkthroughs,
│   │                          # graduation check, learning progress
│   ├── automation/
│   │   └── engine.py          # Profile-driven automation: propose trades, enforce
│   │                          # profile + risk limits, kill-switch, audit log
│   └── ai_assistant/
│       └── assistant.py       # Jarvis-style assistant interface; rule-based in Phase 1,
│                              # LLM-backed in Phase 2 (same function signatures)
└── tests/
    └── test_risk_engine.py    # Risk engine unit tests (run with pytest)
```

**Design rules for every module:**
- Pure functions where possible (indicators, risk math) so they can be unit-tested without the UI or network.
- No module imports Streamlit. Only `app.py` touches the UI.
- No module imports a broker. Brokerage is an adapter to be added in Phase 4.
- Every trade decision carries a reason string — the AI must be able to explain itself.

## 5. Data model (SQLite, Phase 1)

- `user_profile` — goals, capital (virtual), risk tolerance (conservative / balanced / growth), max position %, daily loss limit, allowed markets, automation enabled (default OFF), coaching stage.
- `holdings` — symbol, quantity, average cost, current (sample) price.
- `paper_trades` — symbol, side, quantity, price, stop-loss, take-profit, reason, source (coached / automated / manual), status, P&L.
- `signals` — symbol, direction, confidence (with evidence, not a promise), indicators used, created date.
- `coach_progress` — checklist items completed, coached trades done, graduation status.
- `automation_log` — every automated proposal, approval, block, and kill-switch event.

## 6. Risk Engine — the non-negotiable layer

Every order, coached or automated, passes through `risk/engine.py` before it can be placed:

1. **Position sizing** — max % of portfolio per trade (from profile; default 5% conservative, 10% balanced, 15% growth — never more than profile allows).
2. **Stop-loss required** — no trade without a stop-loss. Period.
3. **Take-profit planning** — risk/reward must be at least 1:1.5 to be proposed, and the reason must say so.
4. **Maximum exposure** — total invested cannot exceed the profile's max exposure.
5. **Concentration** — no single holding above the profile's concentration limit.
6. **Daily loss limit** — if paper losses hit the daily limit, trading stops for the day and automation is paused.
7. **No leverage, no options** — the engine rejects any order flagged as leveraged or options-based.
8. **Kill-switch** — `automation_enabled = False` blocks all automated orders instantly; the state is logged.

If any check fails, the trade is **blocked and logged with the reason** — never silently adjusted to fit.

## 7. Market data (Phase 1)

- **Default:** built-in sample dataset (deterministic, offline) so the app runs with no internet, no API key, and no cost.
- **Optional:** `yfinance` for delayed real quotes when the user enables it in settings. No paid data in Phase 1.
- **Phase 2:** evaluate licensed real-time data providers; cost them before committing.
- The data provider is behind one interface (`market/data.py`), so swapping providers does not touch the rest of the app.

## 8. AI Assistant (Phase 1 starter → Phase 2 LLM)

Phase 1 assistant is rule-based and honest about it:
- answers portfolio questions from live (paper) data,
- explains a signal in plain language ("why this trade, what could go wrong"),
- gives the daily market briefing from the watchlist,
- never invents a price, a prediction, or a guarantee.

Phase 2 swaps the engine for an LLM behind the same interface, with the same rules: cite evidence, give a confidence estimate with reasons, and say "I don't know" when data is missing. Voice commands are Phase 2+.

## 9. Dashboard (Phase 1, in `app.py`)

Obsidian black / industrial charcoal / metallic gold / vault amber. Underground financial intelligence bunker — clean, military-style labels, no cheesy hacker neon.

Sections:
- Portfolio value, daily + total P&L (paper)
- Market conditions + active signals (with explanations)
- Watchlist
- Risk exposure (exposure meter, daily loss limit status)
- Coaching checklist — first-trades progress, next coached step
- Profile settings — risk tolerance, capital, automation on/off, kill-switch
- Trading history / trade journal
- Risk disclosure footer on every page

## 10. Membership model (to be priced later)

Free / Standard / Premium / Elite, as in the brief. Phase 1 builds a single-user app with the tier structure in `config/settings.py` as data only — no billing, no paywall, no subscription code until Phase 5. Pricing and limits need research and finalising before launch.

## 11. Vault Operators (exploratory only)

Michigan-based 1099 contractor model for acquisition / onboarding / support, with automated commission accounting. **Do not classify anyone as an independent contractor without confirming the legal requirements with a licensed professional.** No Operator code in Phase 1.

## 12. Roadmap — what is Phase 1, and what is not

| Phase | Scope | Status |
|---|---|---|
| 1 — Foundation | Project skeleton, Streamlit dashboard, SQLite, sample market data, risk engine, paper trading, coach checklist, profile/automation settings (paper only) | **This build** |
| 2 — Intelligence | AI assistant (expanded rule-based, LLM-ready), technical analysis, scanners, signal generation, historical analysis | **Done — this build** |
| 3 — Risk & Testing | Full risk engine, backtesting, 30–50 paper trades, accuracy tracking | **Done — this build** |
| 4 — Brokerage | Alpaca-style API, authorisation, safeguards, simulated funds, limited live trading only after validation | Not started — no broker code, NOT authorised yet |
| 5 — Commercial | Memberships, billing, support, referrals, monitoring + Polsia sales site | Not started — the Polsia site is built only after the app is complete, per Neko 2026-11-08 |

## 13. Security, compliance, and safety notes

- No real money, no broker credentials, and no API keys in Phase 1. `.env` is git-ignored from day one.
- Trading is regulated. Before any live trading, commercial launch, or public signal: get advice from a licensed financial / legal professional on licensing, disclosures, and brokerage permissions. This document is technical architecture, not legal or financial advice.
- Never promise guaranteed profits. Never advertise unverified accuracy. Disclose risks clearly.
- VaultTec is the heart of the family trust — the engine that grows the trust's money. That makes the risk engine and the paper-trading validation gate even more important: the trust's money must never be the test subject. Paper first, small live only after validation, always within profile limits.

## 14. Phase 2 — Intelligence (done 2026-11-08)

What was added, and where:

- **Technical analysis** (`market/indicators.py`): EMA, MACD, Bollinger Bands,
  ATR, volume analysis, plus a plain-language explainer for every indicator.
  `analyse_indicators(history)` is the single source every other module
  reads indicators from, so the dashboard, scanner, and assistant can never
  disagree. Phase 1 functions (`sma`, `rsi`, `trend`) are unchanged.
- **Market data** (`market/data.py`): both providers now return full OHLCV
  history. `fetch_history` / `fetch_quote` try the requested provider and
  fall back to the offline sample provider automatically, labelling the
  source honestly — the app always works, with or without internet.
  `SCAN_UNIVERSE` (12 symbols, stocks + crypto) is the scanner's default.
- **Signal generation** (`analytics/signals.py`): signals now combine six
  independent checks (trend, EMA, MACD, RSI, Bollinger, volume). Confidence
  is 0.50 base + 0.05 per weighted point of agreement, capped at 0.85;
  neutral signals score 0.40. Every signal carries its full evidence list.
- **Market scanner** (`analytics/scanner.py`): scans the watchlist / universe,
  ranks by signal strength (confidence + agreement), neutrals last, and
  `top_opportunities()` returns only signals above a confidence floor —
  an empty list is a valid answer.
- **Signal history** (`analytics/signal_history.py`, table `signal_history`):
  every signal is recorded with its price; outcomes are resolved 5+ days
  later (win/loss/no-call), and accuracy is only reported once at least 10
  outcomes exist — before that it says "not enough data yet".
- **Historical analysis** (`analytics/backtest.py`): `analyse_history()`
  (returns, volatility, max drawdown, best/worst day, trend, volume trend,
  plain-language summary) and a MACD-crossover backtest alongside the
  Phase 1 SMA backtest. Historical only — never presented as future returns.
- **AI assistant** (`ai_assistant/assistant.py`): expanded rule-based
  assistant — daily market briefings, market explanations, trade analysis,
  strategy explanations (SMA/MACD crossover, stop-loss, position sizing,
  diversification, risk/reward, Bollinger, RSI), portfolio questions.
  Still local, no paid LLM, no API keys. `ai_assistant/llm_hook.py`
  defines the `LLMProvider` protocol a future LLM must fit, with
  `NoLLMProvider` as the default that fails loudly instead of faking
  an answer. Phase 1 methods (`briefing`, `explain_signal`, `answer`)
  keep their signatures.
- **Dashboard** (`app.py`): new sections — Market Scanner, Technical
  Analysis (per-symbol, with chart), Historical Analysis, Signal History
  + accuracy, daily briefing button, strategy explainer, "explain the
  market" button. Coaching, automation, kill-switch, and risk rules are
  unchanged. Signals are recorded once per session per symbol (not on
  every page reload).

Constraints kept: paper trading only, no live brokerage, no leverage,
no options, no profit promises, risk disclosure on every view, no paid
API or data feed, web-based Streamlit (no PC-only dependencies).

## 16. Phase 3 — Risk & Testing (done 2026-11-08)

What was added, and what the validation actually found:

- **Risk Engine — side-aware, boundary-fixed** (`risk/engine.py`):
  stop-loss / take-profit direction is now checked per trade side
  (buy: stop below entry, target above; sell: the reverse), and a
  take-profit on the wrong side is blocked. A trade at exactly the
  1.5:1 minimum now passes — the old code blocked it when
  floating-point rounding made it 1.4999:1. Money caps use the same
  1e-9 tolerance so a position sized to exactly the cap is not
  blocked by a few cents of rounding. Suggested stop/targets are
  built from the rounded stop with the target rounded *up* to the
  cent, so the app's own suggestions always meet the 1.5:1 minimum.
- **Paper-trading engine wired up** (`paper_trading/engine.py`):
  the two limits that could never fire before now do — the current
  holding value is passed to the Risk Engine (concentration limit),
  and realised P&L from closed trades is tracked (daily loss limit).
  A buy the virtual cash cannot cover is blocked with a reason
  instead of raising an error. New `close_position()` sells a
  holding, realises its P&L, and marks the trade closed.
- **Backtest suite** (`analytics/backtest.py`): RSI and Bollinger
  mean-reversion backtests join SMA and MACD; every strategy now
  reports max drawdown, and `run_backtest_suite()` runs all four on
  the same history and compares them. A strategy with zero trades is
  reported as zero trades, not hidden.
- **Paper-trading validation** (`analytics/validation.py`,
  report in `validation/`): a walk-forward run over deterministic
  offline sample history — 180 days per symbol, 5-day windows,
  signals from history up to the trade day only (no look-ahead),
  every trade through the real `PaperTradingEngine` with a 3%
  stop and a 4.5% target (1.5:1), exiting at stop, target, or 10 days.
  **Result (generated, not hand-written): 40 trades placed (target
  40, inside the brief's 30–50), 24 wins / 16 losses, 60.0% win rate,
  +$490.49 paper P&L (+4.90% of $10,000 virtual cash), average win
  $32.51, average loss −$18.11, exits 13 take-profit / 6 stop-loss /
  21 time exits, 0 blocked by risk.** Full trade-by-trade table in
  `validation/phase3-paper-validation-report.md` (+ JSON).
- **What the validation does NOT prove:** the sample history is a
  random walk, not real market data, so the 60% win rate says more
  about the sample data than about the strategy — the win rate moved
  between 52.5% and 60% across runs as different trades were
  included. The run proves the *machinery* works (signals, risk
  checks, exits, accounting, kill-switch, graduation gate). A real
  verdict needs the same run on real market history plus live paper
  trades over real days. The report states this in plain language.
- **Kill-switch verified** (`automation/engine.py`, tests): enabling
  before graduation is blocked; after graduation automation trades;
  the kill-switch stops it instantly, logs the event, and resuming
  does *not* silently re-enable it — the user must enable it again.
- **Graduation gate verified end to end** (tests): checklist + 5
  coached trades → graduation needs explicit user confirmation
  (confirming "no" does not graduate) → automation enables →
  kill-switch stops it. Paper mode only, throughout.
- **App fixes** (`app.py`): the emergency-stop button used to build
  a throwaway automation engine, so the stop was logged nowhere and
  paused nothing — the dashboard now keeps one session automation
  engine. Added an "Enable supervised automation" button after
  graduation, a backtest-suite comparison table, and a validation
  section that shows the generated report (or says it has not been
  run yet).
- **Tests:** 60 passed (36 from Phases 1–2 + 24 new Phase 3 tests:
  risk validation, backtest suite, validation run, graduation /
  kill-switch). Run with `pytest tests/ -q`.

## 17. Phase 4 Step 1 — Real-market validation (done 2026-11-09)

The first real-money-readiness test: the exact Phase 3 machinery
(`analytics/validation.py`, now provider-aware) re-run on delayed
real market history from yfinance (free), instead of the offline
sample random walk.

- **Data:** yfinance, 180 days requested per symbol, all 12 symbols
  fetched, none failed. Stocks returned 180 trading days
  (2026-02-23 → 2026-11-06); crypto returned 179 calendar days
  (2026-05-14 → 2026-11-09) — yfinance's "180d" period means
  trading days for stocks, calendar days for crypto. Histories can
  differ in length, so windows now run to each symbol's own length.
  A symbol that cannot be fetched is recorded in `failed_symbols`
  and skipped — never silently replaced with sample data.
- **Method (unchanged from Phase 3):** walk-forward, 5-day windows,
  signals from history up to the trade day only, 3% stop / 4.5%
  target (1.5:1), exit at stop, target, or 10 days, every trade
  through the real `PaperTradingEngine` and Risk Engine, balanced
  profile, $10,000 virtual cash, long-only (34 short signals skipped
  and counted, 7 neutral skipped).
- **Result (generated, not hand-written): 40 trades placed, 16 wins /
  24 losses, 40.0% win rate, −$92.40 paper P&L (−0.92%). Average
  win $37.50, average loss −$28.85. Exits: 23 stop-loss / 12
  take-profit / 5 time exits. 0 blocked by risk.** Full trade table:
  `validation/phase4-real-market-validation-report.md` (+ JSON).
- **What this means, honestly:** at 1.5:1 risk/reward the break-even
  win rate is exactly 40% — and the signal method landed on exactly
  40%. It shows **no edge on real data in this one 180-day window**:
  roughly break-even, slightly negative. The Phase 3 60% win rate
  was a sample-data artefact, exactly as that report warned. The
  machinery works (signals, risk checks, exits, accounting all ran
  cleanly on real prices); the *strategy* does not yet earn its keep.
- **Backtest suite on the same real history** (mean across symbols):
  Bollinger mean-reversion +17.71% mean total return, 81.2% win
  rate, −0.82% mean max drawdown; RSI mean-reversion +12.44%,
  83.3% win rate, −2.18% drawdown; MACD crossover +8.38%, 35.9%
  win rate; SMA crossover +1.46%, 45.1% win rate. Mean-reversion
  did best in this window — treat that as a **hypothesis to test on
  other windows**, not proof: small trade counts (20–24 for
  RSI/Bollinger), one window, one market regime.
- **Verdict: do NOT move to real money on this result.** Next step
  is live paper trades over real days (the app's paper engine, real
  prices, real time, fake money), plus testing the mean-reversion
  hypothesis out-of-sample, plus a compliance/legal review. Brokerage
  integration is still not started and not authorised; no broker was
  contacted, no data feed was paid for. 65 tests pass (60 + 5 new
  Phase 4 tests, stub providers only — no test touches the network).
- **How to re-run:** `python -m vaulttec.analytics.validation
  --provider yfinance --days 180 --target 40 --stem
  phase4-real-market-validation-report --backtests`

## 18. Phase 4b — Mean-reversion follow-up (done 2026-11-09)

The Phase 4 backtest suite suggested Bollinger (+17.71% mean return)
and RSI (+12.44%) mean reversion — a hypothesis picked *because* it
looked good on that one window. This follow-up tested it out-of-sample
(`vaulttec/analytics/mean_reversion.py`, report in `validation/`):
three earlier, non-overlapping 180-calendar-day windows ending before
the Phase 4 window starts (OOS-1 2025-08-27→2026-02-22, OOS-2
2025-02-28→2025-08-26, OOS-3 2024-09-01→2025-02-27), 40 days of
warm-up history before each window, delayed real yfinance history,
all 12 symbols fetched, none failed. The Phase 4 window was re-run
and labelled in-sample for comparison. Two variants per strategy per
window: A — risk-managed validation (entry on the trigger, 3% stop /
4.5% target / 10-day exit through the real PaperTradingEngine and Risk
Engine, balanced, $10,000 virtual cash, long-only); B — native backtest
exactly as in `backtest.py` (RSI sells above 70, Bollinger sells at
the upper band, no fixed stop/target). Signals use history up to the
trade day only — no look-ahead.

- **Variant B replicates out-of-sample:** mean of window means RSI
  **+10.98%** (in-sample re-run +12.40%, Phase 4's own figure +12.44%),
  Bollinger **+12.95%** (in-sample +11.29%, Phase 4 +17.71%),
  positive in 3 of 3 windows each, 40 / 38 trades total, win rates
  75–100%. The mean-reversion *bounce* is not a one-window artefact.
- **Variant A does not:** pooled over the 3 windows, RSI 67 trades,
  47.8% win, **+$341.61 (+1.14%)**; Bollinger 40 trades, 42.5% win,
  **+$27.76 (+0.09%)**. Per window RSI +$267 / −$398 / +$473;
  Bollinger +$74 / −$238 / +$192. The falling OOS-2 window (Feb–Aug
  2025) stopped RSI out 18 of 21 times (14.3% win, −$398.34) and
  Bollinger 11 of 13 — a 3% stop gets whipsawed in a downtrend while
  hold-through recovers, which is exactly why Variant B wins there.
- **Reading it honestly:** Variant B's numbers overstate what a
  tradeable strategy earns — no stop-loss means it rides the fall
  before the recovery (its drawdown counts completed trades only),
  and its mean return sums per-trade percentage moves with no
  position sizing, so one big crypto move counts like a whole
  portfolio. Variant A is the only version VaultTec may trade, and
  it is roughly break-even pooled. The next question is therefore
  an *exit* question, not an entry question: a wider stop, a
  time-based exit, or a downtrend filter that skips oversold buys
  while the market is falling. That is a new hypothesis to test.
- **Verdict: keep testing this direction, do NOT move to real money.**
  75 tests pass (65 + 10 new Phase 4b tests, stubs only — no test
  touches the network). One run note: the first dated-yfinance fetch
  hit a transient Yahoo block (all symbols empty); the provider now
  retries up to 3 times with backoff, and yfinance dates are
  tz-aware, so the provider strips the tz and the window-start
  comparison does too. Re-run: `python -m vaulttec.analytics.mean_reversion`.
  In-sample native backtests here start at row 60 (the validation
  warm-up), while Phase 4's ran on the full history — in-sample
  trade counts here (RSI 10, Bollinger 10) are lower than Phase 4's
  (20, 24); mean returns are still comparable.

## 19. Phase 4c — Exit test (done 2026-11-09)

The exit question from Phase 4b: can a better exit raise the win
rate? (`vaulttec/analytics/exit_test.py`, report in `validation/`.)
Same three out-of-sample windows (OOS-1/2/3), same 12 symbols,
delayed real yfinance history, 70 days of warm-up (up from 40, so
the SMA-50 filter is defined on day one), 5-day walk-forward steps,
no look-ahead, real PaperTradingEngine + Risk Engine, $10,000
virtual cash, long-only. Every variant keeps a stop-loss — the stop
is never removed. Seven variants per strategy: baseline (3% stop /
4.5% target / 10 days — the Phase 4b control), wide-5 (5% / 7.5%),
wide-6 (6% / 9%), filter (baseline exits + downtrend filter),
time-5d (baseline exits, 5-day horizon), signal-exit (3% stop, no
fixed target, exit on RSI > 70 / close >= upper band or 10 days),
and combined (best base variant per strategy + filter, selected
after seeing the base results — post-hoc, flagged as such).
Downtrend filter, fixed before the run: skip the buy when the
close is below its 50-day SMA AND that SMA is falling (today's
SMA-50 below the SMA-50 of 10 bars ago); if the SMA-50 is not yet
defined, the filter does not block. Verdict rules, also fixed
before the run: a variant "survives OOS-2" when its OOS-2 paper
P&L is >= $0; "worth keeping" when pooled OOS P&L > $0 AND it
survives OOS-2. Baseline reproduced Phase 4b exactly (RSI 67
trades, +$341.61; Bollinger 40 trades, +$27.76) — the machinery
is consistent. One transient Yahoo message appeared during a
fetch and the provider retried; all 12 symbols were fetched in
every window, none failed.

- **The wider stop is the clear direction.** Pooled OOS, RSI:
  wide-5 67 trades, 59.7% win, **+$1,517.23** (expectancy
  +$22.65/trade), OOS-2 −$41.05 — misses survival by $41;
  wide-6 67 trades, 59.7% win, **+$1,441.19**, OOS-2 +$63.26 —
  the only RSI variant worth keeping by the pre-set rules.
  Bollinger: wide-5 40 trades, 65.0% win, **+$888.92**, OOS-2
  +$352.19; wide-6 40 trades, 65.0% win, **+$880.48**, OOS-2
  +$482.00. Both wide variants are positive pooled for both
  strategies, and the win rate rose from 47.8%/42.5% (baseline)
  to ~60%/65%.
- **The filter throws away winners too.** RSI filter: 32 trades
  (35 of 67 triggers skipped), +$267.68 pooled, OOS-2 −$208.42
  — still fails the falling window. Bollinger filter: 17 trades,
  +$191.95, OOS-2 +$14.55 on just 2 trades — survives on paper,
  but that is a two-trade result. Combined (wide-5 + filter) is
  worse than wide-5 alone for both strategies (RSI +$532.13 vs
  +$1,517.23; Bollinger +$376.36 vs +$888.92).
- **Time-5d and signal-exit are mixed.** RSI time-5d +$417.33,
  OOS-2 −$348.71; Bollinger time-5d −$115.00. RSI signal-exit
  +$843.58 pooled at only 41.8% win — expectancy (+$12.59) beat
  win rate there, because a few big winners carried it — but
  OOS-2 −$439.76; Bollinger signal-exit −$103.42. Signal-exit
  note: this codebase's RSI is undefined (NaN) after 14 straight
  up-days, so a straight 14-day rise never registers as RSI > 70
  and the trade then closes on the 10-day time exit.
- **Verdict: keep the wider stop, drop the filter as a standalone
  fix, do NOT move to real money.** Wide-5 vs wide-6 differ by
  noise in OOS-2 for RSI (−$41 vs +$63), and seven variants were
  tested on the same three windows, so the best-looking one is
  partly best by chance. The next test is the wide-stop variants
  on a FRESH window (or live paper trades over real days), then
  a compliance/legal review — real money is still not supported.
  89 tests pass (75 + 14 new Phase 4c tests, stubs only — no test
  touches the network). Re-run:
  `python -m vaulttec.analytics.exit_test`.

## 20. Phase 4d — Fresh-window test (done 2026-11-09)

Was the wider stop real, or Phase 4c selection luck?
(`vaulttec/analytics/fresh_window.py`, report in `validation/`.)
Only the two Phase 4c winners — wide-5 (5% stop / 7.5% target)
and wide-6 (6% / 9%) — plus the baseline (3% / 4.5%) as a
control, for both RSI and Bollinger mean-reversion, on three fresh
180-calendar-day windows never used for selection: FRESH-1
2024-03-04 → 2024-09-01, FRESH-2 2023-09-06 → 2024-03-04,
FRESH-3 2023-03-10 → 2023-09-06. All end before OOS-3 starts
(2024-09-01) and none overlaps OOS-1/2/3, the Phase 4 window, or
each other. Same method as Phase 4c: delayed real yfinance
history, 70 days of warm-up, 12 symbols, 5-day walk-forward
steps, no look-ahead, real PaperTradingEngine + Risk Engine,
$10,000 virtual cash, long-only, 10-day exit. Every variant keeps
a stop-loss. Verdict rule, fixed before the run: a variant "holds
up" when its pooled fresh P&L is > $0 AND its pooled win rate is
> 40% (the 1.5:1 break-even) AND it is positive in at least 2 of
the 3 fresh windows. Fresh results are pooled ONLY across the
fresh windows — never with the selection windows, which are not
re-run here. The run itself completed cleanly in ~53 seconds with
no Yahoo approval cards pending (the earlier run had been killed
after its cards timed out; the code caches each fetched history
to `data/fresh-cache/` as it arrives, so a re-run resumes from
disk — 36 cache files after this run, 12 symbols × 3 windows).
All 12 symbols fetched in every window, none failed.

- **The wider stop held up on fresh data.** Pooled fresh, RSI:
  wide-6 73 trades, 61.6% win, **+$1,226.24** (expectancy
  +$16.80/trade), positive 3/3 windows (+$298.22 / +$296.06 /
  +$631.96); wide-5 73 trades, 58.9% win, **+$936.61**, positive
  3/3 (+$129.46 / +$327.46 / +$479.69). Bollinger: wide-6 36
  trades, 63.9% win, **+$1,043.47** (expectancy +$28.99/trade),
  positive 3/3 (+$499.89 / +$128.53 / +$415.05); wide-5 36
  trades, 58.3% win, **+$678.66**, positive 3/3 (+$349.46 /
  +$144.00 / +$185.20). Wide-6 is best on fresh data for both
  strategies, and its edge over wide-5 is consistent across
  windows rather than one lucky window.
- **Baseline split by strategy.** RSI baseline also held up:
  73 trades, 52.1% win, +$425.03, positive 2/3 windows
  (FRESH-1 −$72.53, FRESH-2 +$319.23, FRESH-3 +$178.33).
  Bollinger baseline did not: 36 trades, 38.9% win, −$66.99,
  positive 1/3 windows. So the wider stop is what rescues
  Bollinger on fresh data, while RSI was already positive with
  the tight stop on these windows — the wide stop roughly triples
  its fresh P&L anyway.
- **Verdict: the wider stop survived a genuinely new test, but do
  NOT move to real money.** Fresh windows are still past prices:
  three more windows do not prove the next one, trade counts are
  small (especially Bollinger, 36 trades), and no falling-window
  stress test like OOS-2 was in the fresh set. The honest next
  step is live paper trades over real days — prices arriving one
  day at a time, no re-runs — then a compliance/legal review.
  98 tests pass (89 + 9 new Phase 4d tests, stubs only — no test
  touches the network). Re-run:
  `python -m vaulttec.analytics.fresh_window`.

## 21. Live paper trading over real days (set up 2026-11-09)

The step Phase 4d called for: trade the wide-6 rules one day at a
time on delayed real prices as they arrive — no re-runs, no
look-ahead. (`vaulttec/live_paper_trading.py`, runbook in
`live_paper/RUNBOOK.md`, dashboard panel in `app.py`.)

- **Rules:** wide-6 only — 6% stop / 9% target (1.5:1), 10-bar
  time exit, RSI + Bollinger mean-reversion, long-only, balanced
  profile, $10,000 virtual cash, every trade through the real
  PaperTradingEngine and Risk Engine.
- **Daily run:** `python -m vaulttec.live_paper_trading` from the
  `vaulttec/` folder (venv). Recommended weekdays 17:00 EST, after
  the close — or any time the next morning before the open. The
  runner only ever trades *completed* bars (date before the run
  date, America/New_York), so a still-forming intraday bar is never
  traded on. No cron is set up in this repo — the schedule is set
  by the parent agent.
- **State (durable):** `live_paper/state.json` (cash, open
  positions with bars held, closed trades, last processed bar per
  symbol, run history), `live_paper/trades.jsonl` (append-only
  decision log), `live_paper/live-paper-report.md` (regenerated
  every run). The first ever run treats all earlier bars as
  warm-up and processes only the latest completed bar as day one.
  A second run on the same day finds no new completed bars and
  changes nothing (idempotent per day); a run after missed days
  processes every unprocessed completed bar in order.
- **Per bar, per symbol:** exit check first (stop on the bar's low,
  then target on the bar's high, then the 10-bar time exit), then
  entry check (RSI < 30, then Bollinger lower band) on history up
  to and including that bar only. The daily-loss tracker resets
  each new bar-day. Holidays / no-data days are logged and skipped;
  crypto trades weekends, stocks do not.
- **Failures:** a yfinance fetch is retried 3 times, recorded per
  symbol, and never replaced with sample data — a symbol that
  cannot be fetched is simply not traded that day. Total fetch
  failure exits non-zero with no cash/position change (the failure
  counts are still saved as the audit trail).
- **Kill-switch:** create `live_paper/STOP` (or set `enabled` to
  false in the state file) and the next run logs "stopped" and does
  nothing — no fetch, no trades. Delete the file to resume. Open
  positions stay open until resumed.
- **Two live-only guards** (they cannot change any validated
  backtest result, which used real prices): a position that exits
  on a bar is never re-entered on that same bar, and a Bollinger
  trigger needs a real (non-zero-width) band — a flat line is not
  a bounce.
- **Verdict so far: not yet — the first live day is 2026-11-09.**
  A good live paper run still needs a compliance/legal review
  before real money is ever considered. 111 tests pass (98 + 13
  new live-paper tests, stubs only — no test touches the network).

## 22. Challenge Trial (built 2026-11-09 — paper only)

The free tier becomes a Challenge Trial, approved by Neko
2026-11-09. Plan: `../vaulttec-challenge-trial.md`. Code:
`vaulttec/challenge/` (pure logic, no Streamlit, no network) plus
a dashboard section in `app.py`. It reuses the existing
PaperTradingEngine and Risk Engine — there is no second paper
engine — and it does not touch the coach's 5-trade graduation or
the live-paper runner.

- **The $20 is the user's own money.** `CHALLENGE_STARTING_CAPITAL
  = 20.0`; `vaulttec_takes_from_starting_capital_usd` is always
  0.0. The $20 is the user's starting capital for live trading
  later. VaultTec takes nothing from it and is not paid from it.
  Challenge trades in the app are paper trades on the $10,000
  virtual portfolio — the $20 is not spent in the app. The section
  says so in plain language, so the two numbers are never confused.
- **Pass = finish, not profit — 30 trades only, no course.**
  Revised 2026-11-09: Academy / course is REMOVED — VaultTec is a
  trading platform, not a school. There is no course gate and no
  `ACADEMY_LEVELS`, `complete_level`, or `is_course_done` anywhere
  in the code. Losing trades count — `record_trade` counts every
  trade whatever its outcome. The gate is `trades_done >= 30`;
  profitability is never part of it. Progress is trades only
  (`trades_done / 30`), and the Challenge lasts 1 month.
- **YES/NO flow.** For the selected symbol, the app shows the AI
  proposal — direction, confidence, evidence, price, wide-6 stop
  (6%) / target (9%, 1.5:1), what the trade risks vs targets — in
  plain language, with "the AI can't win every time" stated on the
  card. Only a long signal gets YES/NO buttons; a neutral/short
  signal shows why there is no proposal. YES records the decision,
  risk-checks the trade, and places it through the real engine with
  `source="challenge"` (a Risk Engine block logs the YES but places
  nothing). NO records the decision with a reason (from
  `NO_REASONS`: don't agree, too risky, waiting, don't understand,
  other) and places no trade. Every decision is logged with its
  outcome; the journal shows the last 10, and YES/NO accuracy
  (wins/losses over resolved trades only) appears once a trade has
  resolved — never before there is anything to measure.
- **Graduation.** When the gate is met the app shows "Challenge
  complete — ready for live trading" and, in the same message, that
  live trading is NOT yet available and needs a compliance/legal
  check first. No payment has been taken. The subscription prices
  shown after graduation are the approved ones (Starter $29/mo, Pro
  $59/mo, Elite $99/mo — `CHALLENGE_SUBSCRIPTIONS`, data only).
  After the challenge the user joins the membership separately and
  pays for it themselves — the subscription is NOT taken
  automatically from profits; the rest of the profits are the
  user's. There is no payment, Stripe, broker, or live-trading code
  anywhere in this build.
- **Tests:** 124 pass (112 + 12 new challenge tests, stubs only —
  no test touches the network). The YES and NO flows were also
  verified end to end in the rendered app (AppTest): YES placed a
  paper trade with `source="challenge"` and counted 1/30; NO logged
  the decision with its reason and placed nothing. Streamlit smoke
  run: HTTP 200, no errors.

## 23. Phase 5 — Trend-following & stress test (done 2026-11-09)

Two paper-only tests (`vaulttec/analytics/trend_and_stress.py`,
report in `validation/`). This is a validation step, not the
commercial Phase 5 in the roadmap — the name collides, the work
does not.

- **Test (a) — trend-following complement.** SMA crossover
  (SMA-10 cross above SMA-30) and MACD crossover (MACD cross
  above its signal line), exactly as defined in
  `analytics/backtest.py`, with wide-6 exits (6% stop / 9%
  target, 1.5:1, 10-day exit), on OOS-1/2/3, the Phase 4 window
  (re-run, in-sample), and FRESH-1/2/3. Same 12 symbols, delayed
  real yfinance history, 70 days warm-up, no look-ahead, real
  PaperTradingEngine + Risk Engine, $10,000 virtual cash,
  long-only. One deliberate method difference, stated in the
  report: trend entries are checked on EVERY bar, not every 5
  days, because a crossover is a single-bar event a 5-day step
  would miss; mean-reversion triggers are persistent states, so
  the 5-day step still catches them. Trade counts are therefore
  not directly comparable between trend and mean-reversion — P&L,
  win rate, and expectancy per trade are the comparison.
  Verdict rule, fixed before the run: a trend strategy "beats
  mean-reversion in OOS-2" when its OOS-2 P&L is greater than
  BOTH mean-reversion wide-6 OOS-2 figures (RSI +$63.26,
  Bollinger +$482.00).
- **Result (a): neither trend strategy beats mean-reversion in
  the falling window.** SMA wide-6: OOS-2 +$305.05 (27 trades,
  51.9% win) — beats RSI, not Bollinger; pooled OOS +$314.89
  (84 trades, 50.0%), pooled fresh +$351.50 (73 trades, 58.9%).
  MACD wide-6: OOS-2 +$223.23 (68 trades, 51.5% win) — beats
  RSI, not Bollinger; pooled OOS +$1,432.96 (191 trades, 52.4%),
  which misses beating RSI's pooled +$1,441.19 by $8.23;
  pooled fresh +$2,899.45 (174 trades, 60.9% win, positive 3/3
  windows) — beats both mean-reversion fresh figures (RSI
  +$1,226.24, Bollinger +$1,043.47). Phase-4 in-sample: SMA
  +$349.44 (27 trades, 51.9%), MACD +$249.10 (51 trades, 45.1%).
  All 7 windows pooled: SMA +$1,015.83 (184 trades, 53.8%),
  MACD +$4,581.51 (416 trades, 55.0%, positive 7/7). MACD
  fires far more often than SMA, including in downtrends when a
  steady fall's momentum decelerates — a real MACD behaviour,
  covered by a test, and a reason its fresh strength against
  OOS mediocrity reads as a regime warning, not a solved
  problem. No symbol failed in any window; 0 trades blocked
  by risk.
- **Test (b) — stress test on FRESH-4.** Wide-6 mean-reversion
  (RSI + Bollinger, baseline and wide-5 as controls, Phase 4d
  method, 5-day steps) on FRESH-4: 2022-09-12 → 2023-03-10, a
  180-calendar-day window ending the day FRESH-3 starts, so it
  overlaps no window used before. Verdict rule, fixed before
  the run: wide-6 "holds up" when FRESH-4 P&L > $0 AND win
  rate > 40% — a single window, so weaker evidence than the
  Phase 4d three-window rule.
- **Result (b): split.** RSI wide-6 holds up: 32 trades, 50.0%
  win, **+$651.89** (expectancy +$20.37/trade), best variant on
  the window (baseline +$424.31, wide-5 +$302.41 — all three
  hold up). Bollinger wide-6 does not: 14 trades, 35.7% win,
  **+$3.24** — essentially break-even, below the 40%
  break-even win rate, on a small trade count; Bollinger
  baseline was best there (+$123.22, 50.0% win) and the only
  Bollinger variant holding up. Wide-6 mean-reversion now has
  4 fresh windows of evidence for RSI (FRESH-1/2/3 + FRESH-4,
  all positive) and 3 of 4 for Bollinger.
- **Related work:** a parallel Phase 4e run tested a different
  trend entry (close > SMA-20 > SMA-50, a persistent state) on
  FRESH-1/2/3 only, from cache: wide-6 422 trades, 61.8% win,
  +$5,163.64 pooled fresh. It did not cover OOS-2, so it cannot
  answer the falling-window question either.
- **Verdict: keep wide-6 mean-reversion as the lead, keep MACD
  trend-following as a complement worth watching, do NOT move to
  real money.** Trend-following does not solve the falling
  window — Bollinger mean-reversion was better there — and one
  more single-window stress check does not prove the next
  window. Next step is live paper trades over real days, then a
  compliance/legal review. 141 tests pass (124 + 13 new Phase 5
  tests + 4 Phase 4e tests, stubs only — no test touches the
  network). Re-run:
  `python -m vaulttec.analytics.trend_and_stress`.

## 24. Private live trading — Neko only (built 2026-11-09)

A SEPARATE module, `vaulttec/private_live/`, for Neko's own money
only — not the public product, not for customers, no other
people's money. It does not touch the public sales site, the
Challenge Trial, or the live-paper cron runner; it only reuses
the shared Risk Engine and the mean-reversion trigger.

- **Broker:** Alpaca via plain REST (stdlib `urllib` only, no
  SDK to install). Paper endpoint first
  (`https://paper-api.alpaca.markets`); live endpoint is a
  separate explicit flag. Keys ONLY from `.env`
  (`ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `ALPACA_PAPER=true`
  by default) — never invented, never hardcoded, never logged.
- **Live gate — three locks, all required:** (1)
  `VAULTTEC_LIVE_TRADING_ENABLED=true`, (2)
  `ALPACA_PAPER=false`, (3) `private_live/LIVE_CONFIRMATION.txt`
  containing the exact confirmation line. A missing lock raises
  `LiveTradingRefused` naming the lock — nothing is placed.
- **Strategy:** wide-6 only (6% stop / 9% target, 1.5:1, RSI +
  Bollinger, long-only, 10-bar time exit), stocks first, crypto
  (BTC/USD, ETH/USD) where Alpaca supports it.
- **Orders:** bracket orders by notional (fractional shares), so
  the stop and target live at the broker. Every proposal is
  risk-checked through the shared Risk Engine first.
- **Approval first:** default mode only proposes trades; Neko
  approves by id (`approve` / `approve-all`). Supervised
  automation needs a separate opt-in file
  (`automation-enabled.json`, `{"enabled": true,
  "confirmed_by": "Neko"}`) — `--auto` without it places nothing.
- **Small capital, honestly sized:** 10% position cap, 2% risk
  cap per trade. On $50 that is a $5.00 position, $0.30 risked,
  $0.45 targeted; on $20, $2.00 / $0.12 / $0.18. Positions below
  Alpaca's ~$1 minimum notional are skipped and logged.
  At the Phase 4d fresh-window rate (~+10–12% per 180 days on
  $10,000), $50 makes roughly $5–$6 in six months — a test
  amount, not a funding plan for attorney fees. The README says
  so in plain language.
- **Kill-switch:** `private_live/STOP` — scan/approve refuse
  while it exists. Logging: `trades.jsonl` (append-only),
  `proposals.json`, `state.json`, `report.md` (regenerated).
- **Modes:** dry-run (no keys — signals and proposals only,
  orders recorded as "NOT placed"), paper (real Alpaca paper
  account, fake money), live (three locks open).
- **Runbook:** `vaulttec/private_live/RUNBOOK.md` — Alpaca
  paper account creation, keys, dry-run, paper, automation,
  live, kill-switch. Neko creates the Alpaca account and does
  identity verification himself; no account was created, no
  real order placed, no real money moved in this build.
- **Tests:** 20 new tests in `tests/test_private_live.py`
  (faked broker transport, stub market data — no test touches
  the network). Full suite: **161 passed**. A dry-run smoke
  scan on 2026-11-09 produced 5 proposals (NVDA, SPY, GOOGL,
  META, ETH-USD) at $50 sizing, placed none, and an approve of
  one proposal recorded it via the dry-run broker. One bug
  found and fixed in testing: quantity was rounded up, pushing
  two trades a fraction of a cent over the 10% cap — quantity
  is now floored.
- **Live-paper evidence is still thin:** Day 1 (2026-11-09)
  — 3 trades open (GOOGL, META, ETH-USD), 0 closed, $0.00
  realised. Do not scale up on backtests alone.

## 15. How to run (Phase 1)

```bash
cd vaulttec
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501). All trading is paper trading with virtual cash.
