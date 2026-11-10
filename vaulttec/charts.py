"""Charts — the professional trading-platform look.

Plotly charts in VaultTec colours (obsidian black background, metallic
gold, deep violet purple, green up / red down candles). Pure functions:
each takes data and returns a Plotly figure; only app.py imports
Streamlit and calls ``st.plotly_chart`` on them.

Every chart is labelled honestly: backtests and indicators describe
what *did* happen, never a promise about what will happen.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .market.indicators import bollinger_bands, ema, macd, rsi

GOLD = "#d4af37"
PURPLE = "#8b2ff7"
DEEP_PURPLE = "#5b21b6"
BG = "#0b0b0d"
PANEL = "#121214"
TEXT = "#e8e4d8"
GRID = "#2a2a30"
UP = "#26a69a"
DOWN = "#ef5350"


def _dark(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT, family="sans-serif"),
        height=height,
        margin=dict(l=50, r=20, t=40, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID)
    return fig


def candlestick_chart(history: pd.DataFrame, symbol: str) -> go.Figure:
    """Candlesticks + EMA 20/50 + Bollinger Bands + volume, one chart.

    This is the chart a trading platform shows first: price action,
    trend lines and volume together, so the user can see the market
    instead of reading about it in text.
    """
    h = history.tail(120).reset_index(drop=True)
    closes = h["close"]
    bands = bollinger_bands(closes)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.72, 0.28], vertical_spacing=0.04,
        subplot_titles=(f"{symbol} — price, EMA & Bollinger Bands", "Volume"),
    )
    fig.add_trace(go.Candlestick(
        x=h["date"], open=h["open"], high=h["high"], low=h["low"],
        close=h["close"], name="Price",
        increasing_line_color=UP, decreasing_line_color=DOWN,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=ema(closes, 20), name="EMA 20",
                             line=dict(color=GOLD, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=ema(closes, 50), name="EMA 50",
                             line=dict(color=PURPLE, width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=bands["upper"], name="Bollinger upper",
                             line=dict(color=PURPLE, width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=bands["lower"], name="Bollinger lower",
                             line=dict(color=PURPLE, width=1, dash="dot")), row=1, col=1)
    colours = [UP if c >= o else DOWN for c, o in zip(h["close"], h["open"])]
    fig.add_trace(go.Bar(x=h["date"], y=h["volume"], name="Volume",
                         marker_color=colours, showlegend=False), row=2, col=1)
    fig.update_layout(xaxis_rangeslider_visible=False)
    return _dark(fig, height=520)


def indicator_chart(history: pd.DataFrame, symbol: str) -> go.Figure:
    """RSI (with 30/70 lines) above MACD (line, signal, histogram)."""
    h = history.tail(120).reset_index(drop=True)
    closes = h["close"]
    r = rsi(closes)
    m = macd(closes)
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=(f"{symbol} — RSI", f"{symbol} — MACD"),
    )
    fig.add_trace(go.Scatter(x=h["date"], y=r, name="RSI",
                             line=dict(color=GOLD, width=1.5)), row=1, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color=DOWN, row=1, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=UP, row=1, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=m["macd"], name="MACD",
                             line=dict(color=GOLD, width=1.5)), row=2, col=1)
    fig.add_trace(go.Scatter(x=h["date"], y=m["signal"], name="Signal",
                             line=dict(color=PURPLE, width=1.5)), row=2, col=1)
    fig.add_trace(go.Bar(x=h["date"], y=m["histogram"], name="Histogram",
                         marker_color=[UP if v >= 0 else DOWN for v in m["histogram"]],
                         showlegend=False), row=2, col=1)
    return _dark(fig, height=460)


def allocation_chart(cash: float, holdings_value: dict[str, float]) -> go.Figure:
    """Donut: cash vs each holding, by current value."""
    labels = ["Cash"] + list(holdings_value.keys())
    values = [max(cash, 0.0)] + [max(v, 0.0) for v in holdings_value.values()]
    colours = [GRID, GOLD, PURPLE, UP, "#f5c542", "#7b2ff7", DOWN]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colours[: len(labels)], line=dict(color=BG, width=2)),
        textinfo="label+percent",
    ))
    fig.update_layout(title="Portfolio allocation")
    return _dark(fig, height=360)


def pnl_by_symbol_chart(trades: list, prices: dict[str, float]) -> go.Figure:
    """Realised + unrealised P&L per symbol, green for profit, red for loss."""
    from collections import defaultdict

    pnl: dict[str, float] = defaultdict(float)
    for t in trades:
        current = prices.get(t.symbol, t.price)
        if t.status == "closed":
            pnl[t.symbol] += t.pnl
        else:
            pnl[t.symbol] += (current - t.price) * t.quantity
    symbols = list(pnl.keys())
    values = [pnl[s] for s in symbols]
    fig = go.Figure(go.Bar(
        x=symbols, y=values, name="P&L ($)",
        marker_color=[UP if v >= 0 else DOWN for v in values],
        text=[f"${v:,.0f}" for v in values], textposition="outside",
    ))
    fig.update_layout(title="P&L by symbol (paper)", yaxis_title="$")
    return _dark(fig, height=360)


def cumulative_pnl_chart(trades: list) -> go.Figure | None:
    """Cumulative paper P&L as trades close — the equity curve of the journal.

    Returns None when no trade has closed yet, so the app can say so
    instead of drawing an empty chart.
    """
    closed = [t for t in trades if t.status == "closed"]
    if not closed:
        return None
    running, curve = 0.0, [0.0]
    for t in closed:
        running += t.pnl
        curve.append(running)
    fig = go.Figure(go.Scatter(
        x=list(range(len(curve))), y=curve, name="Cumulative P&L",
        line=dict(color=GOLD, width=2), fill="tozeroy",
        fillcolor="rgba(212,175,55,0.15)",
    ))
    fig.update_layout(
        title="Cumulative P&L — closed paper trades",
        xaxis_title="Closed trades", yaxis_title="P&L ($)",
    )
    return _dark(fig, height=360)


def scanner_confidence_chart(scan_results: list[dict]) -> go.Figure | None:
    """Horizontal bars: signal confidence per symbol, strongest first."""
    if not scan_results:
        return None
    rows = sorted(scan_results, key=lambda r: r["confidence"], reverse=True)[:10]
    fig = go.Figure(go.Bar(
        x=[r["confidence"] * 100 for r in rows],
        y=[r["symbol"] for r in rows],
        orientation="h", name="Confidence %",
        marker_color=[GOLD if r["direction"] == "long" else DOWN for r in rows],
        text=[f"{r['confidence']:.0%}" for r in rows], textposition="outside",
    ))
    fig.update_layout(title="Scanner confidence — strongest first",
                      xaxis_title="Confidence %", yaxis=dict(autorange="reversed"))
    return _dark(fig, height=360)


def strategy_comparison_chart(strategies: list[dict]) -> go.Figure:
    """Backtest comparison: total return per strategy, historical only."""
    names = [s["strategy"] for s in strategies]
    returns = [s["total_return_pct"] for s in strategies]
    fig = go.Figure(go.Bar(
        x=names, y=returns, name="Total return %",
        marker_color=[UP if v >= 0 else DOWN for v in returns],
        text=[f"{v:+.1f}%" for v in returns], textposition="outside",
    ))
    fig.update_layout(title="Backtest strategies — historical return only",
                      yaxis_title="Total return %")
    return _dark(fig, height=360)


def sparkline_chart(values: list[float], color: str = UP) -> go.Figure:
    """Tiny sparkline for a metric card — the little rising line under
    the big number, like the reference dashboard. No axes, no legend."""
    fig = go.Figure(go.Scatter(
        y=values, mode="lines", line=dict(color=color, width=2),
        fill="tozeroy", fillcolor="rgba(38,166,154,0.12)",
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
        height=48, margin=dict(l=0, r=0, t=2, b=2),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
    )
    return fig
