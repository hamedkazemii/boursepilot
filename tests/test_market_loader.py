

from services.tsetmc_market import TSETMCMarket
from core.market_universe import MarketUniverse



market = TSETMCMarket()

storage = MarketUniverse()



print()

print("="*70)

print(
    "📡 شروع دریافت اطلاعات بازار"
)

print("="*70)



symbols = market.get_market_symbols()



print()

print(
    "📌 تعداد کل نمادها:",
    len(symbols)
)



funds = market.filter_funds(
    symbols
)



print()

print(
    "🏦 تعداد صندوق‌های پیدا شده:",
    len(funds)
)



print()

print(
    "نمونه صندوق‌ها:"
)



for fund in funds[:10]:

    print(
        "-",
        fund["name"],
        "|",
        fund["ins_code"]
    )



storage.save(
    funds
)



print()

print(
    "✅ ذخیره شد:"
)

print(
    "data/market_universe.json"
)


