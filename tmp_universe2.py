import sys
sys.path.insert(0, ".")
from services.discovery.fund_universe import build_fund_universe
universe = build_fund_universe()
print(f"Total valid funds: {len(universe)}")
for u in universe:
    if u.symbol in ("عیار", "توان", "سرو", "فیروزه", "کوثری"):
        print(f"  {u.symbol} | {u.name[:45]} | ISIN={u.isin} | Board={u.board} | BoardID={u.board_id} | cs_id={u.cs_id} | cs_sub={u.cs_sub} | cs_sub_id={u.cs_sub_id}")