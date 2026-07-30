"""تعریف جداول SQLite — History + Users + AI memory."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 2

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

CREATE TABLE IF NOT EXISTS fund_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    as_of_date TEXT NOT NULL,
    ret_1d REAL,
    ret_5d REAL,
    ret_20d REAL,
    ret_60d REAL,
    ret_90d REAL,
    ema20 REAL,
    ema50 REAL,
    ema200 REAL,
    rsi14 REAL,
    macd REAL,
    macd_signal REAL,
    atr14 REAL,
    bb_upper REAL,
    bb_mid REAL,
    bb_lower REAL,
    volatility_20 REAL,
    sharpe_60 REAL,
    sortino_60 REAL,
    max_drawdown_90 REAL,
    avg_volume_20 REAL,
    volume_ratio REAL,
    payload_json TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(fund_id, as_of_date),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_fund_indicators_date ON fund_indicators(as_of_date);

CREATE TABLE IF NOT EXISTS request_cache (
    cache_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    params_json TEXT,
    response_json TEXT,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_request_cache_exp ON request_cache(expires_at);

-- Users / portfolio / AI
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT NOT NULL UNIQUE,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    risk_profile TEXT NOT NULL DEFAULT 'medium',
    horizon_months INTEGER NOT NULL DEFAULT 12,
    capital REAL,
    preferred_groups TEXT,
    locale TEXT NOT NULL DEFAULT 'fa',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_seen_at TEXT
);

CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL DEFAULT 'اصلی',
    base_currency TEXT NOT NULL DEFAULT 'IRR',
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS portfolio_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL DEFAULT 0,
    avg_cost REAL,
    weight_target REAL,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(portfolio_id, symbol),
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, symbol),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ai_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL,           -- global | user:<id> | fund:<symbol>
    key TEXT NOT NULL,
    value_json TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    hits INTEGER NOT NULL DEFAULT 0,
    last_used_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(scope, key)
);

CREATE TABLE IF NOT EXISTS ai_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_date TEXT NOT NULL,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'daily_review',
    quality REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ai_lessons_date ON ai_lessons(lesson_date);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    telegram_id TEXT,
    role TEXT NOT NULL,  -- user|assistant|system
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    # migrations سبک v1→v2: جداول IF NOT EXISTS کافی است
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
