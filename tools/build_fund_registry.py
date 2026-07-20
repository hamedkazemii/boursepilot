from services.fund_registry import FundRegistry


registry = FundRegistry()


keywords = [

    "صندوق",

    "طلا",

    "ثابت",

    "دارا",

    "کمند",

    "افران",

    "عیار",

    "اهرم"

]


funds = registry.discover(
    keywords
)


print()

print("="*70)

print(
    "تعداد صندوق‌های پیدا شده:",
    len(funds)
)


print()

for f in funds:

    print(
        f["name"],
        "-",
        f["type"]
    )


registry.save(
    funds
)


print()

print("✅ ذخیره شد:")
print("data/funds.json")
