import sys
sys.path.insert(0, ".")
from services.discovery.universe_store import sync_fund_universe, get_valid_fund_universe, get_valid_fund_symbols, get_valid_fund
print("=== Syncing Universe ===")
saved, stats = sync_fund_universe()
print(f"Saved: {saved}")
print(f"Stats: {stats}")

print("\n=== Loading Universe ===")
universe = get_valid_fund_universe()
print(f"Total valid funds: {len(universe)}")
for u in universe[:10]:
    print(f"  {u.symbol} | {u.name[:40]} | ISIN={u.isin}")
print("...")

print("\n=== Lookup Tests ===")
for sym in ["عیار", "توان", "سرو", "فیروزه", "کوثری"]:
    fund = get_valid_fund(sym)
    if fund:
        print(f"  {sym}: OK - {fund.name[:30]}")
    else:
        print(f"  {sym}: NOT FOUND")

print("\n=== Symbols ===")
symbols = get_valid_fund_symbols()
print(f"Total symbols: {len(symbols)}")
print(f"First 10: {symbols[:10]}")