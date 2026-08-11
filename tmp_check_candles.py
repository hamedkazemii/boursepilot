import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row

# Check candlestick coverage
rows = conn.execute("""
    SELECT COUNT(DISTINCT fund_id) as funds_with_candles,
           COUNT(*) as total_candles
    FROM candlesticks
""").fetchone()
print(f"Funds with candlesticks: {rows['funds_with_candles']}")
print(f"Total candlesticks: {rows['total_candles']}")

# Check per-fund
rows = conn.execute("""
    SELECT f.symbol, COUNT(c.id) as candle_count
    FROM fund_universe f
    LEFT JOIN funds fu ON f.symbol = fu.symbol
    LEFT JOIN candlesticks c ON fu.id = c.fund_id
    GROUP BY f.symbol
    ORDER BY candle_count DESC
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r['symbol']}: {r['candle_count']} candles")