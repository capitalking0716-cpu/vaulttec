# VaultTec — Intraday Live Paper Trading (market hours, paper only)

The market-hours twin of the daily live-paper runner. Same wide-6
rules (6% stop / 9% target, 1.5:1, RSI + Bollinger, long-only,
balanced profile), but on **hourly bars** during the market session
(9:30am–4:00pm ET), in its own state dir
(`live_paper_intraday/`) with its own **$10,000 virtual pot**.
Intraday numbers never mix with the daily runner's state.

## Schedule (recommended — see the cron spec)

Hourly runs weekdays, one per completed hour:

- 10:35 — processes the 9:30 bar
- 11:35 — processes the 10:30 bar
- 12:35 — processes the 11:30 bar
- 13:35 — processes the 12:30 bar
- 14:35 — processes the 13:30 bar
- 15:35 — processes the 14:30 bar
- 16:35 — processes the final 15:30 bar and delivers the **session
  report** (wins and losses that closed in the session, total
  profit so far, open positions listed as still open).

Times are :35 past the hour, not :30, so a run dispatched a few
minutes early still lands after the bar has fully ended. A missed
hour is picked up by the next run — the runner is idempotent per
hour.

## Run it by hand

```bash
cd ~/workspace/goals/5-ai-operated-companies-at-10k-month-each/files/vaulttec
.venv/bin/python -m vaulttec.intraday_paper_trading
# or for a specific time:
.venv/bin/python -m vaulttec.intraday_paper_trading --datetime 2026-11-10T14:35
# session report only (no fetch, no trades):
.venv/bin/python -m vaulttec.intraday_paper_trading --session 2026-11-10
```

## How it works

- Each run fetches the last 60 days of hourly bars (the most
  yfinance serves at 1h) for the same 12-symbol universe, keeps
  only bars that start inside the session (9:30am–3:30pm NY), and
  processes every completed hourly bar not yet processed, in
  order. A bar is complete only when its hour has fully ended.
- Per bar, per symbol: exit check first (stop on the bar's low,
  target on the bar's high, then the 10-SESSION time exit), then
  the RSI/Bollinger trigger on history up to and including that
  bar only — no look-ahead. Triggers use the session-only hourly
  series (7 bars a day for stocks, 6 for crypto, whose Yahoo
  hourly bars start on the hour).
- The 10-bar time exit is measured in sessions: a position exits
  at the first processed bar of its 11th session (10 full
  sessions held). Ten hourly bars would close a trade after ~1.5
  sessions, which would contradict the multi-day-hold reality.
- The daily-loss limit resets once per session, not per bar.

## Honest limits

- Wide-6 was validated on DAILY bars, not hourly ones. RSI-14
  means 14 hours here. Intraday results are an experiment.
- A 6%/9% exit almost never triggers inside one session — most
  wins/losses come from multi-day holds. The session report
  counts ONLY trades that closed in that session. Open positions
  are listed with unrealised value, clearly labelled, and are
  NEVER wins or losses.
- Yahoo's free intraday data is delayed ~15 minutes and rate
  limits are the known failure mode. A fetch failure is recorded,
  never replaced with sample data, never invented. A missed hour
  is picked up by the next run.
- Crypto trades 24/7, but this runner only watches the
  9:30–4:00 ET session. Overnight crypto bars are ignored.

## Kill switch

Create `live_paper_intraday/STOP` (or set `enabled` to false in
`state.json`) and the next run does nothing except log that it
was stopped. Delete the file to resume. Open positions stay open
until the runner is resumed and their exit bars arrive.

## Files

- `state.json` — cash, open positions, closed trades, last
  processed bar per symbol (ISO timestamps), run history.
- `trades.jsonl` — one JSON line per decision.
- `live-paper-intraday-report.md` — regenerated each run,
  including the latest session's wins/losses/total profit.
