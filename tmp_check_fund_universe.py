import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row

# Check fund_universe for duplicates
rows = conn.execute("SELECT symbol, name, isin FROM fund_universe WHERE is_active=1 ORDER BY symbol").fetchall()
print(f"Total active in fund_universe: {len(rows)}")

# Find symbols ending with digit
deriv = [r for r in rows if r["symbol"][-1:].isdigit()]
print(f"Derivative symbols (ending with digit): {len(deriv)}")
for r in deriv:
    print(f"  {r['symbol']} | {r['name'][:30]} | ISIN={r['isin']}")

# Check for duplicate ISINs
from collections import defaultdict
isin_map = defaultdict(list)
for r in rows:
    if r["isin"]:
        isin_map[r["isin"]].append(r["symbol"])
dupes = {k:v for k,v in isin_map.items() if len(v) > 1}
print(f"\nDuplicate ISINs: {len(dupes)}")
for isin, syms in list(dupes.items())[:10]:
    print(f"  {isin}: {syms}")