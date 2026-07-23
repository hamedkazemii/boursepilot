from core.market_engine import MarketEngine
from services.tsetmc_client import TSETMCClient

client = TSETMCClient()

engine = MarketEngine()

DARONO = "34074071043606558"

book = client.orderbook(DARONO)

price = client.closing_price(DARONO)

result = engine.analyze(
    book,
    price
)

print()

print("="*60)

print("تحلیل بازار")

print("="*60)

for k,v in result.items():

    print(k,":",v)
