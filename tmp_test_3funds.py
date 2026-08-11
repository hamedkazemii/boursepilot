import sys
sys.path.insert(0, ".")
from services.discovery.universe_store import get_valid_fund, get_valid_fund_symbols

# Test the 3 specific funds
test_funds = ["عیار", "سرو", "توان"]
for symbol in test_funds:
    fund = get_valid_fund(symbol)
    if fund:
        print(f"✓ {symbol}: {fund.name} | ISIN={fund.isin} | Board={fund.board} | cs_id={fund.cs_id}")
    else:
        print(f"✗ {symbol}: NOT FOUND in fund_universe")

# Check all valid fund symbols
symbols = get_valid_fund_symbols()
print(f"\nTotal valid fund symbols: {len(symbols)}")
print("First 10:", symbols[:10])