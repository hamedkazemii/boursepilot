from services.discovery.universe_store import get_valid_fund_universe
universe = get_valid_fund_universe()
print(f"Total fund universe entries: {len(universe)}")
funds = [f for f in universe if f.get("cs_id") == 68]
print(f"Fund-like (cs_id=68) entries: {len(funds)}")
non_funds = [f for f in universe if f.get("cs_id") != 68]
print(f"Non-fund entries: {len(non_funds)}")
for f in non_funds[:5]:
    print(f"  {f.get('symbol')}: {f.get('name')} (cs_id={f.get('cs_id')}, cs_sub_id={f.get('cs_sub_id')})")