import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT symbol, name, fund_type FROM funds WHERE is_active=1 AND fund_type IN ('طلا', 'کالایی', 'اهرم') ORDER BY fund_type, symbol").fetchall()
for r in rows:
    print(r["symbol"], r["name"], r["fund_type"])