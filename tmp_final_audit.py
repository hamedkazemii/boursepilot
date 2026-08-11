import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row

print("=== FINAL UNIVERSE AUDIT ===\n")

# Old funds table stats
rows = conn.execute("SELECT COUNT(*) as cnt FROM funds WHERE is_active=1").fetchone()
print(f"OLD funds table (is_active=1): {rows['cnt']}")

rows = conn.execute("SELECT COUNT(*) as cnt FROM funds WHERE is_active=1 AND is_fund_like=1").fetchone()
print(f"OLD funds with is_fund_like=1: {rows['cnt']}")

rows = conn.execute("SELECT COUNT(*) as cnt FROM funds WHERE is_active=1 AND is_fund_like=0").fetchone()
print(f"OLD funds with is_fund_like=0: {rows['cnt']}")

# Derivatives in old funds
rows = conn.execute("SELECT COUNT(*) as cnt FROM funds WHERE is_active=1 AND substr(symbol, -1) IN ('2','3','4') AND length(symbol) > 1").fetchone()
print(f"OLD funds with derivative suffix (2,3,4): {rows['cnt']}")

# New fund_universe
rows = conn.execute("SELECT COUNT(*) as cnt FROM fund_universe WHERE is_active=1").fetchone()
print(f"\nNEW fund_universe (is_active=1): {rows['cnt']}")

# Candlestick history coverage
rows = conn.execute("""
    SELECT fu.symbol, COUNT(h.id) as history_days
    FROM fund_universe fu
    LEFT JOIN history h ON h.fund_id = (
        SELECT id FROM funds WHERE isin = fu.isin AND is_active=1 LIMIT 1
    )
    WHERE fu.is_active=1
    GROUP BY fu.symbol
    HAVING history_days > 0
    ORDER BY history_days DESC
    LIMIT 10
""").fetchall()
print("\nTop 10 funds by history days:")
for r in rows:
    print(f"  {r['symbol']}: {r['history_days']} days")

# Funds with no history
rows = conn.execute("""
    SELECT COUNT(*) as cnt FROM fund_universe fu
    LEFT JOIN history h ON h.fund_id = (
        SELECT id FROM funds WHERE isin = fu.isin AND is_active=1 LIMIT 1
    )
    WHERE fu.is_active=1 AND h.id IS NULL
""").fetchone()
print(f"\nFunds with NO history: {rows['cnt']}")

# Funds with sufficient history (>=250 days)
rows = conn.execute("""
    SELECT COUNT(*) as cnt FROM fund_universe fu
    LEFT JOIN history h ON h.fund_id = (
        SELECT id FROM funds WHERE isin = fu.isin AND is_active=1 LIMIT 1
    )
    WHERE fu.is_active=1
    GROUP BY fu.symbol
    HAVING COUNT(h.id) >= 250
""").fetchall()
print(f"Funds with >=250 days history: {len(rows)}")

# API quota usage summary
print("\n=== API QUOTA USED IN THIS SESSION ===")
print("AllSymbols: 1 call")
print("Symbol: 3 calls (test 3 funds)")
print("Nav: 3 calls (test 3 funds)")  
print("Candlestick: 50+3 = 53 calls (backfill + test 3 funds)")
print("CodalAnnouncement: 0")
print("Shareholder: 0")
print("History: 0")
print("Transaction: 0")