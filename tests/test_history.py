from services.providers.fund_provider import FundProvider
from services.collectors.fund_collector import FundCollector
from services.storage import StorageService


provider = FundProvider()

storage = StorageService()


collector = FundCollector(
    provider,
    storage
)


result = collector.collect(
    "دارونو"
)


print("Saved:")
print(result)
