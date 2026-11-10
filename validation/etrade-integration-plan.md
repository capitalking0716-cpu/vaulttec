# E*TRADE integration plan — VaultTec private version

**Status: design + sandbox broker built and tested. No live order exists.
No keys exist. Nothing here touches real money.**

This is the plain-language plan for adding Neko's E*TRADE account to
VaultTec's private version, alongside Alpaca. Alpaca stays as it is —
nothing here changes the Alpaca setup.

> **No profit is promised.** Paper results do not predict real results.
> Trading can lose money. Everything below is about getting a second
> broker connected safely, not about making money.

---

## 1. What E*TRADE actually offers

E*TRADE has a free developer program. It lets your own software talk
to your own E*TRADE account: see your accounts, balances and stock
positions, get prices, and place and cancel stock orders.

- **Cost:** the API itself is free. Online US stock and ETF trades are
  $0 commission.
- **What you can do through it:** list accounts, check balance,
  see positions, get quotes (up to 50 symbols at once), list orders,
  preview an order, place an order, cancel an order.
- **What you cannot do through it:** trade crypto (stocks only),
  place a bracket order (buy + stop + target in one order — the
  website has this, the API does not), or buy a dollar amount.
- **Speed limit:** 120 requests per minute per key — far more than
  VaultTec needs for a daily scan.
- **Where this was checked:** E*TRADE's own developer site
  (developer.etrade.com — getting started, developer guides, FAQ)
  and E*TRADE's own API docs (apisb.etrade.com), plus E*TRADE's help
  pages. No third-party blog was taken as fact where E*TRADE's own
  docs said something.

## 2. The two kinds of access: sandbox first, live later

- **Sandbox** (test mode, `apisb.etrade.com`): a pretend version with
  canned test data — 4 test accounts with old (2013) sample data and
  no real trades. It proves your code and your keys work. It does
  **not** prove a real order would fill, and it never sees your real
  account. **VaultTec is built to use the sandbox by default.**
- **Production** (live, `api.etrade.com`): your real account, real
  money. Sandbox keys and live keys are different — one cannot be
  used on the other.

**You need two different keys:** one for sandbox (to test), one for
live (only after the sandbox works and the legal review is done).
Getting them is free; E*TRADE's FAQ says to allow a few business
days for a key to be issued.

## 3. How signing in works (different from Alpaca)

Alpaca uses a simple key and secret in every request. E*TRADE uses
**OAuth 1.0a** — every single request is signed with a code, and
getting access takes a short browser step:

1. VaultTec asks E*TRADE for a **request token** (it lives ~5 minutes).
2. **You** open an E*TRADE page in your browser, log in, and approve
   the app. E*TRADE shows you a short **verifier code**.
3. You paste that code into VaultTec. VaultTec trades it for an
   **access token**, which is saved on your PC only
   (`private_live/.etrade-tokens.json` — never pushed to GitHub,
   never emailed, never in chat).

Two hard limits E*TRADE sets, not VaultTec:

- **The access token dies at midnight US Eastern every night.**
  There is no refresh token. Every morning you want VaultTec to
  trade on E*TRADE, you repeat the short browser approval.
  (There is a "renew" call that wakes up a token that went quiet
  for 2 hours — but it cannot revive one past midnight.)
- **That daily re-approval is the price of using E*TRADE.** Alpaca's
  keys do not expire like this. If E*TRADE is the backup broker,
  this is a backup-broker chore, not a dealbreaker — but it is real.

## 4. The six big differences from Alpaca — in plain words

| | Alpaca (what we have) | E*TRADE (what this adds) |
|---|---|---|
| **Signing in** | Key + secret, never expires | OAuth 1.0a; token dies at midnight ET, daily browser approval |
| **Buy + stop + target** | One bracket order at the broker | **No bracket through the API.** VaultTec places the buy, then a separate stop-loss order. The take-profit target is **not** resting at the broker — VaultTec itself must watch the price and sell when the target hits |
| **How much you buy** | Any dollar amount (fractional shares) | **Whole shares only.** $5 buys a fraction of a $100 stock on Alpaca; on E*TRADE it buys **zero shares** and the trade is refused |
| **Fractional shares** | Yes, built in | The website allows them for some stocks, but **whether the API accepts them is unproven** — the sandbox preview call is the test. Until it passes, whole shares only |
| **Crypto** | BTC / ETH (paper) | **No crypto at all.** BTC and ETH stay on Alpaca |
| **Market hours** | Broker tells us if the market is open | No clock endpoint — VaultTec estimates from New York time (weekdays 9:30–4:00), holidays not covered |
| **Order safety** | Order goes straight in | **Preview is mandatory:** every order is previewed first (E*TRADE returns a preview ID), then placed. A bad symbol, bad size or not-enough-money fails at preview, before anything moves |
| **Which account** | One paper account | E*TRADE accounts are picked by an encrypted account key (`accountIdKey`). You have to tell VaultTec which of your accounts to use — it never guesses |

