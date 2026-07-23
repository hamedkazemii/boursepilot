from services.fund_discovery_v2 import FundDiscoveryV2

d=FundDiscoveryV2()


items=d.discover()


print()
print("="*60)
print(
    "TOTAL MARKET ITEMS:",
    len(items)
)


for x in items[:20]:

    print(
        x
    )
