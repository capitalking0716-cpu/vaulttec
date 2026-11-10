# Ava upgrade — Check My Move + small-wins watch (2026-11-10)

Ava is now a sharper trading chatbot, not just a paper-trading
runner. She checks the move Neko is about to make *before* he makes
it, calls a bad play a bad play, and pushes him to bank small wins
fast. Everything works offline first — the LLM only adds flavour
when the brain is online.

## What changed

**1. Personality — same Ava, sharper voice (`vaulttec/ava/ava.py`)**

- System prompt rewritten: straight, plain, short. A bad play is a
  bad play — say it plainly, say why, say what to do instead. A
  banked small win is a win — say so briefly, then move on. Aggressive
  about banking small wins: a 4–5% gain in hand beats a 9% target
  that never comes. Never chases, never widens a stop, never holds
  out for a home run.
- Her brief and her offline answers now carry the small-wins watch,
  so the push to bank wins shows up every time she speaks.
- Hard rules unchanged: risk first, never promises profits, never
  places a trade, Neko decides YES or NO on everything.

**2. Check My Move — new (`vaulttec/ava/move_check.py` + Results tab
in `app.py`)**

- A form in the Results tab under Ava: symbol, buy/sell, shares,
  entry price, stop-loss, take-profit, and what he thinks the setup
  is. One button: "Ask Ava — is this a good play?"
- She checks the move against, in order:
  - the wide-6 rules (RSI < 30 or price at the Bollinger lower band,
    from the last completed daily bars — a chase is flagged);
  - the risk limits, through the same RiskEngine the paper trades
    use (stop present and on the right side, size inside the profile
    cap, concentration, exposure, risk/reward ≥ 1.5:1, daily loss
    limit);
  - his current open paper positions (live_paper state + the app's
    open trades, deduplicated by symbol);
  - pending private-panel proposals for the same symbol;
  - her lessons from closed trades on that symbol;
  - the small-win rule (a target over 15% is a home run — bring it
    down to the 9%; a stop wider than 6% gets tightened).
- Verdict: **good play / fix this first / bad play**, with the reason
  in plain language and exactly what to change. Sells are judged as
  exits: banking a win at least halfway to target is a good play,
  cutting past the stop is a good play, cutting early out of fear is
  flagged, selling a name he doesn't hold is a bad play (we don't
  short). Leverage and options in his own setup text are a bad play.
- When prices can't be fetched, the setup is "unknown" and the
  verdict is capped at "fix" — she never blesses a trade she can't
  see. A fetch failure is reported, never replaced with sample data.

**3. Small-wins watch — new (`vaulttec/ava/small_wins.py` + Results
tab in `app.py`)**

- Scans his open positions on every Results view and flags:
  - **Bank it** — up at least halfway to the 9% target, or the
    target is hit. A small win in hand beats a target that never comes.
  - **Slipping** — was up 5%+ and has given back more than 40% of
    the win (needs recent history; otherwise skipped, never guessed).
  - **Cut it** — past the stop. **Drifting** — down 3%+, heading for
    the stop. **Too much in one name** — over the 25% concentration cap.
- Shows in her brief, her offline answers, and its own section
  ("💰 Small wins — what to bank, what to cut") under Check My Move.

## Files

- `vaulttec/ava/move_check.py` (new) — the check, the live-paper
  and private-proposal loaders, the verdict renderer.
- `vaulttec/ava/small_wins.py` (new) — the watch.
- `vaulttec/ava/ava.py` — sharper voice, `Ava.check_move()`,
  `Ava.small_wins_watch()` / `Ava.small_wins_flags()`.
- `vaulttec/ava/__init__.py` — new exports.
- `app.py` — Check My Move form + verdict, Small wins watch (Results tab).
- `tests/test_ava_move_check.py` (new, 20 tests) — good RSI and
  Bollinger buys pass; chase, no-stop, wrong-side stop, oversized,
  home-run target, short, leverage, unknown setup all flagged;
  sell exits; lessons and proposals surfaced; offline verdict text.
- `tests/test_ava_small_wins.py` (new, 9 tests) — bank it, target
  hit, cut it, drifting, slipping, steady win not flagged, over-
  concentration, no price means no flag, summary text.

## Tests

`.venv/bin/python -m pytest -q` → **317 passed** (was 288; +29 new).
Nothing else changed. `app.py` compiles clean.

## What still needs the key fixed

Ava's brain is still **offline** (status line: "Brain offline").
Everything above works without the key — the trade check, the
watch, and her offline answers are pure logic on real app data.
What the key buys is *flavour*: when the brain is online, the same
verdict is restated by the model in her voice (the verdict itself
never changes). Until the PC secrets file is fixed (three lines:
`AVA_API_KEY`, `AVA_BASE_URL`, `AVA_MODEL` — plus an app restart),
she stays in clearly-labelled offline mode and never pretends to
think. Do not sell or promise anything on the basis of an offline
answer she has not verified.

## Honest limits

- The setup check uses the last *completed* daily bars; intraday
  moves are not covered. If Yahoo blocks the fetch, the setup is
  "unknown" — the risk checks still run, but she will not bless it.
- The small-wins watch uses last completed closes, not live ticks.
  A win can move between runs; the watch only sees what the state
  file and the app's quotes say.
- The check reads the durable live-paper state (daily $10k pot) and
  the pending private proposals. The intraday pot is a separate
  experiment and is not merged into the check.
- Live Stripe verification of nothing here — this is paper trading
  only. The live locks are untouched. No auto-trading was added:
  Ava advises, Neko decides YES or NO, every time.

## Push status

These files are **not pushed**. They join the 14-file push already
awaiting Neko's answer: `vaulttec/ava/move_check.py`,
`vaulttec/ava/small_wins.py`, `vaulttec/ava/ava.py`,
`vaulttec/ava/__init__.py`, `app.py`,
`tests/test_ava_move_check.py`, `tests/test_ava_small_wins.py`,
`validation/ava-upgrade-note.md` (+ tests still need a re-run on the
PC after pull, since the PC copy is the one that runs).
