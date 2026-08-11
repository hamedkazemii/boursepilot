import sqlite3
conn = sqlite3.connect("data/database.db")
conn.row_factory = sqlite3.Row

# Check old funds table
rows = conn.execute("SELECT symbol, name, fund_type, sector, is_fund_like FROM funds WHERE is_active=1 ORDER BY symbol").fetchall()
print("OLD funds table (active):")
fund_like = [r for r in rows if r["is_fund_like"] == 1]
non_fund = [r for r in rows if r["is_fund_like"] == 0]
print(f"  fund_like=1: {len(fund_like)}")
print(f"  fund_like=0: {len(non_fund)}")
for r in fund_like[:20]:
    print(f"    {r['symbol']} | {r['name'][:30]} | type={r['fund_type']} | sector={r['sector']}")
print("...")
for r in non_fund[:20]:
    print(f"    {r['symbol']} | {r['name'][:30]} | type={r['fund_type']} | sector={r['sector']}")
print("...")

# Check derivative symbols (ending with digit)
deriv = [r for r in rows if r["symbol"][-1:].isdigit()]
print(f"\nDerivative symbols (ending with digit): {len(deriv)}")
for r in deriv[:20]:
    print(f"    {r['symbol']} | {r['name'][:30]} | type={r['fund_type']}")

# Check new fund_universe
rows2 = conn.execute("SELECT symbol, name, isin, cs_id, is_active FROM fund_universe ORDER BY symbol").fetchall()
print(f"\nNEW fund_universe table:")
print(f"  Total: {len(rows2)}")
active2 = [r for r in rows2 if r["is_active"] == 1]
inactive2 = [r for r in rows2 if r["is_active"] == 0]
print(f"  Active: {len(active2)}")
print(f"  Inactive: {len(inactive2)}")