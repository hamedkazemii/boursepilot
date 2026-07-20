from services.fund_discovery import FundDiscovery

fd = FundDiscovery()

items = fd.discover()

print()

print("=" * 60)

print("تعداد:", len(items))

print("=" * 60)

for item in items[:30]:

    print(
        item["symbol"],
        "|",
        item["name"],
        "|",
        item["ins_code"]
    )
