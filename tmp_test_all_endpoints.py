from config import settings
from services.providers.brs_provider import BrsProvider
provider = BrsProvider()

# Test CODAL
print("=== CODAL Announcements ===")
try:
    announcements = provider.get_codal_announcements(symbol="عیار", category=1, page=1)
    print(f"Count: {len(announcements)}")
    for a in announcements[:3]:
        print(f"  {a.get('published_date')}: {a.get('title')}")
except Exception as e:
    print(f"CODAL ERROR: {e}")

# Test Shareholder
print("\n=== Shareholders ===")
try:
    holders = provider.get_shareholders("عیار")
    print(f"Count: {len(holders)}")
    for h in holders[:3]:
        print(f"  {h.name}: {h.volume} ({h.percent}%)")
except Exception as e:
    print(f"Shareholder ERROR: {e}")

# Test Transaction
print("\n=== Transactions ===")
try:
    txns = provider.get_transaction("عیار")
    print(f"Count: {len(txns)}")
    for t in txns[:3]:
        print(f"  {t}")
except Exception as e:
    print(f"Transaction ERROR: {e}")

# Test History (type=1 for trade stats)
print("\n=== History (type=1) ===")
try:
    hist = provider.get_history("عیار", history_type=1)
    print(f"Count: {len(hist)}")
    for h in hist[:3]:
        print(f"  {h}")
except Exception as e:
    print(f"History ERROR: {e}")

# Test Candlestick (type=3 for adjusted daily)
print("\n=== Candlestick (type=3) ===")
try:
    candles = provider.get_candlestick("عیار", candlestick_type=3, count=10)
    print(f"Count: {len(candles)}")
    for c in candles[:3]:
        print(f"  {c.get('date')}: O={c.get('open')} H={c.get('high')} L={c.get('low')} C={c.get('close')} V={c.get('volume')}")
except Exception as e:
    print(f"Candlestick ERROR: {e}")

print("\n=== QUOTA REPORT ===")
import json
print(json.dumps(provider.get_quota_report(), ensure_ascii=False, indent=2))