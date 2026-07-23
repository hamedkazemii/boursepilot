from core.market_analyzer import MarketAnalyzer
from core.market_engine import MarketEngine
from services.tsetmc_client import TSETMCClient

client = TSETMCClient()

engine = MarketEngine()

analyzer = MarketAnalyzer()

DARONO = "34074071043606558"

book = client.orderbook(DARONO)

price = client.closing_price(DARONO)

market = engine.analyze(
    book,
    price
)

report = analyzer.analyze(
    market
)

print()

print("=" * 60)

print("📊 تحلیل هوشمند بازار")

print("=" * 60)

print()

print("قدرت تقاضا :", report["demand"])

print("قدرت عرضه :", report["supply"])

print("وضعیت صف :", report["queue"])

print("روند :", report["trend"])

print()

print("جمع‌بندی")

print(report["summary"])

print()
