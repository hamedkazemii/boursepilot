"""تعریف جداول SQLite نسخه v1 History Engine."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    ins_code TEXT NOT NULL DEFAULT '',
    isin TEXT,
    fund_type TEXT NOT NULL DEFAULT '',
    sector TEXT,
    sector_id INTEGER,
    board TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TEXT,
    last_seen_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_funds_type ON funds(fund_type);
CREATE INDEX IF NOT EXISTS idx_funds_ins ON funds(ins_code);

CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    last_price REAL,
    yesterday_price REAL,
    volume REAL,
    value REAL,
    trade_count INTEGER,
    change_pct REAL,
    bid_qty REAL,
    ask_qty REAL,
    buy_real_volume REAL,
    sell_real_volume REAL,
    buy_legal_volume REAL,
    sell_legal_volume REAL,
    source TEXT NOT NULL DEFAULT 'brs',
    created_at TEXT NOT NULL,
    UNIQUE(fund_id, trade_date),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_history_date ON history(trade_date);
CREATE INDEX IF NOT EXISTS idx_history_fund_date ON history(fund_id, trade_date);

CREATE TABLE IF NOT EXISTS nav_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    nav_date TEXT NOT NULL,
    issue_nav REAL,
    redeem_nav REAL,
    premium_pct REAL,
    market_price REAL,
    source TEXT NOT NULL DEFAULT 'brs',
    created_at TEXT NOT NULL,
    UNIQUE(fund_id, nav_date),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nav_date ON nav_history(nav_date);

CREATE TABLE IF NOT EXISTS market_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_at TEXT NOT NULL,
    trade_date TEXT NOT NULL,
    funds_count INTEGER NOT NULL DEFAULT 0,
    market_status TEXT,
    market_power REAL,
    best_group TEXT,
    worst_group TEXT,
    total_value REAL,
    total_volume REAL,
    avg_change_pct REAL,
    payload_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_snap_date ON market_snapshot(trade_date);

CREATE TABLE IF NOT EXISTS daily_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    score_date TEXT NOT NULL,
    final_score REAL NOT NULL,
    rank INTEGER,
    recommendation TEXT,
    recommendation_label TEXT,
    trend_score REAL,
    liquidity_score REAL,
    risk_score REAL,
    money_flow_score REAL,
    nav_score REAL,
    volume_score REAL,
    technical_score REAL,
    historical_return_score REAL,
    ai_confidence REAL,
    factors_json TEXT,
    reasons_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(fund_id, score_date),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_daily_scores_date ON daily_scores(score_date);
CREATE INDEX IF NOT EXISTS idx_daily_scores_rank ON daily_scores(score_date, rank);

CREATE TABLE IF NOT EXISTS request_cache (
    cache_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    params_json TEXT,
    response_json TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_request_cache_exp ON request_cache(expires_at);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'"
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO schema_meta(key, value) VALUES('version', ?)",
            (str(SCHEMA_VERSION),),
        )
    else:
        conn.execute(
            "UPDATE schema_meta SET value = ? WHERE key = 'version'",
            (str(SCHEMA_VERSION),),
        )
