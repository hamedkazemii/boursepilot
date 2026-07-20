
from services.providers.fund_provider import FundProvider


provider = FundProvider()


print()
print("="*70)
print("📡 تست دریافت لیست صندوق‌ها")
print("="*70)


funds = provider.get_funds()


print()

print(
    "تعداد صندوق‌ها:",
    len(funds)
)


print()

for fund in funds[:10]:

    print(
        fund
    )