### The small-money problem — read this first

Because E*TRADE only sells whole shares, **the size of your account
decides what you can buy at all:**

- A $10 position buys **1 share of a stock that costs $10 or less**,
  and **0 shares of anything that costs more**.
- On a $100 account, the 10%-per-position rule means a ~$10 position
  — so only stocks under $10 are buyable, one share at a time.
- A $5 position in a $600 stock (like META) is refused outright.
  VaultTec says so in plain words instead of pretending it worked.
- How much is actually in your E*TRADE account is still unknown
  (you said ~10 stocks, amount unknown). That number decides whether
  E*TRADE can trade the wide-6 sizes at all. **Ask yourself: what is
  the account worth?** If it is a few hundred dollars, E*TRADE can
  only trade cheap stocks. If it is a few thousand, normal stocks
  open up, one share at a time.

This is the single biggest practical difference from Alpaca, and it
is why Alpaca stays the main broker for small money.

## 5. What was built

All in `vaulttec/private_live/`, mirroring the Alpaca broker so the
strategy and runner can use it unchanged (same method names, same
return shapes):

- **`etrade_oauth.py`** — the OAuth 1.0a signer, standard-library
  only (no new dependency). Proven against the worked example in
  the OAuth spec itself (RFC 5849 §3.4.1.3.2), so the signing math
  is verified without ever calling E*TRADE.
