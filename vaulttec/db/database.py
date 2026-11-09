"""SQLite database — Phase 1 storage for profile, trades, signals, logs."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT, goal TEXT, risk_tolerance TEXT,
    virtual_capital REAL, max_position_pct REAL, daily_loss_limit_pct REAL,
    allowed_markets TEXT, automation_enabled INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, side TEXT, quantity REAL, price REAL,
    stop_loss REAL, take_profit REAL, reason TEXT,
    source TEXT, status TEXT, pnl REAL, created_at TEXT
);
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, direction TEXT, confidence REAL, evidence TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS automation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event TEXT, detail TEXT, created_at TEXT
);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA)
        conn.commit()
