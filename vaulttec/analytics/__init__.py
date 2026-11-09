"""Predictive analytics: signals + backtesting + scanner + signal history
+ Phase 3 validation."""
from .signals import explain_signal_plain, generate_signal, signal_checks
from .backtest import (
    analyse_history, backtest_bollinger_bands, backtest_macd_crossover,
    backtest_rsi, backtest_sma_crossover, max_drawdown_pct,
    run_backtest_suite,
)
from .scanner import scan_symbol, scan_watchlist, top_opportunities
from .signal_history import (
    accuracy_summary, get_signal_history, init_signal_history,
    record_signal, resolve_outcomes,
)
from .validation import render_markdown, run_validation, save_report

__all__ = [
    "generate_signal", "signal_checks", "explain_signal_plain",
    "backtest_sma_crossover", "backtest_macd_crossover", "backtest_rsi",
    "backtest_bollinger_bands", "max_drawdown_pct", "run_backtest_suite",
    "analyse_history",
    "scan_symbol", "scan_watchlist", "top_opportunities",
    "record_signal", "get_signal_history", "resolve_outcomes", "accuracy_summary",
    "init_signal_history",
    "run_validation", "save_report", "render_markdown",
]
