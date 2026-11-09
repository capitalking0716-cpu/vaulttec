# VaultTec — Live Paper Trading Runbook

> **PAPER ONLY — virtual money, no live brokerage, no real money.**
> Trading involves substantial risk of loss. This live paper run does
> not promise profits. Past performance does not guarantee future results.

## What this is

The live paper runner trades the wide-6 rules (6% stop / 9% target,
1.5:1, 10-bar time exit, RSI + Bollinger mean-reversion, long-only,
balanced profile, $10,000 virtual cash) one day at a time, on delayed
real prices from yfinance as they arrive. It is the step Phase 4d
called for: prices arrive one day at a time and cannot be re-run.

## Run one day (the daily command)

From the `vaulttec/` folder, in the project virtualenv:

```bash
cd ~/workspace/goals/5-ai-operated-companies-at-10k-month-each/files/vaulttec
.venv/bin/python -m vaulttec.live_paper_trading
```

That runs **today** (America/New_York date). To re-run a specific
date (for example after a missed day — the runner catches up
automatically, so this is rarely needed):

```bash
.venv/bin/python -m vaulttec.live_paper_trading --date 2026-11-10
```

Exit codes: `0` = ran fine (including "already processed" and
"stopped by kill-switch"); `2` = every symbol failed to fetch, no
state change.

## How the daily schedule should work

- **When:** once a day, after the market close is known. Recommended:
  **weekdays at 17:00 EST (America/New_York)** — after the 16:00
  close, so the day's stock bar is complete — or any time the next
  morning before the open (the runner only trades *completed* bars,
  so a morning run processes yesterday's bar). Either time works;
  pick one and stick to it. Do **not** run it mid-day: the current
  day's bar is still forming and will be skipped until tomorrow.
- **What the scheduler must do:** run the command above once per
  day. That is all — no cron is set up in this folder (the parent
  agent sets the schedule). The runner is idempotent: a second run
  on the same day finds no new completed bars and changes nothing.
- **Weekends / holidays:** nothing special to do. Stocks have no
  new bar, so the runner logs "no new bar" for them and moves on;
  crypto (BTC-USD, ETH-USD) trades every day, so weekend runs can
  still open/close crypto positions. A market holiday is the same:
  logged and skipped, never traded on.
- **Yahoo Finance approvals:** the first runs ask for network
  permission to `query1/query2.finance.yahoo.com` (one approval per
  fetch, in the foreground). Approve them while awake — if they time
  out, the fetch fails, the symbol is recorded as failed, and the
  run continues with the symbols that did fetch. A total fetch
  failure exits non-zero with no state change.

## What the runner does each day, in order

1. If `live_paper/STOP` exists (or `enabled` is false in
   `state.json`): log "stopped" and do nothing — no fetch, no trades.
2. Fetch the last ~280 days of delayed real history per symbol
   (yfinance, retries 3 times). A symbol that cannot be fetched is
   recorded and skipped — never replaced with sample data, never
   invented.
3. For each symbol, process every completed bar (date before the run
   date) not yet processed, in order. The first ever run treats all
   earlier bars as warm-up and processes only the latest completed
   bar as its first trading day.
4. Per bar: exit check first (stop-loss on the bar's low, then
   take-profit on the bar's high, then the 10-bar time exit), then
   entry check (RSI < 30, then Bollinger lower band) on history up
   to and including that bar only — no look-ahead. Every entry goes
   through the real PaperTradingEngine and Risk Engine.
5. Save state atomically, append every decision to the log, and
   regenerate the report.

Two live-only guards (they cannot change any validated backtest
result, which used real prices): a position that exits on a bar is
never re-entered on that same bar, and a Bollinger trigger needs a
real (non-zero-width) band — a flat line is not a bounce.

## Files to check

| File | What it is |
|---|---|
| `live_paper/state.json` | Durable state: cash, open positions, closed trades, last processed bar per symbol, run history. The single source of truth. |
| `live_paper/trades.jsonl` | Append-only log: one JSON line per decision (trade opened/closed/blocked/skipped, fetch failure, run summary). |
| `live_paper/live-paper-report.md` | Human-readable running report, regenerated every run: portfolio, win rate, P&L, open/closed trades, run history. |
| `live_paper/RUNBOOK.md` | This file. |
| `live_paper/STOP` | Kill-switch file (only exists when stopped). |

## How to read the report

- **Portfolio value** = virtual cash + open holdings at their last
  completed close. **Total realised P&L** is from closed trades only.
- **Win rate** — break-even at 1.5:1 is 40%. Judge by expectancy
  (P&L per trade) as well as win rate: a high win rate with small
  wins can still lose money.
- **Open positions** show entry, stop, target, and bars held (10 =
  time exit on the next bar).
- **Run history** shows each day's status: `ok`, `already_processed`
  (no new bars — normal on a second run or a holiday), `stopped`,
  or `fetch_failed`.

## How to stop it (kill-switch)

Create the stop file — the next run will log "stopped" and do
nothing (no fetch, no trades). Open positions stay open until the
runner is resumed:

```bash
touch live_paper/STOP
```

Resume by deleting it:

```bash
rm live_paper/STOP
```

## How to restart from scratch (only if the test itself is abandoned)

Delete the state (the log and report are history — keep or delete
them separately). The next run starts over at $10,000 with no
positions, treating its latest completed bar as day one:

```bash
rm live_paper/state.json
```

Do not do this to "fix" a losing run — the losses are the data.

## What this does NOT do

- No broker is contacted. No brokerage account exists. No real
  money moves. No leverage, no options. The stop-loss is never removed.
- No prices are invented. A failed fetch means that symbol is not
  traded that day.
- A good live paper run does **not** mean real money is safe. A
  compliance/legal review is still required before real money is
  ever considered.
