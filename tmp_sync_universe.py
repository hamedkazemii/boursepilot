import sys
sys.path.insert(0, ".")
from services.discovery.universe_store import sync_fund_universe
saved, stats = sync_fund_universe()
print(f"Saved: {saved}")
print(f"Stats: {stats}")