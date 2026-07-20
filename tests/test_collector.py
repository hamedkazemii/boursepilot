from services.providers.fund_provider import FundProvider
from services.collectors.fund_collector import FundCollector


provider = FundProvider()

collector = FundCollector(
    provider
)


result = collector.collect(
    "دارونو"
)


print(result)
