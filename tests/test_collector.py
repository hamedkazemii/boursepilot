from services.collectors.fund_collector import FundCollector
from services.providers.fund_provider import FundProvider

provider = FundProvider()

collector = FundCollector(
    provider
)


result = collector.collect(
    "دارونو"
)


print(result)
