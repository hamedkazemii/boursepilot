from services.analysis.fund_deepdive import get_fund_deepdive

for symbol in ["عیار", "سرو", "توان"]:
    print(f"\n{'='*60}")
    print(f"DEEP DIVE: {symbol}")
    print(f"{'='*60}")
    result = get_fund_deepdive(symbol)
    print(result)