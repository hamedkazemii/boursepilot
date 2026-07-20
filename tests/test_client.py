from services.tsetmc_client import TSETMCClient


DARONO = "34074071043606558"

client = TSETMCClient()


print("=" * 60)
print("اطلاعات نماد")
print("=" * 60)

info = client.instrument(DARONO)

print(
    info["instrumentInfo"]["lVal18AFC"]
)

print(
    info["instrumentInfo"]["faraDesc"]
)


print()

print("=" * 60)
print("قیمت")
print("=" * 60)

price = client.closing_price(DARONO)

cp = price["closingPriceInfo"]

print("آخرین قیمت:", cp["pClosing"])
print("دیروز:", cp["priceYesterday"])
print("حجم:", cp["qTotTran5J"])


print()

print("=" * 60)
print("بهترین سفارش")
print("=" * 60)

book = client.orderbook(DARONO)

for row in book["bestLimits"]:

    print(row)


print()

print("=" * 60)
print("آخرین معاملات")
print("=" * 60)

trades = client.trades(DARONO)

for trade in trades["trade"][:10]:

    print(
        trade["hEven"],
        trade["pTran"],
        trade["qTitTran"]
    )
