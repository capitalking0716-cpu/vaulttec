"""VaultTec — Streamlit dashboard (Phase 1, paper trading only).

Run:  streamlit run app.py
Design: obsidian black / deep violet purple / metallic gold — matched to the
official VaultTec logo (gold V, purple T, crown, black/purple/gold).
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

from vaulttec.ai_assistant import Assistant  # kept for reference; Ava replaces it in the app
from vaulttec.ava import Ava, list_clips, load_lessons, random_clip, review_closed_trades
from vaulttec.analytics import (
    accuracy_summary, analyse_history, backtest_macd_crossover,
    backtest_sma_crossover, generate_signal, get_signal_history,
    record_signal, run_backtest_suite, scan_watchlist, top_opportunities,
)
from vaulttec.analytics.signal_history import init_signal_history
from vaulttec.automation import AutomationEngine
from vaulttec.charts import (
    GOLD, PURPLE, UP, allocation_chart, candlestick_chart, cumulative_pnl_chart,
    indicator_chart, pnl_by_symbol_chart, scanner_confidence_chart,
    sparkline_chart, strategy_comparison_chart,
)
from vaulttec.config import RISK_PROFILES, get_settings
from vaulttec.db import init_db
from vaulttec.db.models import UserProfile
from vaulttec.market import analyse_indicators, fetch_history, get_provider
from vaulttec.paper_trading import PaperTradingEngine
from vaulttec.portfolio import Portfolio
from vaulttec.profile_store import load_profile, profile_snapshot, save_profile
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
from vaulttec.shadow_bridge import (
    build_context_snapshot, load_notes, load_questions, save_question,
)

DISCLOSURE = (
    "⚠️ Risk disclosure: Trading involves substantial risk of loss. "
    "VaultTec does not promise guaranteed profits and does not advertise "
    "unverified accuracy. Past performance does not guarantee future results. "
    "This is PAPER TRADING with virtual money only — no live brokerage, "
    "no real money, no leverage, no options."
)

st.set_page_config(page_title="VaultTec — Financial Intelligence", page_icon="🏦", layout="wide")

# --- VaultTec dashboard theme: black / deep purple / metallic gold --------
# Glowing purple-bordered cards, gold headings, no character imagery
# anywhere — the look is the vault, not a person in it.
st.markdown("""
<style>
.vt-title { text-align: center; font-size: 42px; font-weight: 800;
  letter-spacing: 6px; margin: 0;
  background: linear-gradient(90deg, #f5c542, #d4af37, #f5c542);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.vt-subtitle { text-align: center; color: #b9a8e8; letter-spacing: 4px;
  font-size: 13px; margin: 0 0 4px 0; }
.vt-tagline { text-align: center; color: #8b2ff7; letter-spacing: 3px;
  font-size: 12px; margin-bottom: 18px; }
.vt-card { border: 1px solid #5b21b6; border-radius: 10px;
  background: #121214; padding: 14px 16px; margin-bottom: 10px;
  box-shadow: 0 0 14px rgba(139, 47, 247, 0.25); }
.vt-card-label { color: #b9a8e8; font-size: 13px; margin: 0; }
.vt-card-value { color: #d4af37; font-size: 26px; font-weight: 700; margin: 2px 0; }
.vt-card-delta { font-size: 13px; margin: 0; }
.vt-up { color: #26a69a; } .vt-down { color: #ef5350; }
.vt-tool { border: 1px solid #5b21b6; border-radius: 10px;
  background: #121214; padding: 12px; text-align: center; margin-bottom: 10px;
  box-shadow: 0 0 10px rgba(139, 47, 247, 0.20); }
.vt-tool b { color: #e8e4d8; } .vt-tool span { color: #26a69a; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

LOGO_PATH = Path(__file__).parent / "assets" / "vaulttec-logo.png"

# --- Vault styling: obsidian black / deep violet / metallic gold ----------
# Colours sampled from the official logo: gold #d4af37, violet #8b2ff7,
# deep purple #5b21b6, obsidian #0b0b0d, charcoal #121214.
st.markdown(
    """
    <style>
    .stApp { background-color: #0b0b0d; color: #e8e4d8; }
    h1, h2, h3 { color: #d4af37 !important; font-family: Georgia, serif; letter-spacing: 0.04em; }
    h2 { border-bottom: 2px solid #5b21b6; padding-bottom: 6px; }
    .stMetric { background: #17171b; border: 1px solid #5b21b6; border-radius: 8px; padding: 12px; }
    .stMetric label, .stMetric div { color: #e8e4d8 !important; }
    .stButton>button { background: linear-gradient(90deg, #d4af37, #b8860b); color: #0b0b0d; font-weight: bold; border: none; min-height: 48px; font-size: 16px; }
    .stButton>button:hover { background: #e8c766; color: #0b0b0d; }
    .stButton>button[kind="secondary"] { background: #5b21b6; color: #ffffff; }
    @media (max-width: 600px) { .stMetric { padding: 8px; } .stMetric label { font-size: 13px; } }
    /* Tabs: short labels, scrollable on a phone so no section is a long scroll. */
    [data-testid="stTabs"] button { font-size: 14px; padding: 8px 10px; white-space: nowrap; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #d4af37 !important; border-bottom: 2px solid #8b2ff7 !important; }
    section[data-testid="stSidebar"] { background-color: #121214; border-right: 2px solid #5b21b6; }
    div[data-testid="stAlert"] { border: 1px solid #5b21b6; }
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
# Profile memory: load the saved profile from data/profile.json (local
# only, never pushed to GitHub) so the app remembers who the user is
# and what risk limits they set, every time it opens. Without this the
# profile reset to defaults on every reopen — dangerous for a trading
# app, because the risk limits would silently reset too.
if "profile" not in st.session_state:
    st.session_state.profile = load_profile()
    st.session_state._saved_profile = profile_snapshot(st.session_state.profile)
if "portfolio" not in st.session_state:
    st.session_state.portfolio = Portfolio(cash=settings.paper_starting_cash)
if "risk" not in st.session_state:
    st.session_state.risk = RiskEngine()
if "engine" not in st.session_state:
    st.session_state.engine = PaperTradingEngine(st.session_state.portfolio, st.session_state.risk)
if "ava" not in st.session_state:
    # Ava replaces the old Vault assistant in the app. She is her own
    # AI, not Shadow — Shadow is the chat assistant; Ava lives here.
    st.session_state.ava = Ava()
if "automation" not in st.session_state:
    # One automation engine for the whole session. Phase 3 fix: the
    # emergency-stop button used to build a throwaway engine, so the
    # stop was logged nowhere and never actually paused anything.
    st.session_state.automation = AutomationEngine(st.session_state.profile)

profile: UserProfile = st.session_state.profile
automation: AutomationEngine = st.session_state.automation
portfolio: Portfolio = st.session_state.portfolio
engine: PaperTradingEngine = st.session_state.engine

# --- Sidebar: profile settings --------------------------------------------
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)
st.sidebar.title("VAULTTEC")
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
# Save the profile whenever anything in it changed, so the next open
# remembers this user and these risk limits.
if profile_snapshot(profile) != st.session_state.get("_saved_profile"):
    save_profile(profile)
    st.session_state._saved_profile = profile_snapshot(profile)
    st.sidebar.caption(f"Saved — welcome back, {profile.name}.")
st.sidebar.markdown("---")
st.sidebar.subheader("Automation")
st.sidebar.write(f"Automation: **{'ON (paper only)' if automation.enabled else 'OFF'}**")
if st.sidebar.button("🛑 EMERGENCY STOP — pause automation", use_container_width=True):
    automation.kill_switch()
    st.sidebar.error("Automation stopped.")
if automation.paused:
    if st.sidebar.button("Resume automation (needs re-enable)", use_container_width=True):
        automation.resume()
        st.sidebar.info("Paused flag cleared. Enable automation again below to restart it.")
st.sidebar.caption("Automation is paper-only and never bypasses risk limits.")
st.sidebar.markdown("---")
st.sidebar.info(DISCLOSURE)

# --- Header ----------------------------------------------------------------
if LOGO_PATH.exists():
    st.image(str(LOGO_PATH), use_container_width=True)
st.caption("AI Trading & Investment Intelligence — paper trading only. The heart of the family trust.")
st.warning(DISCLOSURE)


# --- Tabs: one short scroll per section, not one long page -------------
# Order matches the original layout, so every variable a later
# section needs is still defined before it is used.
tab_dashboard, tab_scanner, tab_trade, tab_results, tab_live_paper, tab_private, tab_shadow = st.tabs(["Dashboard", "Scanner", "Trade", "Results", "Live Paper", "Private", "Shadow"])

with tab_dashboard:
    # --- VaultTec dashboard theme: gold header, glowing metric cards,
    # big candlestick chart, assets / tools / Ava row. No character
    # imagery — the look is the vault itself.
    import datetime as _dt
    _today = _dt.datetime.now().strftime("%I:%M %p EST · %b %d, %Y")
    st.markdown(
        f'<p class="vt-title">VAULTTEC</p>'
        f'<p class="vt-subtitle">AI-POWERED TRADING PLATFORM</p>'
        f'<p class="vt-tagline">🟢 LIVE MARKET &nbsp;·&nbsp; {_today} &nbsp;·&nbsp; '
        f'BUILD WEALTH ◆ CONTROL YOUR FUTURE</p>',
        unsafe_allow_html=True,
    )

    # --- Portfolio metrics -----------------------------------------------------
    quotes = {s: provider.get_quote(s) for s in settings.watchlist}
    prices = {s: q.price for s, q in quotes.items()}
    value = portfolio.value(prices)
    pnl = value - settings.paper_starting_cash
    closed_trades = [t for t in engine.trades if t.status == "closed"]
    wins = sum(1 for t in closed_trades if (t.pnl or 0) > 0)
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else None
    win_label = f"{win_rate:.1f}%" if win_rate is not None else "—"
    win_delta = (f"{len(closed_trades)} closed trade(s), {wins} win(s)"
                 if closed_trades else "No closed trades yet — win rate starts with your first close")
    pnl_class = "vt-up" if pnl >= 0 else "vt-down"
    pnl_arrow = "▲" if pnl >= 0 else "▼"

    def _metric_card(label: str, value_text: str, delta: str, delta_class: str = "vt-up"):
        st.markdown(
            f'<div class="vt-card"><p class="vt-card-label">{label}</p>'
            f'<p class="vt-card-value">{value_text}</p>'
            f'<p class="vt-card-delta {delta_class}">{delta}</p></div>',
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("Total Portfolio", f"${value:,.2f}",
                     f"{pnl_arrow} {pnl:+,.2f} vs start" if pnl else "Paper money only",
                     pnl_class)
        st.plotly_chart(sparkline_chart(
            provider.get_history("SPY", days=60)["close"].tolist(), UP),
            use_container_width=True)
    with c2:
        _metric_card("Total P&L (paper)", f"${pnl:,.2f}",
                     f"{pnl_arrow} {pnl / settings.paper_starting_cash * 100:+.1f}% of starting cash",
                     pnl_class)
        st.plotly_chart(sparkline_chart(
            provider.get_history("BTC-USD", days=60)["close"].tolist(), GOLD),
            use_container_width=True)
    with c3:
        _metric_card("Win Rate", win_label, win_delta,
                     "vt-up" if (win_rate or 0) >= 50 else "vt-down")
        if closed_trades:
            _cum, _run = [0.0], 0.0
            for _t in closed_trades:
                _run += _t.pnl or 0
                _cum.append(_run)
            st.plotly_chart(sparkline_chart(_cum, PURPLE), use_container_width=True)
        else:
            st.write("Paper trades only — no wins or losses yet.")
    with c4:
        _metric_card("Active AI Agents", "Ava + Scanner",
                     "🟢 Online — Ava answers in Results", "vt-up")
        _conf = [s.confidence * 100 for s in
                 [generate_signal(sym, provider.get_history(sym))
                  for sym in settings.watchlist]]
        st.plotly_chart(sparkline_chart(_conf, PURPLE), use_container_width=True)

    # --- Market Overview: the big candlestick chart --------------------------
    _signals_preview = [
        generate_signal(sym, provider.get_history(sym)) for sym in settings.watchlist
    ]
    _best = max(_signals_preview, key=lambda s: s.confidence)
    _best_hist = provider.get_history(_best.symbol, days=120)
    _best_q = quotes[_best.symbol]
    _b_arrow = "▲" if _best_q.change_pct >= 0 else "▼"
    st.subheader(f"📈 Market Overview — {_best.symbol} "
                 f"${_best_q.price:,.2f} {_b_arrow} {_best_q.change_pct:+.2f}%")
    st.caption(f"Strongest signal right now: {_best.symbol} — {_best.direction} "
               f"({_best.confidence:.0%} confidence). A signal is not a trade.")
    st.plotly_chart(candlestick_chart(_best_hist, _best.symbol),
                    use_container_width=True)
    st.plotly_chart(indicator_chart(_best_hist, _best.symbol),
                    use_container_width=True)

    # --- Bottom row: Your Assets / Trading Tools / Ava ------------------------
    _b1, _b2, _b3 = st.columns(3)
    with _b1:
        st.subheader("💰 Your Assets")
        _rows = []
        for _sym, _h in portfolio.holdings.items():
            _rows.append({"Asset": _sym, "Qty": _h.quantity,
                          "Price": f"${prices.get(_sym, _h.avg_cost):,.2f}",
                          "Value": f"${_h.quantity * prices.get(_sym, _h.avg_cost):,.2f}"})
        for _sym in settings.watchlist:
            if _sym not in portfolio.holdings:
                _q = quotes[_sym]
                _rows.append({"Asset": _sym, "Qty": "—",
                              "Price": f"${_q.price:,.2f}",
                              "Value": f"{_q.change_pct:+.2f}%"})
        st.table(_rows)
    with _b2:
        st.subheader("🛠️ Trading Tools")
        _tools = [
            ("🤖 Auto Trade", "ON" if automation.enabled else "OFF — your choice"),
            ("🔎 Market Scanner", "Scanner tab"),
            ("🧪 Backtest", "Results tab"),
            ("🛡️ Risk Control", "Trade tab — wide-6"),
            ("💜 Ava", "Results tab — ask her"),
            ("🔄 Portfolio Sync", "Live Paper tab"),
        ]
        for _i in range(0, len(_tools), 2):
            _t1, _t2 = st.columns(2)
            for _col, (_name, _status) in zip((_t1, _t2), _tools[_i:_i + 2]):
                _col.markdown(
                    f'<div class="vt-tool"><b>{_name}</b><br><span>{_status}</span></div>',
                    unsafe_allow_html=True,
                )
    with _b3:
        st.subheader("💜 Ava")
        _ava_img = Path(__file__).resolve().parent / "assets" / "ava.png"
        if _ava_img.exists():
            st.image(str(_ava_img), width=180)
        st.write("Ava — your trading AI. She hates losing money, learns "
                 "from every closed trade, and never places one herself. "
                 "Ask her in the Results tab.")

    # --- Dashboard charts: allocation + P&L by symbol ------------------------
    holdings_value = {
        s: h.quantity * prices.get(s, h.avg_cost)
        for s, h in portfolio.holdings.items()
    }
    chart1, chart2 = st.columns(2)
    chart1.plotly_chart(allocation_chart(portfolio.cash, holdings_value),
                        use_container_width=True)
    if engine.trades:
        chart2.plotly_chart(pnl_by_symbol_chart(engine.trades, prices),
                            use_container_width=True)
    else:
        chart2.write("No paper trades yet — place your first trade in the "
                     "Trade tab and the P&L chart will appear here.")

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
    conf_fig = scanner_confidence_chart(scan_results)
    if conf_fig is not None:
        st.plotly_chart(conf_fig, use_container_width=True)
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
    st.plotly_chart(candlestick_chart(ta_history, ta_symbol), use_container_width=True)
    st.plotly_chart(indicator_chart(ta_history, ta_symbol), use_container_width=True)

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
    # --- Trade desk: place paper trades. No coaching, no Challenge,
    # no course — just trading, with the Risk Engine checking every order.
    st.header("📈 Trade — place a paper trade")
    st.caption("Paper trading only — virtual money. Every order goes through "
               "the Risk Engine first: stop-loss required, position sized to "
               "your limits. You decide every trade — nothing auto-buys.")
    trade_symbol = st.selectbox("Symbol", settings.watchlist, key="trade_symbol")
    trade_q = quotes[trade_symbol]
    trade_history = provider.get_history(trade_symbol)
    trade_sig = generate_signal(trade_symbol, trade_history)
    st.write(f"**{trade_symbol}** — ${trade_q.price:,.2f} — signal: "
             f"**{trade_sig.direction}** ({trade_sig.confidence:.0%})")
    st.write(trade_sig.evidence)
    trade_check = st.session_state.risk.check_order(
        symbol=trade_symbol, price=trade_q.price, quantity=1,
        stop_loss=trade_q.price * 0.94, take_profit=trade_q.price * 1.09,
        portfolio_value=value,
        current_exposure=portfolio.exposure(prices),
    )
    trade_qty = st.number_input(
        "Quantity (shares)", min_value=1,
        max_value=max(1, int(trade_check.max_quantity)),
        value=1, step=1, key="trade_qty")
    trade_sl = st.number_input(
        "Stop-loss ($)", value=trade_check.suggested_stop_loss,
        step=0.5, key="trade_sl")
    trade_tp = st.number_input(
        "Take-profit ($)", value=trade_check.suggested_take_profit,
        step=0.5, key="trade_tp")
    st.write(f"Risk on this trade: about "
             f"${abs(trade_q.price - trade_sl) * trade_qty:,.2f} if the stop hits, "
             f"about ${abs(trade_tp - trade_q.price) * trade_qty:,.2f} if the target hits.")
    if st.button("✅ Place this paper trade", use_container_width=True):
        trade = engine.place_order(
            trade_symbol, "buy", trade_qty, trade_q.price, trade_sl, trade_tp,
            reason=trade_sig.evidence, source="manual")
        if trade:
            st.success(f"Paper trade placed: {trade_qty} × {trade_symbol} @ "
                       f"${trade_q.price:,.2f} (virtual money).")
        else:
            st.error("Trade BLOCKED by the Risk Engine:")
            for r in engine.blocked[-1]["reasons"]:
                st.write(f"- {r}")
    # --- Open positions: close one by hand ----------------------------------
    st.subheader("Open positions")
    open_trades = [t for t in engine.trades if t.status == "open"]
    if not open_trades:
        st.write("No open paper positions right now.")
    for t in open_trades:
        col1, col2 = st.columns([3, 1])
        col1.write(f"**{t.symbol}** — {t.quantity} × @ ${t.price:,.2f} — "
                   f"stop ${t.stop_loss:,.2f}, target ${t.take_profit:,.2f}")
        if col2.button("Close", key=f"close_{t.symbol}_{t.created_at}"):
            pnl = engine.close_position(t.symbol, prices.get(t.symbol, t.price),
                                        exit_reason="manual close")
            if pnl is not None:
                st.success(f"Closed {t.symbol} — P&L ${pnl:,.2f} (paper).")
            else:
                st.error(f"Could not close {t.symbol}.")
    # --- Supervised automation (paper only, your choice) ---------------------
    st.subheader("Supervised automation (paper only)")
    if automation.enabled:
        st.write("🤖 Supervised automation is **ON** — paper trades only, inside your profile limits.")
    elif st.button("Enable supervised automation (paper only)", use_container_width=True):
        if automation.enable():
            st.success("Automation enabled — paper only, risk-checked, kill-switch ready.")
        else:
            st.error("Automation could not be enabled.")


with tab_results:
    # --- Trading history -------------------------------------------------------
    st.header("📓 Trading history (paper)")
    if engine.trades:
        st.table([{"Symbol": t.symbol, "Side": t.side, "Qty": t.quantity, "Price": t.price,
                   "Stop": t.stop_loss, "Target": t.take_profit, "Source": t.source}
                  for t in engine.trades])
    else:
        st.write("No paper trades yet. Your first paper trade starts the journal — "
                 "aim for 30–50 paper trades before any live trading is even considered.")
    cum_fig = cumulative_pnl_chart(engine.trades)
    if cum_fig is not None:
        st.plotly_chart(cum_fig, use_container_width=True)

    # --- Ava — the trading AI inside the app (replaces the old Vault assistant)
    st.header("💜 Ava — your trading AI")
    _ava_path = Path(__file__).resolve().parent / "assets" / "ava.png"
    if _ava_path.exists():
        st.image(str(_ava_path), width=220)
    _ava_ctx = build_context_snapshot(
        profile, portfolio, engine, signals, prices,
        portfolio.cash, value, pnl,
    )
    st.write(st.session_state.ava.brief(_ava_ctx))
    # --- Ava's own brain: online or offline, and a test ---------------------
    _brain = st.session_state.ava.brain_status()
    st.write(_brain["status"])
    if st.button("🧠 Test Ava's brain", use_container_width=True, key="ava_brain_test"):
        st.write(st.session_state.ava.ask(
            "Say hello in one line, then tell me your number one risk rule.",
            _ava_ctx))
    # --- Ava's clips: she chills, then shows off ----------------------------
    # Clips are .mp4 files in assets/clips/. Drop a new one in that folder
    # and it appears here automatically — that is how more get added later.
    _clips = list_clips()
    if _clips:
        st.subheader("🎬 Watch Ava")
        _clip_labels = [c["label"] for c in _clips]
        _picked = st.selectbox("Pick a clip — or let her surprise you",
                               ["🎲 Surprise me"] + _clip_labels, key="ava_clip_pick")
        if st.button("▶️ Play", use_container_width=True, key="ava_clip_play"):
            if _picked == "🎲 Surprise me":
                _clip = random_clip()
            else:
                _clip = next(c for c in _clips if c["label"] == _picked)
            if _clip:
                st.write(f"**{_clip['label']}**")
                st.video(_clip["file"])
    else:
        st.caption("No Ava clips saved yet — save .mp4 files into "
                   "assets/clips/ and they will appear here.")
    if st.button("📖 Review my closed trades — learn from them",
                 use_container_width=True, key="ava_review"):
        _new_lessons = review_closed_trades(engine)
        if _new_lessons:
            st.success(f"Ava learned {_new_lessons} new lesson(s) from your closed trades.")
        else:
            st.write("Nothing new to learn yet — every closed trade already has a lesson, "
                     "or no trades have closed yet.")
    _ava_lessons = load_lessons(limit=5)
    if _ava_lessons:
        st.subheader("What Ava has learned")
        for _lesson in _ava_lessons:
            st.write(f"- {_lesson['lesson']}")
    _ava_q = st.text_input("Ask Ava a question",
                           placeholder="e.g. Should I close GOOGL? Is META worth a trade today?",
                           key="ava_question")
    if _ava_q:
        st.write(st.session_state.ava.ask(_ava_q, _ava_ctx))

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
    st.plotly_chart(strategy_comparison_chart(suite["strategies"]),
                    use_container_width=True)
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


    # --- Phase 6: win-rate test -------------------------------------------------
    st.header("📊 Phase 6 — Win-rate test (pickier entries + combined portfolio)")
    phase6_path = Path(__file__).resolve().parent / "validation" / "phase6-win-rate-report.json"
    if phase6_path.exists():
        phase6 = json.loads(phase6_path.read_text())
        st.write("Three new wide-6 variants on OOS-1/2/3 + FRESH-1/2/3/4, from the "
                 "disk cache — no Yahoo re-fetch. Verdict rule, fixed before the run: "
                 "worth keeping when pooled fresh P&L is > $0 AND pooled fresh win rate "
                 "is > 40% AND positive in at least 2 fresh windows AND pooled OOS P&L "
                 "is also > $0. Every variant keeps a stop-loss.")
        for key, label in (("rsi_highconf", "RSI, confidence ≥ 0.70 only"),
                           ("bollinger_highconf", "Bollinger, confidence ≥ 0.70 only"),
                           ("rsi_volume", "RSI, volume > 20-day average only"),
                           ("bollinger_volume", "Bollinger, volume > 20-day average only"),
                           ("combined", "Combined — MR wide-6 + MACD trend, one portfolio")):
            fresh = phase6["pooled_fresh"][key]
            oos = phase6["pooled_oos"][key]
            verdict = phase6["verdict"][key]
            small = " ⚠️ SMALL SAMPLE — too few trades to adopt." if verdict.get("small_sample_fresh") else ""
            st.write(f"**{label}** — fresh: {fresh['trades']} trades, {fresh['win_rate_pct']}% win, "
                     f"paper P&L ${fresh['total_pnl_usd']:,.2f} (expectancy ${fresh['expectancy_usd']:,.2f}/trade), "
                     f"positive in {fresh['positive_windows']}/{fresh['windows_total']} windows; "
                     f"OOS: ${oos['total_pnl_usd']:,.2f} — "
                     f"{'worth keeping' if verdict['worth_keeping'] else 'NOT worth keeping'}.{small}")
        combined = phase6["combined_vs_legs"]
        st.write(f"Combined beats both mean-reversion legs on P&L — fresh "
                 f"${combined['fresh']['combined_pnl_usd']:,.2f} vs RSI "
                 f"${combined['fresh']['rsi_wide6_pnl_usd']:,.2f} / Bollinger "
                 f"${combined['fresh']['bollinger_wide6_pnl_usd']:,.2f}, and OOS "
                 f"${combined['oos']['combined_pnl_usd']:,.2f} vs RSI "
                 f"${combined['oos']['rsi_wide6_pnl_usd']:,.2f} / Bollinger "
                 f"${combined['oos']['bollinger_wide6_pnl_usd']:,.2f} — but its expectancy "
                 f"per trade is lower than either leg alone, so it wins by trading more, "
                 f"not by trading better. The high-confidence gate almost never fires at "
                 f"a mean-reversion entry (RSI: 1 fresh trade of 105 signals) — it is a "
                 f"'don't trade' filter, not a pickier entry. Volume confirmation does not "
                 f"raise the win rate; it just trades less for about the same expectancy.")
        st.caption("Recommendation: keep wide-6 as the lead, test the combined portfolio "
                   "in live paper before adopting it, do NOT adopt the high-confidence gate. "
                   "Live paper evidence is still Day 1 only. Past performance does not "
                   "guarantee future results.")
        st.caption(phase6["note"])
        st.caption("Full report: validation/phase6-win-rate-report.md")
    else:
        st.write("Win-rate test has not been run yet. Run it with: "
                 "`python -m vaulttec.analytics.win_rate`")


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

with tab_shadow:
    # --- Shadow — your assistant, inside YOUR private system only --------
    # This tab is private, like the Private tab: it stays locked until
    # your VaultTec login password is set (VAULTTEC_LOGIN_PASSWORD).
    # It is never part of the public product — no customer ever sees
    # it, and nothing saved here leaves your PC.
    # Shadow does not run inside Streamlit. This tab is the bridge:
    # it shows Shadow exactly what the app sees, saves your question
    # with that context to data/shadow-questions.jsonl (local only),
    # and Shadow answers in the Muse chat with your real numbers in
    # front of it. Nothing here trades or sends anything on its own.
    st.header("🌑 Shadow — ask me, with your real numbers")
    if not login_password_set(_login_password):
        st.error(
            "🔐 Private only — set your VaultTec login password first. "
            "This Shadow tab is part of your private system, not the "
            "public app, so it stays locked until a login password is "
            "set — in Streamlit Cloud, open the app's Settings → Secrets "
            "and add VAULTTEC_LOGIN_PASSWORD = \"the password you choose\", "
            "then reboot the app (see DEPLOY.md)."
        )
    else:
        st.write(
            "I'm Shadow, your assistant — the same one you talk to in chat. "
            "I don't live inside this app, so this tab is how we merge: it "
            "shows me your positions, P&L, signals and limits, and saves "
            "your question with all of that attached. Then ask me in the "
            "Muse chat and I'll answer with your actual app data in front "
            "of me — not generic advice."
        )
        _snap = build_context_snapshot(
            profile, portfolio, engine, signals, prices,
            portfolio.cash, value, pnl,
        )
        _sc1, _sc2, _sc3 = st.columns(3)
        _sc1.metric("Portfolio value (paper)", f"${_snap['portfolio']['value']:,.2f}")
        _sc2.metric("Total P&L (paper)", f"${_snap['portfolio']['pnl']:,.2f}")
        _sc3.metric("Open trades", str(len(_snap["open_trades"])))
        st.subheader("What Shadow sees right now")
        st.json(_snap, expanded=False)
        _q = st.text_area(
            "Ask Shadow a question",
            placeholder="e.g. Should I close GOOGL? What does the scanner think of META today?",
            key="shadow_question",
        )
        if st.button("💾 Save this question for Shadow", use_container_width=True,
                     key="shadow_save"):
            if not _q.strip():
                st.warning("Type a question first.")
            else:
                _path = save_question(_q, _snap)
                st.success(
                    "Saved. Now send me the same question in the Muse chat "
                    "and I'll answer it with these numbers in front of me. "
                    f"(Saved locally at data/shadow-questions.jsonl — never uploaded.)"
                )
        _past = load_questions()
        if _past:
            st.subheader("Your saved questions")
            for _row in _past:
                st.write(f"- **{_row['asked_at'][:16]}** — {_row['question']}")
        _notes = load_notes()
        if _notes:
            st.subheader("Notes from Shadow")
            st.markdown(_notes)

st.markdown("---")
st.caption(DISCLOSURE)
