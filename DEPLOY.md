# VaultTec — How to host the web version (Streamlit Community Cloud, free)

The app in this folder is the full VaultTec trading app (Phases 1–3, paper
trading only). VaultTec is for DAY TRADING stocks AND CRYPTO — day-trading
focus and day-trading strategies front and center, covering stocks and
cryptocurrency, not general long-term investing.
It is ready to deploy. Deploying needs two accounts Neko
must create/sign into himself — Muse cannot create them for him:

1. **GitHub** (free) — to hold the code.
2. **Streamlit Community Cloud** (free) — to run the app on the web.

No money is needed for either. No broker, no API key, no paid data feed.

## Step 1 — Put the code on GitHub

From this folder, on a PC with git installed:

```bash
cd vaulttec
git init
git add .
git commit -m "VaultTec Phases 1-3: paper trading app"
```

Then on github.com, create a **new public repository** called `vaulttec`
(do not add a README/license there — this folder already has them), and:

```bash
git remote add origin https://github.com/<your-github-username>/vaulttec.git
git branch -M main
git push -u origin main
```

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in **with GitHub**.
2. Click **Create app** → pick repository `vaulttec`, branch `main`,
   main file `app.py`.
3. Click **Deploy**. The app builds for a minute or two, then gives you a
   public URL like `https://vaulttec.streamlit.app` — that is the web
   version, openable on PC, iPad, and phone.

## Step 3 — Set your login (so only you can use it)

The app has a login gate that is **off** until a password is set. To turn
it on, in Streamlit Cloud open the app's **Settings → Secrets** and add:

```toml
VAULTTEC_LOGIN_PASSWORD = "the password you choose"
```

Then reboot the app. From then on the web app asks for:

- Email: `capitalking0716@gmail.com`
- Password: the password you put in Secrets

Choose the password yourself, in Streamlit's Secrets page — never type it
in chat, never put it in any file in this repo, and never share it.
If you ever forget it, change it in Secrets and reboot the app.

Without a secret set, the app opens with no login (local use). With a
secret set, nobody can open the dashboard without your email + password.

**The "My Private Trading" section needs this password.** It stays
hidden — no proposals shown, no approvals possible — until
`VAULTTEC_LOGIN_PASSWORD` is set. That is deliberate: your private
trades must never be visible on a password-less app.

## Step 4 — Use it on your phone (My Private Trading)

Honest limit first: **until the app is deployed and hosted, it only
runs on a local PC at http://localhost:8501 — you cannot open it on
your phone yet.** Phone access needs the hosted deploy above
(GitHub + Streamlit Cloud). Once it is deployed, the phone steps are:

1. On your phone, open the deployed URL (e.g.
   `https://vaulttec.streamlit.app`) in your phone's browser.
   Bookmark it / add it to your home screen for one-tap access.
2. Sign in with email `capitalking0716@gmail.com` and the password
   you set in Secrets (Step 3).
3. Scroll to **🔒 My Private Trading — Neko only** (near the bottom,
   after Live paper trading). It is built phone-first: large
   buttons, one column, no wide tables.
4. Tap **🔍 Scan for trades** — proposals only, nothing is placed.
   Each proposal is a card: symbol, entry, stop, target, dollars
   at risk / dollars targeted.
5. Tap **✅ APPROVE** on one proposal to place it, or **❌ REJECT**
   to skip it. Nothing is placed until you tap Approve on that
   proposal.
6. **🛑 KILL SWITCH** stops all private trading at once; clear it
   from the same section to resume.

### Alpaca paper keys (for real paper trading, not just dry-run)

Dry-run mode (no keys) shows proposals and records approvals as
"dry-run — NOT placed". To trade against a real Alpaca **paper**
account (fake money, real broker mechanics), add to the same
Secrets page in Step 3:

```toml
ALPACA_API_KEY = "your Alpaca paper key"
ALPACA_SECRET_KEY = "your Alpaca paper secret"
ALPACA_PAPER = "true"
```

Get those keys by creating your own Alpaca account at
https://alpaca.markets and generating a **paper** key pair in the
Alpaca dashboard — Muse cannot create that account or those keys
for you, and they must never be typed in chat or put in any file
in this repo.

**Live trading is NOT enabled from the phone or the app.** It stays
locked off unless all three locks are opened by hand:
`VAULTTEC_LIVE_TRADING_ENABLED=true` in Secrets, `ALPACA_PAPER`
set to `false`, and the file `private_live/LIVE_CONFIRMATION.txt`
created with the exact confirmation text (see
`vaulttec/private_live/RUNBOOK.md`). The app's "Check live trading
gate" button only reports which locks are still closed — it never
opens them. Do not open live trading until paper runs clean over
real days and you have said so explicitly.

## What the hosted app does / does not do

- Paper trading ONLY, with $10,000 virtual cash. No live brokerage, no
  real money, no leverage, no options.
- Coaching first (5 coached paper trades), graduation only when you
  confirm it, then supervised automation — paper only, inside your profile
  limits, with an emergency stop.
- Sample data by default (offline demo data, clearly labelled). Delayed
  real prices are available by setting `VAULTTEC_DATA_PROVIDER=yfinance`
  in Secrets — still paper trading only.
- Risk disclosure on every view. Never promises profits; past performance
  never guarantees future results.
- One user at a time in practice: the hosted app's paper portfolio is
  shared by anyone who logs in, so keep your password to yourself.

## If you don't want GitHub / Streamlit Cloud

The Muse web version (built as a VaultTec web app in Muse) works now, with
its own first-use password setup, and has the same dashboard, coaching,
paper trading, risk engine, scanner, backtests, and assistant — sample
data only. The Streamlit version above is the full app; the Muse web
version is the fastest way to use it on the web today.
