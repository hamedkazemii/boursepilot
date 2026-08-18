"""تعریف جداول SQLite — History + Users + AI memory + Sync V2."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 7

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

-- Fund Universe (Source of Truth: BRS AllSymbols, cs_id=68 only)
CREATE TABLE IF NOT EXISTS fund_universe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    isin TEXT UNIQUE,
    ins_code TEXT,
    cs TEXT NOT NULL,
    cs_id INTEGER NOT NULL,
    cs_sub TEXT,
    cs_sub_id INTEGER,
    board TEXT,
    board_id INTEGER,
    shares INTEGER,
    market_value INTEGER,
    last_price REAL,
    close_price REAL,
    yesterday_price REAL,
    nav_issue REAL,
    nav_redeem REAL,
    is_active INTEGER NOT NULL DEFAULT 1,
    synced_at TEXT NOT NULL,
    UNIQUE(isin) ON CONFLICT REPLACE
);

CREATE INDEX IF NOT EXISTS idx_fund_universe_symbol ON fund_universe(symbol);
CREATE INDEX IF NOT EXISTS idx_fund_universe_isin ON fund_universe(isin);
CREATE INDEX IF NOT EXISTS idx_fund_universe_ins_code ON fund_universe(ins_code);
CREATE INDEX IF NOT EXISTS idx_fund_universe_active ON fund_universe(is_active);

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
    change_pct REAL,           -- change_close_pct (pcp)
    change_last_pct REAL,      -- change_last_pct (plp)
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
CREATE INDEX IF NOT EXISTS idx_history_fund_date_time ON history(fund_id, trade_date, snapshot_time);

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
    snapshot_time TEXT DEFAULT NULL,
    UNIQUE(fund_id, nav_date),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nav_date ON nav_history(nav_date);

-- Candlesticks (کندل‌های شمعی تعدیل‌شده برای تحلیل تکنیکال)
CREATE TABLE IF NOT EXISTS candlesticks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    trade_date TEXT NOT NULL,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume REAL,
    value REAL,
    candlestick_type INTEGER NOT NULL DEFAULT 3,  -- 1=لحظه‌ای، 2=روزانه تعدیل‌نشده، 3=روزانه تعدیل‌شده
    source TEXT NOT NULL DEFAULT 'brs_candlestick',
    created_at TEXT NOT NULL,
    UNIQUE(fund_id, trade_date, candlestick_type),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_candlesticks_fund_date ON candlesticks(fund_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_candlesticks_date ON candlesticks(trade_date);

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

-- v6.1: trend/momentum columns for deep dive (conditional)
-- SQLite doesn't support IF NOT EXISTS for columns, so we use a migration approach
-- This will only run once due to schema_meta version tracking

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
    execution_price REAL,
    gross_trade_value REAL,
    fee REAL,
    net_cash_flow REAL,
    cost_basis REAL,
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

-- KODAL Disclosures (اطلاعیه‌های رسمی سامانه کدال)
CREATE TABLE IF NOT EXISTS kodal_disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_id TEXT NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    importance TEXT NOT NULL,
    category TEXT NOT NULL,
    published_at TEXT NOT NULL,
    url TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kodal_symbol ON kodal_disclosures(symbol);
CREATE INDEX IF NOT EXISTS idx_kodal_published ON kodal_disclosures(published_at);
CREATE INDEX IF NOT EXISTS idx_kodal_importance ON kodal_disclosures(importance);

-- Sync V2 — Receiver persistence tables
CREATE TABLE IF NOT EXISTS received_batches (
    batch_id TEXT PRIMARY KEY,
    source_server TEXT NOT NULL,
    total_chunks INTEGER NOT NULL,
    chunk_size INTEGER NOT NULL,
    record_count INTEGER NOT NULL,
    checksum TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    completed_at TEXT,
    error_message TEXT,
    processed INTEGER NOT NULL DEFAULT 0,
    received_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_received_batches_status ON received_batches(status);
CREATE INDEX IF NOT EXISTS idx_received_batches_received_at ON received_batches(received_at);

CREATE TABLE IF NOT EXISTS received_chunks (
    batch_id TEXT NOT NULL,
    chunk_number INTEGER NOT NULL,
    payload BLOB NOT NULL,
    checksum TEXT NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (batch_id, chunk_number)
);

CREATE TABLE IF NOT EXISTS sync_acknowledgements (
    batch_id TEXT PRIMARY KEY,
    acknowledged_at TEXT NOT NULL,
    acknowledged_by TEXT NOT NULL,
    ack_payload TEXT
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
    
    # Migration: add trend_score/momentum_score columns if not exist
    try:
        conn.execute("ALTER TABLE fund_indicators ADD COLUMN trend_score REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    try:
        conn.execute("ALTER TABLE fund_indicators ADD COLUMN momentum_score REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Migration v7.1: add history columns required by current repository/mapper
    # (open_price, high_price, low_price, close_price, yesterday_price, volume,
    #  value, trade_count, change_pct, bid_qty, ask_qty, buy_real_volume,
    #  sell_real_volume, buy_legal_volume, sell_legal_volume, snapshot_time_semantics)
    _HISTORY_MISSING_COLUMNS = [
        ("open_price", "REAL"),
        ("high_price", "REAL"),
        ("low_price", "REAL"),
        ("close_price", "REAL"),
        ("yesterday_price", "REAL"),
        ("volume", "REAL"),
        ("value", "REAL"),
        ("trade_count", "INTEGER"),
        ("change_pct", "REAL"),
        ("bid_qty", "REAL"),
        ("ask_qty", "REAL"),
        ("buy_real_volume", "REAL"),
        ("sell_real_volume", "REAL"),
        ("buy_legal_volume", "REAL"),
        ("sell_legal_volume", "REAL"),
        ("snapshot_time_semantics", "TEXT"),
    ]
    for col, col_type in _HISTORY_MISSING_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE history ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Migration: add change_last_pct column to history table
    try:
        conn.execute("ALTER TABLE history ADD COLUMN change_last_pct REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Migration: recreate kodal_disclosures without FK constraint
    # Check if FK exists
    fks = conn.execute("PRAGMA foreign_key_list(kodal_disclosures)").fetchall()
    if fks:
        print("Recreating kodal_disclosures without FK...")
        # Backup data
        conn.execute("""
            CREATE TABLE kodal_disclosures_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disclosure_id TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                importance TEXT NOT NULL,
                category TEXT NOT NULL,
                published_at TEXT NOT NULL,
                url TEXT,
                raw_json TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            INSERT INTO kodal_disclosures_new
            SELECT id, disclosure_id, symbol, title, summary, importance, category, 
                   published_at, url, raw_json, created_at
            FROM kodal_disclosures
        """)
        conn.execute("DROP TABLE kodal_disclosures")
        conn.execute("ALTER TABLE kodal_disclosures_new RENAME TO kodal_disclosures")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kodal_symbol ON kodal_disclosures(symbol)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kodal_published ON kodal_disclosures(published_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kodal_importance ON kodal_disclosures(importance)")
        print("kodal_disclosures recreated without FK")

    # Migration v7.2: add transaction/cost-basis columns to portfolio_items
    _PORTFOLIO_NEW_COLUMNS = [
        ("execution_price", "REAL"),
        ("gross_trade_value", "REAL"),
        ("fee", "REAL"),
        ("net_cash_flow", "REAL"),
        ("cost_basis", "REAL"),
    ]
    for col, col_type in _PORTFOLIO_NEW_COLUMNS:
        try:
            conn.execute(f"ALTER TABLE portfolio_items ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists
