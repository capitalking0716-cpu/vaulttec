"""VaultTec — Streamlit dashboard (Phase 1, paper trading only).

Run:  streamlit run app.py
Design: obsidian black / charcoal / metallic gold / vault amber.
Underground financial intelligence bunker — clean, no cheesy hacker neon.

Only this file imports Streamlit. All logic lives in the vaulttec package.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

import streamlit as st

from vaulttec.ai_assistant import Assistant
from vaulttec.analytics import (
    accuracy_summary, analyse_history, backtest_macd_crossover,
    backtest_sma_crossover, generate_signal, get_signal_history,
    record_signal, run_backtest_suite, scan_watchlist, top_opportunities,
)
from vaulttec.analytics.signal_history import init_signal_history
from vaulttec.automation import AutomationEngine
from vaulttec.challenge import (
    CHALLENGE_REQUIRED_TRADES,
    CHALLENGE_STARTING_CAPITAL_LABEL,
    CHALLENGE_SUBSCRIPTIONS,
    NO_REASONS,
    ChallengeTrial,
    build_proposal,
    explain_proposal_plain,
)
from vaulttec.coach import COACHING_CHECKLIST, Coach, walkthrough
from vaulttec.config import RISK_PROFILES, get_settings
from vaulttec.db import init_db
from vaulttec.db.models import UserProfile
from vaulttec.market import analyse_indicators, fetch_history, get_provider
from vaulttec.paper_trading import PaperTradingEngine
from vaulttec.portfolio import Portfolio
from vaulttec.private_live.panel import (
    activate_kill_switch,
    approve_proposal,
    check_live_gate,
    clear_kill_switch,
    get_private_status,
    login_password_set,
    reject_proposal,
    run_private_scan,
)
from vaulttec.risk import RiskEngine

DISCLOSURE = (
    "⚠️ Risk disclosure: Trading involves substantial risk of loss. "
    "VaultTec does not promise guaranteed profits and does not advertise "
    "unverified accuracy. Past performance does not guarantee future results. "
    "This is PAPER TRADING with virtual money only — no live brokerage, "
    "no real money, no leverage, no options."
)

st.set_page_config(page_title="VaultTec — Financial Intelligence", page_icon="🏦", layout="wide")

# --- Vault styling: obsidian / charcoal / gold / amber -------------------
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0b0d; color: #e8e4d8; }
    h1, h2, h3 { color: #d4af37 !important; font-family: Georgia, serif; letter-spacing: 0.04em; }
    .stMetric { background: #17171b; border: 1px solid #3a3222; border-radius: 8px; padding: 12px; }
    .stMetric label, .stMetric div { color: #e8e4d8 !important; }
    .stButton>button { background: #d4af37; color: #0b0b0d; font-weight: bold; border: none; min-height: 48px; font-size: 16px; }
    .stButton>button:hover { background: #e8c766; color: #0b0b0d; }
    @media (max-width: 600px) { .stMetric { padding: 8px; } .stMetric label { font-size: 13px; } }
    /* Tabs: short labels, scrollable on a phone so no section is a long scroll. */
    [data-testid="stTabs"] button { font-size: 14px; padding: 8px 10px; white-space: nowrap; }
    section[data-testid="stSidebar"] { background-color: #121214; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Login gate (optional, hosting only) ------------------------------------
# The gate is OFF unless a password is set in Streamlit secrets
# (.streamlit/secrets.toml, key VAULTTEC_LOGIN_PASSWORD) or the
# VAULTTEC_LOGIN_PASSWORD environment variable. Locally, with no secret
# set, the app opens straight in — nothing changes for local use.
# On Streamlit Community Cloud, Neko sets his own password in the app's
# Secrets settings; the password is never stored in this repo.
# Login email is capitalking0716@gmail.com.
LOGIN_EMAIL = "capitalking0716@gmail.com"


def _login_password() -> str | None:
    try:
        secret = st.secrets.get("VAULTTEC_LOGIN_PASSWORD")  # type: ignore[attr-defined]
        if secret:
            return str(secret)
    except Exception:
        pass
    env = os.getenv("VAULTTEC_LOGIN_PASSWORD")
    return env or None


_login_password = _login_password()
if _login_password and not st.session_state.get("vaulttec_logged_in"):
    st.title("🏦 VAULTTEC")
    st.caption("Sign in to use your VaultTec trading app.")
    _email = st.text_input("Email", value=LOGIN_EMAIL)
    _pw = st.text_input("Password", type="password")
    if st.button("Sign in"):
        _ok = (
            _email.strip().lower() == LOGIN_EMAIL
            and hmac.compare_digest(
                hashlib.sha256(_pw.encode()).hexdigest(),
                hashlib.sha256(_login_password.encode()).hexdigest(),
            )
        )
        if _ok:
            st.session_state["vaulttec_logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid email or password.")
    st.caption(
        "Paper trading only — virtual money, no live brokerage, no real money. "
        "First time on the hosted app? Set your password in the app's Secrets "
        "settings on Streamlit Cloud (see DEPLOY.md) — never share it here."
    )
    st.stop()

settings = get_settings()
init_db(settings.db_path)
init_signal_history(settings.db_path)
provider = get_provider(settings.data_provider)

# --- Session state ---------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state.profile = UserProfile()
if "portfolio" not in st.session_state:
    st.session_state.portfolio = Portfolio(cash=settings.paper_starting_cash)
if "coach" not in st.session_state:
    st.session_state.coach = Coach()
if "risk" not in st.session_state:
    st.session_state.risk = RiskEngine()
if "engine" not in st.session_state:
    st.session_state.engine = PaperTradingEngine(st.session_state.portfolio, st.session_state.risk)
if "challenge" not in st.session_state:
    st.session_state.challenge = ChallengeTrial()
if "assistant" not in st.session_state:
    st.session_state.assistant = Assistant()
if "automation" not in st.session_state:
    # One automation engine for the whole session. Phase 3 fix: the
    # emergency-stop button used to build a throwaway engine, so the
    # stop was logged nowhere and never actually paused anything.
    st.session_state.automation = AutomationEngine(st.session_state.profile)

profile: UserProfile = st.session_state.profile
automation: AutomationEngine = st.session_state.automation
portfolio: Portfolio = st.session_state.portfolio
coach: Coach = st.session_state.coach
engine: PaperTradingEngine = st.session_state.engine
challenge: ChallengeTrial = st.session_state.challenge

# --- Sidebar: profile settings --------------------------------------------
st.sidebar.title("🏦 VAULTTEC")
st.sidebar.caption("Financial Intelligence Bunker")
st.sidebar.markdown("---")
st.sidebar.subheader("Your Profile")
profile.name = st.sidebar.text_input("Name", profile.name)
profile.goal = st.sidebar.text_input("Goal", profile.goal)
risk_key = st.sidebar.selectbox(
    "Risk tolerance", list(RISK_PROFILES), index=list(RISK_PROFILES).index(profile.risk_tolerance)
)
profile.risk_tolerance = risk_key
limits = RISK_PROFILES[risk_key]
profile.max_position_pct = limits["max_position_pct"]
profile.daily_loss_limit_pct = limits["daily_loss_limit_pct"]
st.session_state.risk = RiskEngine(
    max_position_pct=limits["max_position_pct"],
    max_concentration_pct=limits["max_concentration_pct"],
    max_exposure_pct=limits["max_exposure_pct"],
    daily_loss_limit_pct=limits["daily_loss_limit_pct"],
    min_risk_reward=limits["min_risk_reward"],
)
engine.risk = st.session_state.risk
profile.allowed_markets = st.sidebar.multiselect(
    "Allowed markets", ["stocks", "crypto"], default=profile.allowed_markets
)
st.sidebar.markdown("---")
st.sidebar.subheader("Automation")
st.sidebar.write(f"Coaching stage: **{profile.coaching_stage}**")
st.sidebar.write(f"Automation: **{'ON (paper only)' if automation.enabled else 'OFF'}**")
if st.sidebar.button("🛑 EMERGENCY STOP — pause automation", use_container_width=True):
    automation.kill_switch()
    st.sidebar.error("Automation stopped.")
if automation.paused:
    if st.sidebar.button("Resume automation (needs re-enable)", use_container_width=True):
        automation.resume()
        st.sidebar.info("Paused flag cleared. Enable automation again below to restart it.")
st.sidebar.caption("Automation is paper-only, needs coaching graduation, and never bypasses risk limits.")
st.sidebar.markdown("---")
st.sidebar.info(DISCLOSURE)

# --- Header ----------------------------------------------------------------
st.title("🏦 VAULTTEC")
st.caption("AI Trading & Investment Intelligence — paper trading only. The heart of the family trust.")
st.warning(DISCLOSURE)


# --- Tabs: one short scroll per section, not one long page -------------
# Order matches the original layout, so every variable a later
# section needs is still defined before it is used.
tab_dashboard, tab_scanner, tab_trade, tab_challenge, tab_results, tab_live_paper, tab_private = st.tabs(["Dashboard", "Scanner", "Trade", "Challenge", "Results", "Live Paper", "Private"])

with tab_dashboard:
    # --- Portfolio metrics -----------------------------------------------------
    quotes = {s: provider.get_quote(s) for s in settings.watchlist}
    prices = {s: q.price for s, q in quotes.items()}
    value = portfolio.value(prices)
    pnl = value - settings.paper_starting_cash

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio value (paper)", f"${value:,.2f}")
    c2.metric("Total P&L (paper)", f"${pnl:,.2f}")
    c3.metric("Cash available (paper)", f"${portfolio.cash:,.2f}")
    c4.metric("Risk exposure", f"${portfolio.exposure(prices):,.2f}")

    # --- Watchlist + signals ---------------------------------------------------
    st.header("Market Intelligence")
    cols = st.columns(len(settings.watchlist))
    signals = []
    for col, symbol in zip(cols, settings.watchlist):
        q = quotes[symbol]
        history = provider.get_history(symbol)
        sig = generate_signal(symbol, history)
        signals.append(sig)
        arrow = "▲" if q.change_pct >= 0 else "▼"
        col.metric(symbol, f"${q.price:,.2f}", f"{arrow} {q.change_pct:+.2f}%")
        col.caption(f"Signal: {sig.direction} ({sig.confidence:.0%})")

    st.subheader("Active signals — with the evidence, not a promise")
    if "signals_recorded" not in st.session_state:
        st.session_state.signals_recorded = set()
    for sig in signals:
        st.write(f"**{sig.symbol}** — {sig.direction} ({sig.confidence:.0%}): {sig.evidence}")
        # Record each symbol's signal once per session, not on every page reload.
        if sig.symbol not in st.session_state.signals_recorded:
            record_signal(settings.db_path, sig, prices[sig.symbol])
            st.session_state.signals_recorded.add(sig.symbol)


with tab_scanner:
    # --- Market scanner (Phase 2) ----------------------------------------------
    st.header("🔎 Market Scanner — opportunities, strongest first")
    st.caption("Stocks + crypto, ranked by signal strength. A high rank means several "
               "independent checks agreed — it is still an observation, not a promise.")
    scan_results = scan_watchlist(provider_name=settings.data_provider)
    if scan_results and scan_results[0].get("source") == "sample":
        st.caption("Data source: sample (offline demo data). Switch the data provider to "
                   "yfinance in settings for delayed real prices.")
    for r in scan_results:
        st.write(f"**{r['symbol']}** — {r['direction']} ({r['confidence']:.0%} confidence, "
                 f"{r['checks_agreeing']}/{r['checks_total']} checks agreed): {r['evidence']}")
    top = top_opportunities(provider_name=settings.data_provider)
    st.subheader("Top opportunities today")
    if top:
        for r in top:
            st.write(f"⭐ **{r['symbol']}** — {r['direction']} ({r['confidence']:.0%}): {r['evidence']}")
    else:
        st.write("Nothing cleared the confidence bar today — that is normal, and better than forcing a trade.")

    # --- Technical analysis detail (Phase 2) ------------------------------------
    st.header("📊 Technical Analysis — what each indicator is saying")
    ta_symbol = st.selectbox("Analyse a symbol", settings.watchlist, key="ta_symbol")
    ta_history, ta_source = fetch_history(ta_symbol, days=120, provider_name=settings.data_provider)
    if ta_source == "sample":
        st.caption("Showing sample data for this symbol (offline demo data).")
    ind = analyse_indicators(ta_history)
    st.write(f"**{ta_symbol}** — ${ind['price']:,.2f} — trend: **{ind['trend']}**")
    st.write(f"- RSI: {ind['rsi_text']}")
    st.write(f"- MACD: {ind['macd_text']}")
    st.write(f"- Bollinger: {ind['bollinger_text']}")
    st.write(f"- EMA: {ind['ema_text']}")
    st.write(f"- Volume: {ind['volume']['label']} ({ind['volume']['ratio']:.1f}× its 20-day average).")
    if ind["atr"] == ind["atr"]:
        st.write(f"- Typical daily move (ATR): about ${ind['atr']:.2f} — a stop-loss tighter than "
                 "that can be hit by ordinary daily noise.")
    st.line_chart(ta_history.set_index("date")["close"])

    # --- Historical analysis (Phase 2) ------------------------------------------
    st.header("🕰️ Historical Analysis — what this market actually did")
    hist = analyse_history(ta_history)
    st.write(hist["summary"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total return", f"{hist['total_return_pct']:+.1f}%")
    c2.metric("Daily volatility", f"{hist['volatility_pct']:.1f}%")
    c3.metric("Worst drawdown", f"{hist['max_drawdown_pct']:.1f}%")
    c4.metric("Best / worst day", f"{hist['best_day_pct']:+.1f}% / {hist['worst_day_pct']:+.1f}%")


with tab_trade:
    # --- Coaching --------------------------------------------------------------
    st.header("🎓 Your Coach — learn first, automate later")
    st.progress(coach.progress_pct / 100)
    st.write(f"Coaching progress: {coach.progress_pct}% — next step: **{coach.next_step}**")
    for item in COACHING_CHECKLIST:
        done = item["id"] in coach.completed
        if st.checkbox(item["label"], value=done, key=f"coach_{item['id']}"):
            coach.complete(item["id"])
    st.write(f"Coached paper trades done: {coach.coached_trades_done} / 5")
    if coach.can_graduate() and not coach.graduated:
        if st.button("Take the graduation review — I understand the risks"):
            if coach.graduate(user_confirmed=True):
                profile.coaching_stage = "graduated"
                st.success("Graduated! You can now enable supervised automation (paper only).")
    elif coach.graduated:
        st.success("✅ Graduated from coaching. Supervised automation is available (paper only).")
        if automation.enabled:
            st.write("🤖 Supervised automation is **ON** — paper trades only, inside your profile limits.")
        elif st.button("Enable supervised automation (paper only)"):
            if automation.enable(graduated=True):
                st.success("Automation enabled — paper only, risk-checked, kill-switch ready.")
            else:
                st.error("Automation could not be enabled.")

    # --- Coached paper trade ---------------------------------------------------
    st.header("📈 Place a coached paper trade")
    symbol = st.selectbox("Symbol", settings.watchlist)
    q = quotes[symbol]
    history = provider.get_history(symbol)
    sig = generate_signal(symbol, history)
    check = st.session_state.risk.check_order(
        symbol=symbol, price=q.price, quantity=1, stop_loss=q.price * 0.97,
        take_profit=q.price * 1.045, portfolio_value=value,
        current_exposure=portfolio.exposure(prices),
    )
    qty = st.number_input("Quantity (shares)", min_value=1, max_value=max(1, int(check.max_quantity)),
                          value=1, step=1)
    sl = st.number_input("Stop-loss ($)", value=check.suggested_stop_loss, step=0.5)
    tp = st.number_input("Take-profit ($)", value=check.suggested_take_profit, step=0.5)
    if st.button("Show me the walkthrough"):
        st.info(walkthrough(symbol, sig.direction, q.price, sl, tp, qty, sig.evidence))
    if st.button("Approve & place this paper trade"):
        trade = engine.place_order(symbol, "buy", qty, q.price, sl, tp,
                                   reason=sig.evidence, source="coached")
        if trade:
            coach.record_coached_trade()
            st.success(f"Paper trade placed: {qty} × {symbol} @ ${q.price:,.2f} (virtual money).")
        else:
            st.error("Trade BLOCKED by the Risk Engine:")
            for r in engine.blocked[-1]["reasons"]:
                st.write(f"- {r}")


with tab_challenge:
    # --- Challenge Trial -------------------------------------------------------
    # Paper only. Trading platform, not a school — no Academy, no course.
    # $20 is the user's own starting capital — VaultTec takes nothing from
    # it. Pass = 30 paper trades in 1 month (win or lose). AI proposes,
    # the user decides YES or NO. Live trading is NOT built: it needs a
    # compliance/legal check first, and no payment is taken.
    st.header("🏆 Challenge Trial — $20 is yours, trade by deciding")
    st.write(f"**{CHALLENGE_STARTING_CAPITAL_LABEL}**")
    st.write(
        "The Challenge replaces the free tier. You put in $20 — your starting "
        "capital for live trading later. VaultTec takes nothing from it. "
        "After the challenge you join the membership separately and pay for "
        "it yourself — the subscription is NOT taken from your profits. "
        "Whatever you earn is yours. Challenge trades below are PAPER trades "
        "on the $10,000 virtual portfolio — the $20 is not spent here."
    )
    st.write(
        "Pass the Challenge by finishing **30 paper trades in 1 month — win "
        "or lose**. No course, no Academy — VaultTec is a trading platform, "
        "not a school. Losing trades still count: finishing is the pass, not "
        "being profitable. The AI proposes each trade and shows its evidence; "
        "**you decide YES or NO**. The AI can't win every time — the better "
        "you understand the data, the better your chances."
    )
    acc = challenge.yes_no_accuracy()
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("Challenge trades", f"{challenge.trades_done} / {CHALLENGE_REQUIRED_TRADES}")
    cc2.metric("Your YES/NO accuracy",
               f"{acc['accuracy_pct']:.1f}%" if acc["accuracy_pct"] is not None else "—")
    cc3.metric("Your starting capital", "$20.00")
    st.progress(challenge.progress_pct / 100)
    st.write(f"Challenge progress: {challenge.progress_pct}% — " +
             ("; ".join(challenge.whats_left) if challenge.whats_left else "nothing left — Challenge complete!"))

    st.subheader("Today's proposal — your call: YES or NO?")
    proposal = build_proposal(symbol, sig.direction, sig.confidence, sig.evidence, q.price, qty)
    st.write(explain_proposal_plain(proposal))
    if sig.direction != "long":
        st.info(f"No long proposal for {symbol} right now — the signal is "
                f"{sig.direction}. Try another symbol above, or come back "
                f"when the checks agree on a long trade. Forcing a trade is "
                f"worse than waiting.")
    else:
        check_ch = st.session_state.risk.check_order(
            symbol=symbol, price=q.price, quantity=qty,
            stop_loss=proposal["stop_loss"], take_profit=proposal["take_profit"],
            portfolio_value=value, current_exposure=portfolio.exposure(prices),
        )
        if not check_ch.allowed:
            st.error("This proposal is BLOCKED by the Risk Engine — it cannot be placed:")
            for r in check_ch.reasons:
                st.write(f"- {r}")
        no_reason = st.selectbox("If you say NO, why? (logged in your journal)",
                                 NO_REASONS, key="challenge_no_reason")
        yes_col, no_col = st.columns(2)
        if yes_col.button("✅ YES — place this paper trade", use_container_width=True):
            decision_index = len(challenge.decisions)
            challenge.record_decision(symbol, sig.direction, sig.confidence, sig.evidence,
                                      q.price, proposal["stop_loss"], proposal["take_profit"],
                                      qty, "yes", "Agreed with the AI's reasoning")
            trade = engine.place_order(symbol, "buy", qty, q.price,
                                       proposal["stop_loss"], proposal["take_profit"],
                                       reason=sig.evidence, source="challenge")
            if trade:
                challenge.record_trade(symbol, outcome="open", price=q.price,
                                       stop_loss=proposal["stop_loss"],
                                       take_profit=proposal["take_profit"], quantity=qty,
                                       decision_index=decision_index)
                st.success(f"YES logged and paper trade placed: {qty} × {symbol} @ "
                           f"${q.price:,.2f} (virtual money). That's "
                           f"{challenge.trades_done} of {CHALLENGE_REQUIRED_TRADES} "
                           f"Challenge trades.")
            else:
                st.error("Trade BLOCKED by the Risk Engine — your YES was logged, "
                         "but no trade was placed:")
                for r in engine.blocked[-1]["reasons"]:
                    st.write(f"- {r}")
        if no_col.button("❌ NO — skip this trade", use_container_width=True):
            challenge.record_decision(symbol, sig.direction, sig.confidence, sig.evidence,
                                      q.price, proposal["stop_loss"], proposal["take_profit"],
                                      qty, "no", no_reason)
            st.info("NO logged — no trade placed. A NO is a good decision too, "
                    "and it is in your journal just like a YES.")

    st.subheader("Your 30-trade checklist — losses count, finishing is the pass")
    if challenge.trades:
        st.table([{"#": i + 1, "Symbol": t.symbol, "Date": t.date,
                   "Your call": t.decision.upper(), "Outcome": t.outcome,
                   "P&L (paper)": f"${t.pnl:+,.2f}"}
                  for i, t in enumerate(challenge.trades)])
    else:
        st.write("No Challenge trades yet. Your first YES starts the count — "
                 "losses count too, so a losing trade still moves you forward.")

    st.subheader("Your YES/NO journal — are your calls any good?")
    if challenge.decisions:
        st.table([{"Symbol": d.symbol, "Call": d.decision.upper(),
                   "Confidence": f"{d.confidence:.0%}",
                   "Reason": d.reason, "Outcome": d.outcome,
                   "P&L (paper)": f"${d.pnl:+,.2f}"}
                  for d in reversed(challenge.decisions[-10:])])
        if acc["accuracy_pct"] is None:
            st.write("No Challenge trade has resolved yet, so there is no "
                     "accuracy number to show — it appears once a trade closes.")
        else:
            st.write(f"Your YES calls so far: **{acc['wins']} wins, {acc['losses']} losses "
                     f"({acc['accuracy_pct']:.1f}% accuracy)** over {acc['resolved_trades']} "
                     f"resolved trades. Your NOs: {acc['no_decisions']} skipped. "
                     f"Compare your accuracy with the AI's signal accuracy below — "
                     f"if your NOs were right, your judgement is adding something.")
    else:
        st.write("No decisions logged yet. Every YES and NO you make on a "
                 "proposal is recorded here, with the outcome when the trade resolves.")

    if challenge.is_complete:
        st.success("🏆 " + challenge.graduation_message())
        tier_text = ", ".join(
            f"{v['label']} ${v['monthly_usd']}" for v in CHALLENGE_SUBSCRIPTIONS.values()
        )
        st.write("After the challenge, you join the membership separately and "
                 f"pay for it yourself ({tier_text} a month) — it is NOT taken "
                 "from your profits. The rest of the profits are yours. No "
                 "payment has been taken yet, and none will be until live "
                 "trading is available.")
    else:
        st.write("**Still to go:** " + "; ".join(challenge.whats_left) + ".")


with tab_results:
    # --- Trading history -------------------------------------------------------
    st.header("📓 Trading history (paper)")
    if engine.trades:
        st.table([{"Symbol": t.symbol, "Side": t.side, "Qty": t.quantity, "Price": t.price,
                   "Stop": t.stop_loss, "Target": t.take_profit, "Source": t.source}
                  for t in engine.trades])
    else:
        st.write("No paper trades yet. Your first coached trade starts the journal — "
                 "aim for 30–50 paper trades before any live trading is even considered.")

    # --- AI Assistant (Phase 2) ------------------------------------------------
    st.header("🤖 Vault — your AI assistant")
    st.write(st.session_state.assistant.briefing(value, pnl, signals))
    if st.button("☀️ Give me today's briefing"):
        acc = accuracy_summary(settings.db_path)
        st.write(st.session_state.assistant.daily_briefing(scan_results, value, pnl, acc))
    strategy = st.selectbox(
        "Explain a strategy or concept",
        ["", "SMA crossover", "MACD crossover", "stop-loss", "position sizing",
         "diversification", "risk/reward", "Bollinger Bands", "RSI"],
        key="strategy_picker",
    )
    if strategy:
        st.write(st.session_state.assistant.explain_strategy(strategy))
    if st.button("Explain the market on my chosen symbol"):
        st.write(st.session_state.assistant.explain_market(ta_symbol, ind))
    question = st.text_input("Ask Vault a question", placeholder="e.g. What is a stop-loss?")
    if question:
        st.write(st.session_state.assistant.answer(
            question,
            context={"portfolio_value": value, "cash": portfolio.cash,
                     "holdings": [{"symbol": t.symbol, "quantity": t.quantity}
                                  for t in engine.trades],
                     "exposure": portfolio.exposure(prices),
                     "signals": signals, "scan_results": scan_results,
                     "daily_pnl": pnl}))

    # --- Signal history + accuracy (Phase 2) -------------------------------------
    st.header("📜 Signal History — are the signals worth anything?")
    acc = accuracy_summary(settings.db_path)
    if acc["accuracy_pct"] is None:
        st.write(acc["note"])
    else:
        st.write(f"Signal accuracy: **{acc['accuracy_pct']:.1f}%** over {acc['total']} resolved "
                 f"signals ({acc['wins']} wins, {acc['losses']} losses). {acc['note']}")
    recent = get_signal_history(settings.db_path, limit=10)
    if recent:
        st.table([{"Symbol": r["symbol"], "Direction": r["direction"],
                   "Confidence": f"{r['confidence']:.0%}",
                   "Outcome": r["outcome"] or "pending",
                   "When": r["created_at"][:10]} for r in recent])
    else:
        st.write("No signals recorded yet — the scanner above records each one as it runs.")

    # --- Backtest suite (historical only, Phase 3) ---------------------------
    st.header("🧪 Backtest suite — historical only")
    st.caption("Four strategies on the same SPY history, compared side by side. "
               "A good past result is not a promise about the future.")
    suite = run_backtest_suite(provider.get_history("SPY", days=180))
    st.table([{"Strategy": s["strategy"], "Return": f"{s['total_return_pct']:+.2f}%",
               "Trades": s["trades"], "Win rate": f"{s['win_rate_pct']:.1f}%",
               "Worst drawdown": f"{s['max_drawdown_pct']:.1f}%"}
              for s in suite["strategies"]])
    if suite["best_by_return"]:
        st.write(f"Best by past return: **{suite['best_by_return']}** — historical only, not a recommendation.")
    st.write(suite["note"])
    bt = backtest_sma_crossover(provider.get_history("SPY", days=120))
    st.write(f"SPY SMA crossover backtest: {bt['total_return_pct']:+.2f}% over {bt['trades']} trades, "
             f"win rate {bt['win_rate_pct']:.1f}%. {bt['note']}")
    bt2 = backtest_macd_crossover(provider.get_history("SPY", days=120))
    st.write(f"SPY MACD crossover backtest: {bt2['total_return_pct']:+.2f}% over {bt2['trades']} trades, "
             f"win rate {bt2['win_rate_pct']:.1f}%. {bt2['note']}")

    # --- Phase 3 validation report -------------------------------------------
    st.header("✅ Phase 3 Validation — 30–50 paper trades, run for real")
    validation_path = Path(__file__).resolve().parent / "validation" / "phase3-paper-validation-report.json"
    if validation_path.exists():
        report = json.loads(validation_path.read_text())
        st.write(f"**{report['trades_placed']} paper trades** placed (target {report['target_trades']}) — "
                 f"{report['wins']} wins, {report['losses']} losses, "
                 f"win rate **{report['win_rate_pct']}%**, total paper P&L "
                 f"**${report['total_pnl_usd']:,.2f} ({report['total_pnl_pct']:+.2f}%)**. "
                 f"Exits: {report['exits']}. Blocked by the Risk Engine: {report['blocked_by_risk']}.")
        st.caption(report["note"])
        st.caption("Full trade-by-trade report: validation/phase3-paper-validation-report.md")
    else:
        st.write("Validation report not generated yet. Run it with: "
                 "`python -m vaulttec.analytics.validation`")

    # --- Phase 4 Step 1: real-market validation ------------------------------
    st.header("📊 Phase 4 Step 1 — Same test, real market history")
    real_path = Path(__file__).resolve().parent / "validation" / "phase4-real-market-validation-report.json"
    if real_path.exists():
        real = json.loads(real_path.read_text())
        st.write(f"**{real['trades_placed']} paper trades** on delayed real history "
                 f"({real['data_source']}) — {real['wins']} wins, {real['losses']} losses, "
                 f"win rate **{real['win_rate_pct']}%**, total paper P&L "
                 f"**${real['total_pnl_usd']:,.2f} ({real['total_pnl_pct']:+.2f}%)**. "
                 f"Exits: {real['exits']}. Blocked by the Risk Engine: {real['blocked_by_risk']}.")
        if "backtests" in real:
            st.write("Backtest suite on the same real history (mean across symbols):")
            for name, agg in real["backtests"]["aggregate"].items():
                st.write(f"- {name}: {agg['mean_total_return_pct']:+.2f}% mean return, "
                         f"{agg['mean_win_rate_pct']:.1f}% mean win rate, "
                         f"{agg['mean_max_drawdown_pct']:.2f}% mean max drawdown, "
                         f"{agg['total_trades']} trades.")
        st.caption(real["note"])
        st.caption("Full trade-by-trade report: validation/phase4-real-market-validation-report.md")
    else:
        st.write("Real-market validation has not been run yet. Run it with: "
                 "`python -m vaulttec.analytics.validation --provider yfinance "
                 "--stem phase4-real-market-validation-report --backtests`")

    # --- Phase 4b: mean-reversion follow-up (out-of-sample) -------------------
    st.header("📊 Phase 4b — Mean-reversion follow-up (out-of-sample)")
    follow_path = Path(__file__).resolve().parent / "validation" / "phase4b-mean-reversion-followup-report.json"
    if follow_path.exists():
        follow = json.loads(follow_path.read_text())
        st.write("The Phase 4 backtests suggested Bollinger (+17.71%) and RSI "
                 "(+12.44%) mean reversion. This follow-up tested both on three "
                 "earlier, non-overlapping windows — out-of-sample, so the "
                 "Phase 4 window could not confirm them.")
        for key, label in (("rsi", "RSI mean-reversion"), ("bollinger", "Bollinger mean-reversion")):
            pooled = follow["pooled_out_of_sample"][key]
            a = pooled["variant_a_validation_oos_pooled"]
            b = pooled["variant_b_native_backtest_oos_pooled"]
            st.write(f"**{label}** — out-of-sample, 3 windows pooled:")
            st.write(f"- Risk-managed (3% stop / 4.5% target): {a['trades']} trades, "
                     f"{a['win_rate_pct']}% win rate, paper P&L "
                     f"${a['total_pnl_usd']:,.2f} ({a['total_pnl_pct']:+.2f}% across the 3 windows).")
            st.write(f"- Native backtest (no fixed stop): {b['total_trades']} trades, "
                     f"mean of window means {b['mean_of_window_means_pct']:+.2f}%, "
                     f"positive in {b['windows_positive']} of {b['windows_total']} windows.")
        st.caption("The bounce shows up in the no-stop backtest in all three windows, "
                   "but the risk-managed version — the only one VaultTec may trade — "
                   "is roughly break-even pooled and lost badly in the falling "
                   "OOS-2 window. Past performance does not guarantee future results.")
        st.caption(follow["note"])
        st.caption("Full report: validation/phase4b-mean-reversion-followup-report.md")
    else:
        st.write("Mean-reversion follow-up has not been run yet. Run it with: "
                 "`python -m vaulttec.analytics.mean_reversion`")

    # --- Phase 4c: exit test ---------------------------------------------------
    st.header("📊 Phase 4c — Exit test (can a better exit raise the win rate?)")
    exit_path = Path(__file__).resolve().parent / "validation" / "phase4c-exit-test-report.json"
    if exit_path.exists():
        exit_test = json.loads(exit_path.read_text())
        st.write("Same three out-of-sample windows as Phase 4b, seven exit "
                 "variants per strategy — every variant keeps a stop-loss. "
                 "Verdict rules were fixed before the run: a variant survives "
                 "OOS-2 (the falling window) when its OOS-2 P&L is >= $0, and "
                 "is worth keeping when its pooled P&L is > $0 AND it survives OOS-2.")
        for key, label in (("rsi", "RSI mean-reversion"), ("bollinger", "Bollinger mean-reversion")):
            pooled = exit_test["pooled_out_of_sample"][key]
            st.write(f"**{label}** — out-of-sample, 3 windows pooled:")
            for variant_id, result in pooled.items():
                st.write(f"- {variant_id}: {result['trades']} trades, "
                         f"{result['win_rate_pct']}% win rate, paper P&L "
                         f"${result['total_pnl_usd']:,.2f} (expectancy "
                         f"${result['expectancy_usd']:,.2f}/trade), OOS-2 "
                         f"${result['oos2_pnl_usd']:,.2f} "
                         f"({'survives' if result['survives_oos2'] else 'does NOT survive'}).")
            verdict = exit_test["verdict"][key]
            st.write(f"Worth keeping: {verdict['variants_worth_keeping'] or 'none'}.")
        st.caption("The wider stop is the clear direction (RSI wide-5 +$1,517.23, "
                   "wide-6 +$1,441.19; Bollinger wide-5 +$888.92, wide-6 +$880.48), "
                   "but wide-5 vs wide-6 differ by noise in OOS-2 for RSI, and "
                   "seven variants on the same three windows means the best-looking "
                   "one is partly best by chance. The downtrend filter throws away "
                   "winners too. Keep the wider stop, test it on a FRESH window next; "
                   "do NOT move to real money. Past performance does not guarantee "
                   "future results.")
        st.caption(exit_test["note"])
        st.caption("Full report: validation/phase4c-exit-test-report.md")
    else:
        st.write("Exit test has not been run yet. Run it with: "
                 "`python -m vaulttec.analytics.exit_test`")

    # --- Phase 4d: fresh-window test -------------------------------------------
    st.header("📊 Phase 4d — Fresh-window test (was the wider stop real, or selection luck?)")
    fresh_path = Path(__file__).resolve().parent / "validation" / "phase4d-fresh-window-report.json"
    if fresh_path.exists():
        fresh = json.loads(fresh_path.read_text())
        st.write("Only the Phase 4c winners (wide-5, wide-6) plus the baseline, "
                 "on three fresh 180-day windows never used for selection "
                 "(FRESH-1/2/3, all ending before OOS-3 starts). Verdict rule, "
                 "fixed before the run: a variant holds up when its pooled fresh "
                 "P&L is > $0 AND its pooled win rate is > 40% (the 1.5:1 "
                 "break-even) AND it is positive in at least 2 of 3 fresh windows. "
                 "Fresh results are pooled only across the fresh windows — never "
                 "with the selection windows.")
        for key, label in (("rsi", "RSI mean-reversion"), ("bollinger", "Bollinger mean-reversion")):
            st.write(f"**{label}** — fresh windows pooled:")
            for variant_id, result in fresh["pooled_fresh"][key].items():
                st.write(f"- {variant_id}: {result['trades']} trades, "
                         f"{result['win_rate_pct']}% win rate, paper P&L "
                         f"${result['total_pnl_usd']:,.2f} (expectancy "
                         f"${result['expectancy_usd']:,.2f}/trade), positive in "
                         f"{result['positive_windows']}/{result['windows_total']} windows "
                         f"({'holds up' if result['holds_up'] else 'does NOT hold up'}).")
            st.write(f"Holding up on fresh data: {fresh['verdict'][key]['variants_holding_up'] or 'none'}.")
        st.caption("The wider stop held up on fresh data: RSI wide-6 +$1,226.24 "
                   "(61.6% win, 3/3 windows), wide-5 +$936.61 (58.9% win, 3/3); "
                   "Bollinger wide-6 +$1,043.47 (63.9% win, 3/3), wide-5 +$678.66 "
                   "(58.3% win, 3/3). RSI baseline also held up (+$425.03) while "
                   "Bollinger baseline did not (-$66.99). This is still past prices "
                   "only — three more windows do not prove the next one. Live paper "
                   "trades over real days plus a compliance/legal review are still "
                   "required before real money is ever considered. Past performance "
                   "does not guarantee future results.")
        st.caption(fresh["note"])
        st.caption("Full report: validation/phase4d-fresh-window-report.md")
    else:
        st.write("Fresh-window test has not been run yet. Run it with: "
                 "`python -m vaulttec.analytics.fresh_window`")


with tab_live_paper:
    # --- Live paper trading (real days, paper only) ---------------------------
    st.header("📊 Live paper trading — real days, paper only (wide-6)")
    live_state_path = Path(__file__).resolve().parent / "live_paper" / "state.json"
    if live_state_path.exists():
        try:
            from vaulttec.live_paper_trading import compute_summary as _live_summary
            _live_state = json.loads(live_state_path.read_text())
            _live = _live_summary(_live_state)
            st.write("**PAPER ONLY — virtual money, no live brokerage, no real money.** "
                     "Wide-6 (6% stop / 9% target, 1.5:1, 10-bar exit), RSI + Bollinger "
                     "mean-reversion, one run per day on completed bars only. "
                     "Prices arrive one day at a time and cannot be re-run.")
            st.write(f"Started {_live['started_on']} — last run: {_live['last_run_date'] or 'never'} "
                     f"— runs: {_live['runs']}.")
            st.write(f"Virtual cash: ${_live['cash_usd']:,.2f} — holdings: "
                     f"${_live['holdings_value_usd']:,.2f} — portfolio value: "
                     f"**${_live['portfolio_value_usd']:,.2f}**.")
            st.write(f"Closed trades: {_live['closed_trades']} — wins: {_live['wins']} — "
                     f"losses: {_live['losses']} — win rate: **{_live['win_rate_pct']}%** "
                     f"(break-even at 1.5:1 is 40%) — total realised paper P&L: "
                     f"**${_live['total_pnl_usd']:+,.2f}** ({_live['total_pnl_pct']:+.2f}%) — "
                     f"expectancy: ${_live['expectancy_usd']:+,.2f}/trade.")
            st.write(f"Open positions: {_live['open_positions']} — exits: {_live['exits'] or 'none yet'}.")
            if _live_state.get("open_positions"):
                for _p in _live_state["open_positions"]:
                    st.write(f"- {_p['symbol']} ({_p['strategy']}): entry ${_p['entry_price']:,.2f} "
                             f"on {_p['entry_date']}, stop ${_p['stop_loss']:,.2f}, "
                             f"target ${_p['take_profit']:,.2f}, bars held {_p['bars_held']}.")
            st.caption("A good live paper run does not prove future profits, and a "
                       "compliance/legal review is still required before real money "
                       "is ever considered. Past performance does not guarantee "
                       "future results.")
            st.caption("Full report: live_paper/live-paper-report.md — "
                       "run one day with: `.venv/bin/python -m vaulttec.live_paper_trading`")
        except Exception as exc:  # noqa: BLE001 — a bad live state must never break the dashboard
            st.write(f"Live paper state could not be read ({exc}).")
    else:
        st.write("Live paper trading has not started yet. Run one day with: "
                 "`.venv/bin/python -m vaulttec.live_paper_trading`")


with tab_private:
    # --- My Private Trading — Neko only, operate from your phone ---------
    # Paper first, live locked off, approval-first. This section is
    # behind the login gate: it only shows when a login password is
    # set (VAULTTEC_LOGIN_PASSWORD). No API key is ever shown here.
    # Live trading can never be enabled from this UI — the three-lock
    # gate in private_live/config.py must be opened by hand first.
    st.header("🔒 My Private Trading — Neko only")
    st.warning(
        "PRIVATE — Neko only. Not the public VaultTec product. No "
        "customers, no other people's money. Your own money, paper "
        "first. Trading involves substantial risk of loss. No profit "
        "is promised. Past performance does not guarantee future results."
    )
    if not login_password_set(_login_password):
        st.error(
            "🔐 Set a password first. This private section stays hidden "
            "until a login password is set — in Streamlit Cloud, open the "
            "app's Settings → Secrets and add "
            "VAULTTEC_LOGIN_PASSWORD = \"the password you choose\", then "
            "reboot the app (see DEPLOY.md). Until then, no proposals are "
            "shown and no approvals are possible here. Use the command "
            "line on your PC instead: "
            "`.venv/bin/python -m vaulttec.private_live.runner scan`"
        )
    else:
        _priv = get_private_status()
        st.write(f"**Mode: {_priv['mode']}**")
        if _priv["is_live"]:
            st.error("🔴 LIVE — real money. The live gate is fully open.")
        else:
            st.info("🔒 LIVE IS LOCKED — paper / dry-run only. Live needs all "
                    "three locks opened by hand; it cannot be enabled here.")
            for _lock in _priv["missing_live_locks"]:
                st.write(f"- Missing live lock: {_lock}")
        if _priv["kill_switch_on"]:
            st.error("🛑 KILL-SWITCH IS ON — scan and approve will refuse "
                     "until it is cleared.")
        _pm1, _pm2 = st.columns(2)
        _pm1.metric("Account value", f"${_priv['account_value_usd']:,.2f}")
        _pm2.metric("Open positions", str(_priv["open_positions_count"]))
        _pm3, _pm4 = st.columns(2)
        _pm3.metric("Pending proposals", str(_priv["pending_count"]))
        _pm4.metric("Closed trades", str(_priv["closed_trades"]))
        st.caption("Realised P&L is not tracked in the private runner's "
                   "closed-trade records, so no P&L number is shown here — "
                   "it is not invented. See private_live/report.md for the "
                   "full log.")
        _acct = st.number_input(
            "Account value for sizing ($)", min_value=20.0, max_value=1000000.0,
            value=float(_priv["account_value_usd"] or 50.0), step=10.0,
            key="private_account_value",
        )
        if st.button("🔍 Scan for trades — proposals only, nothing placed",
                     use_container_width=True, key="private_scan"):
            try:
                _scan = run_private_scan(account_value=float(_acct))
            except Exception as exc:  # noqa: BLE001 — a failed scan must not break the app
                st.error(f"Scan failed: {exc}")
            else:
                if _scan.get("status") == "stopped":
                    st.error("Kill-switch is on — scan refused.")
                elif _scan.get("proposals"):
                    st.success(f"Scan done — {len(_scan['proposals'])} proposal(s). "
                               "Nothing was placed. Tap APPROVE on one below.")
                else:
                    st.info("Scan done — no trade triggered today. That is "
                            "normal; forcing a trade is worse than waiting.")
                if _scan.get("failed_symbols"):
                    st.warning(f"Some symbols failed to fetch: "
                               f"{list(_scan['failed_symbols'])} — no data invented.")
                st.rerun()
        # Re-read status after a possible scan, so proposals show at once.
        _priv = get_private_status()
        st.subheader("Proposals — tap APPROVE on one, or REJECT it")
        if not _priv["pending_proposals"]:
            st.write("No proposals waiting. Run a scan above.")
        for _prop in _priv["pending_proposals"]:
            with st.container(border=True):
                if _prop.get("kind") == "exit":
                    st.write(f"**EXIT {_prop['symbol']}** — {_prop.get('reason', '')}")
                else:
                    st.write(f"**BUY {_prop['symbol']}** ({_prop.get('strategy', '')})")
                    st.write(f"Entry: **${_prop['entry_price']:,.2f}** — "
                             f"spend **${_prop['notional_usd']:,.2f}** — "
                             f"stop **${_prop['stop_loss']:,.2f}** — "
                             f"target **${_prop['take_profit']:,.2f}**")
                    st.write(f"Risk if the stop fires: **${_prop['risk_usd']:,.2f}** — "
                             f"gain if the target fills: **${_prop['target_usd']:,.2f}**")
                    st.caption(_prop.get("reason", ""))
                _ap, _rj = st.columns(2)
                if _ap.button(f"✅ APPROVE {_prop['proposal_id']}",
                              use_container_width=True,
                              key=f"priv_approve_{_prop['proposal_id']}"):
                    try:
                        _res = approve_proposal(_prop["proposal_id"])
                    except Exception as exc:  # noqa: BLE001 — live-gate refusal, etc.
                        st.error(f"Approval refused: {exc}")
                    else:
                        if _res.get("status") == "ok" and _res.get("placed"):
                            st.success(f"Placed: {_res['placed']} "
                                       f"(mode: {_res.get('mode', '')}).")
                        elif _res.get("status") == "stopped":
                            st.error("Kill-switch is on — approval refused.")
                        else:
                            st.error(f"Approval did not place a trade: {_res}")
                    st.rerun()
                if _rj.button(f"❌ REJECT {_prop['proposal_id']}",
                              use_container_width=True,
                              key=f"priv_reject_{_prop['proposal_id']}"):
                    if reject_proposal(_prop["proposal_id"]):
                        st.info("Proposal rejected — no order was placed.")
                    else:
                        st.warning("That proposal was already gone.")
                    st.rerun()
        st.subheader("Open positions")
        if _priv["open_positions"]:
            for _pos in _priv["open_positions"]:
                st.write(f"- **{_pos['symbol']}** — entry "
                         f"${_pos['entry_price']:,.2f} on {_pos.get('entry_date')}, "
                         f"stop ${_pos['stop_loss']:,.2f}, target "
                         f"${_pos['take_profit']:,.2f}, bars held {_pos.get('bars_held', 0)}.")
        else:
            st.write("No open private positions.")
        if st.button("Check live trading gate", use_container_width=True,
                     key="private_live_gate"):
            _gate = check_live_gate()
            if _gate["live_open"]:
                st.success("Live gate is open — live trading is possible. "
                           "It was opened by hand, not from this UI.")
            else:
                st.error("Live trading is LOCKED. Missing locks:")
                for _lock in _gate["missing_locks"]:
                    st.write(f"- {_lock}")
        if _priv["kill_switch_on"]:
            if st.button("▶️ Clear kill-switch — resume private trading",
                         use_container_width=True, key="private_clear_stop"):
                clear_kill_switch()
                st.success("Kill-switch cleared. Private trading can resume.")
                st.rerun()
        else:
            if st.button("🛑 KILL SWITCH — stop all private trading now",
                         use_container_width=True, key="private_kill"):
                activate_kill_switch()
                st.error("Kill-switch ON. Scan and approve will refuse until "
                         "you clear it.")
                st.rerun()
        st.caption("Phone access needs the hosted deploy — see DEPLOY.md. "
                   "Until the app is deployed on Streamlit Cloud, it only "
                   "runs on a local PC at localhost:8501.")

st.markdown("---")
st.caption(DISCLOSURE)