- **`etrade_broker.py`** — `ETradeBroker` (sandbox by default) and
  `ETradeDryRunBroker` (records what *would* be sent, places
  nothing — the E*TRADE twin of Alpaca's `DryRunBroker`), plus
  `ETradeConfig` and the same three-lock live gate with E*TRADE
  names (`ETRADE_LIVE_TRADING_ENABLED=true` +
  `ETRADE_SANDBOX=false` + the same `LIVE_CONFIRMATION.txt`).
- **Safety behaviour built into the broker:**
  - Crypto symbols are refused outright.
  - A position that buys 0 whole shares is refused with a plain
    explanation.
  - Every order is previewed before it is placed.
  - The entry and the stop are separate orders; if the entry fills
    and the stop then fails, the error says **UNPROTECTED** and
    names the entry order id so it can be fixed by hand.
  - A sell always cancels the resting stop first, so a filled sale
    never leaves a live stop that could fire against a position
    that is gone.
  - The live gate is closed by default; sandbox is the default.
- **`.gitignore`** now also ignores `private_live/.etrade-tokens.json`
  (the saved access token — owner-only file permissions, never
  committed).
- **`tests/test_etrade_broker.py`** — 31 tests, all passing.
  Fake-broker tests use canned sandbox-shaped responses, never the
  real API.

**Test result:** full suite **250 passed, 4 failed**. The 4 failures
are in `tests/test_private_panel.py` and are **pre-existing and
unrelated**: those tests expect proposal IDs dated 2026-11-09, but
today is 2026-11-10 and the runner stamps today's date. No E*TRADE
code is imported by the panel tests. (Baseline was 223 passing;
223 + 31 new = 254 total; 250 passed + 4 date-failing = 254.)

## 6. What you must do on your side — step by step (phone-first)

Do these yourself, in your own browser. **Never send the keys,
the secret, your E*TRADE login, the verifier code, or any
screenshot showing them to Shadow or anyone in chat.** The keys
go only into the app's Secrets / `.env` file on your own devices.

### Step A — get a sandbox key (test mode)

1. On your phone, open Chrome and go to **us.etrade.com** and log in
   to your E*TRADE account.
2. Go to the API key page: **us.etrade.com/etx/ris/apikey**
   (or from the developer site: developer.etrade.com → getting
   started → request a key).
3. Ask for a **sandbox** key (test mode). It is free. E*TRADE says
   to allow a few business days for it to be issued.
4. When it arrives, you will have a **consumer key** and a
   **consumer secret**. Write them down somewhere safe — the secret
   is shown once.
5. In VaultTec, these become (Secrets on Streamlit, or `.env` on
   the PC — same pattern as the Alpaca keys):
   - `ETRADE_CONSUMER_KEY = "…"`.
   - `ETRADE_CONSUMER_SECRET = "…"`.
   - Leave `ETRADE_SANDBOX = "true"` — sandbox is the default.
   - `ETRADE_ACCOUNT_ID_KEY` comes from Step B.

### Step B — find which account to use

1. Once the sandbox key works, VaultTec can list your accounts
   (`list_accounts()`). It shows the description (e.g. INDIVIDUAL)
   and the value — **not** the account number.
2. Pick the account you want VaultTec to use (your main brokerage
   one, not a retirement or managed account) and copy its
   **accountIdKey** into `ETRADE_ACCOUNT_ID_KEY`.
3. If you have more than one E*TRADE account, tell Shadow which
   one you picked — the broker never guesses.

### Step C — approve the app (the browser step)

1. In VaultTec's private panel, tap the E*TRADE authorize button
   (once the panel is wired — see §8). It gives you a link.
2. Open the link in your browser. Log in to E*TRADE and tap
   **Approve**. E*TRADE shows a short **verifier code**.
3. Type that code into VaultTec. VaultTec saves the access token
   on your device only.
4. **Repeat this every morning** you want E*TRADE connected — the
   token dies at midnight Eastern.

### Step D — live key (only after sandbox works)

1. On developer.etrade.com, complete the **API Developer Agreement**
   and the **User Intent Survey** at the bottom of the getting-started
   page.
2. For an Individual key (your own personal use — the right one),
   E*TRADE issues the live key in the page once requirements are
   met. A Vendor key is for apps used by many people — not us.
3. You also need the **Market Data Agreement** for live quotes,
   and an annual **Market Data Attestation**.
4. Live keys go in as a *separate* pair — never reuse the sandbox
   pair. The live locks stay shut (`ETRADE_SANDBOX` stays `"true"`)
   until the sandbox test passes **and** the legal review is done
   **and** you say go, in words.

## 7. What is still missing

- **Your keys.** Nothing can be tested against the real sandbox
  until you have the sandbox consumer key and secret (Step A)
  and the account key (Step B).
- **A real sandbox test.** The code is proven against canned
  responses only. The first real sandbox run must check: the
  OAuth flow works, the quote comes back, a preview accepts a
  whole-share order, and — the open question — whether a preview
  accepts a **fractional** quantity. The sandbox answers with
  stored sample data, so it still does not prove a real order
  fills.
- **Runner wiring (not done yet, on purpose).** The runner still
  picks the Alpaca broker. Wiring E*TRADE in is one choice in
  `runner.make_broker` plus one fix: the runner's position record
  currently stores a *fractional* quantity from the proposal,
  and E*TRADE needs the *whole-share* quantity the broker
  actually bought (`order["qty"]`) stored instead.
- **The take-profit watcher (not built yet).** Because E*TRADE
  has no bracket order, VaultTec must watch the price and sell
  when the target hits, cancelling the stop first. The runner
  has a 10-day time exit; a target exit for E*TRADE is still to
  build. Until it exists, an E*TRADE position's upside is only
  protected by the time exit and by you watching it.
- **Broker-side stop reconciliation.** If the stop-loss fires at
  E*TRADE while VaultTec is off, VaultTec's saved state still
  thinks the position is open. The runner needs to compare its
  state with the broker's real positions before proposing.
- **The panel.** The private phone panel still only drives
  Alpaca. An E*TRADE section (authorize button, token status,
  "re-authorize" reminder) is still to build.
- **The fractional question.** See §4. Only a sandbox preview
  with a decimal quantity settles it.

## 8. Honest limits

- **E*TRADE is a backup, not a replacement, for small money.**
  Whole shares only means a small account can barely trade on it.
  Alpaca stays the main broker for the $100 plan.
- **Daily re-approval is a real chore.** If you forget, VaultTec
  simply cannot reach E*TRADE that day. Nothing breaks — it just
  does not trade.
- **The sandbox proves shapes, not fills.** A green sandbox test
  does not mean a live order will fill at the price you expect.
- **No crypto, no bracket, no market clock.** All three are
  E*TRADE API limits, not VaultTec choices.
- **E*TRADE's sample data is old.** Sandbox accounts are canned
  2013 data; balances and positions there are not yours.
- **The first live order, whenever it happens, must be tiny,**
  previewed, approved by you, and watched — exactly like the
  Alpaca live plan. No automation on E*TRADE until its paper
  record earns it.
- **No legal review has happened for E*TRADE either.** The same
  clinic/attorney review that gates the public product gates any
  live trading on any broker.

## 9. Sources (E*TRADE's own pages)

- Developer program, getting started, key requests, agreements:
  https://developer.etrade.com/getting-started
- Developer guides (OAuth lifecycle, authorize flow):
  https://developer.etrade.com/getting-started/developer-guides
- FAQ (key wait time — "a few business days"): on the
  getting-started page above
- API reference (sandbox docs — accounts, balance, portfolio,
  quotes, orders, preview/place/cancel):
  https://apisb.etrade.com/docs/api/account/api-balance-v1.html
  (and the matching pages under apisb.etrade.com/docs)
- Authorization page (browser approval):
  https://us.etrade.com/e/t/etws/authorize
- Sandbox key request (log in first):
  https://us.etrade.com/etx/ris/apikey
- Fractional-share rules (website): E*TRADE's own help pages
  on us.etrade.com
  ("if the quantity is less than 1 share, price type must be
  MARKET"; eligible listed securities only; $5.00 minimum
  notional for buys; Day orders in regular hours only)
- Order-linking limits (what the API cannot do — no OCO/bracket
  via API) were cross-checked across the official docs and three
  independent API comparisons, all agreeing: the website offers
  bracketed/OCO, the REST API does not.
