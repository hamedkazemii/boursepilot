import sys
sys.path.insert(0, ".")
from services.providers.brs_provider import BrsProvider

provider = BrsProvider()

test_funds = ["عیار", "سرو", "توان"]
for symbol in test_funds:
    print(f"\n=== {symbol} ===")
    # Test Symbol
    try:
        quote = provider.get_symbol(symbol)
        print(f"Symbol: {quote.symbol} | Last={quote.last_price} | Close={quote.close_price} | Yesterday={quote.yesterday_price}")
    except Exception as e:
        print(f"Symbol ERROR: {e}")
    
    # Test NAV
    try:
        nav = provider.get_nav(symbol)
        print(f"NAV: issue={nav.nav_issue} | redeem={nav.nav_redeem} | date={nav.date}")
        if nav.nav_redeem and quote.last_price:
            bubble = ((quote.last_price - nav.nav_redeem) / nav.nav_redeem) * 100
            print(f"BUBBLE: {bubble:.2f}%")
    except Exception as e:
        print(f"NAV ERROR: {e}")
    
    # Test Candlestick (type=3, 10 days)
    try:
        candles = provider.get_candlestick(symbol, candlestick_type=3, count=10)
        print(f"Candlestick: {len(candles)} days")
        for c in candles[:3]:
            print(f"  {c.get('date')}: O={c.get('open')} H={c.get('high')} L={c.get('low')} C={c.get('close')} V={c.get('volume')}")
    except Exception as e:
        print(f"Candlestick ERROR: {e}")

print("\n=== API QUOTA REPORT ===")
import json
print(json.dumps(provider.get_quota_report(), ensure_ascii=False, indent=2))