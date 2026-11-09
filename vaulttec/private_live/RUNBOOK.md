# VaultTec PRIVATE — Runbook (Neko only)

> **PRIVATE — Neko only. Not the public VaultTec product. No
> customers, no other people's money. Trading involves substantial
> risk of loss. No profit is promised. Past performance does not
> guarantee future results.**

## Step 0 — What you need

- A computer with this `vaulttec/` folder and its `.venv`
  (the same one the Streamlit app uses).
- An Alpaca account — **you create this yourself, in your
  browser**. Muse cannot create a brokerage account for you and
  cannot pass your identity verification.
- About 15 minutes for the paper setup. Live setup is a separate
  step, later, only when you say so.

## Step 1 — Create an Alpaca paper account (you do this)

1. Go to **https://alpaca.markets** in your browser.
2. Sign up with your email and a password **you** choose.
   (Do not share the password with anyone, including in chat.)
3. Complete Alpaca's identity verification for a paper account.
   Paper trading is free and uses fake money.
4. In the Alpaca dashboard, go to **Paper Trading → API Keys**
   (or "Your API Keys") and generate a paper API key pair.
   You will see a **Key ID** and a **Secret Key**.
   - The secret is shown once — copy it immediately and keep it
     somewhere safe. Do not paste it in chat, in a file that
     gets shared, or in any message.

## Step 2 — Put the keys in `.env` (you do this)

In the `vaulttec/` folder, copy `.env.example` to `.env` if you
have not already, and add:

```ini
ALPACA_API_KEY=<your paper Key ID>
ALPACA_SECRET_KEY=<your paper Secret Key>
ALPACA_PAPER=true
VAULTTEC_LIVE_TRADING_ENABLED=false
```

- `.env` is git-ignored and is never committed. Never put keys
  in code, in a report, or in chat.
- `ALPACA_PAPER=true` is the default. Leave it there until the
  live step below.

## Step 3 — Dry-run first (no keys needed)

Before the keys even exist, test the logic:

```bash
cd vaulttec
.venv/bin/python -m vaulttec.private_live.runner scan --account-value 50
.venv/bin/python -m vaulttec.private_live.runner status
```

- This scans the latest completed bar per symbol and writes
  **proposals only** — nothing is placed, because there is no
  broker. The report is at `vaulttec/private_live/report.md`.
- `--account-value 50` sizes proposals for a $50 account
  ($5.00 per position, $0.30 risked). Use 20 for a $20 account.

## Step 4 — Paper mode (keys set, still fake money)

```bash
cd vaulttec
.venv/bin/python -m vaulttec.private_live.runner scan
```

- With keys set, the runner reads your real Alpaca **paper**
  account value and sizes positions from it.
- It still only **proposes**. To place a proposal:

```bash
.venv/bin/python -m vaulttec.private_live.runner approve --id PROP-2026-11-09-AAPL
```

- Or approve everything pending:

```bash
.venv/bin/python -m vaulttec.private_live.runner approve-all
```

- Every proposal is risk-checked again at approval time. A
  blocked trade is logged, never placed.
- Check what happened:

```bash
.venv/bin/python -m vaulttec.private_live.runner status
```

- The log is `vaulttec/private_live/trades.jsonl` — every
  proposal, approval, order, and exit, in order.
- Run the scan **once a day, after the market close** (or the
  next morning before the open). It only trades completed bars,
  so a mid-day run would miss the day's bar anyway.

## Step 5 — Supervised automation (optional, paper first)

Automation is OFF by default and stays off until you opt in
explicitly. To opt in, create
`vaulttec/private_live/automation-enabled.json` by hand with:

```json
{"enabled": true, "confirmed_by": "Neko"}
```

Then:

```bash
.venv/bin/python -m vaulttec.private_live.runner scan --auto
```

- Proposals are placed immediately, still through the Risk
  Engine, still as bracket orders with broker-side stops.
- To turn it off, delete that file — or create the STOP file
  (Step 7). Automation never bypasses the Risk Engine.

## Step 6 — Live mode (ONLY when you explicitly say so)

Live is three locks, all three must be open:

1. In `.env`, set `VAULTTEC_LIVE_TRADING_ENABLED=true` **and**
   `ALPACA_PAPER=false`.
2. In Alpaca, generate a **live** API key pair (separate from
   the paper keys) and put those in `.env` instead of the paper
   ones. Live keys and paper keys are different — do not mix
   them up.
3. Create `vaulttec/private_live/LIVE_CONFIRMATION.txt` by hand
   containing exactly this line:

   ```
   I, Neko Robinson, confirm I want VaultTec PRIVATE to trade live with my own real money. I understand I can lose money.
   ```

If any lock is missing, the runner **refuses** to place a live
order and says which lock is closed. Paper mode keeps working.

Before you flip live, the honest checklist:

- [ ] Paper mode has run cleanly for real days (fills work,
      stops fire, the log matches Alpaca's dashboard).
- [ ] The public live-paper run has closed trades — not just
      open ones — so there is real evidence, not just backtests.
- [ ] You have read the maths in README.md: $20–$50 risks
      $0.12–$0.30 per trade. Live money at that size is a test,
      not a funding plan.
- [ ] You are using money you can afford to lose. Never trade
      money you need for rent, bills, or the attorney.

## Step 7 — Kill it instantly

```bash
.venv/bin/python -m vaulttec.private_live.runner kill
```

Or create the file `vaulttec/private_live/STOP` yourself. While
it exists, `scan` and `approve` refuse to do anything. Open
positions stay open at the broker (their bracket stops still
protect them) until you resume. Delete the file to resume.

To close a position at the broker immediately, use the Alpaca
dashboard (Positions → Close), or ask Muse — do not delete
state files by hand.

## Step 8 — What to check after each run

1. `vaulttec/private_live/report.md` — mode, account value,
   open positions, pending proposals.
2. `vaulttec/private_live/trades.jsonl` — the full decision log.
3. The Alpaca dashboard — your paper/live positions and orders
   should match what VaultTec logged. If they ever disagree,
   stop and tell Muse before running again.

## Troubleshooting

- **"Alpaca API keys are missing"** — the `.env` file is not
  being read, or the keys are not in it. Check you are in the
  `vaulttec/` folder and the file is named exactly `.env`.
- **"Live trading refused"** — one of the three live locks is
  closed. The error message names which one. This is the safety
  working, not a bug.
- **A symbol is skipped / fetch failed** — the Yahoo data feed
  (used for signals) was blocked or returned nothing. The runner
  logs it and does not trade that symbol that day. It never
  invents a price.
- **A proposal is "blocked"** — the Risk Engine refused it
  (position too big, exposure, daily loss limit, or a bad
  risk/reward). Read the reasons in `trades.jsonl`. Do not
  override a block.
- **A crypto order is rejected by Alpaca** — crypto availability
  and fractional rules can change. The runner logs it and skips
  it. Stocks keep working.
