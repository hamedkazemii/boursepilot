from services.advisor.portfolio_advisor import (
    PortfolioAdvisor,
    InvestorProfile
)

from services.providers.factory import get_market_data_provider
from core.pipeline.daily_analysis import DailyAnalysisPipeline


provider = get_market_data_provider()

pipeline = DailyAnalysisPipeline(
    provider=provider,
    allow_offline_seed=False
)

result = pipeline.run()


advisor = PortfolioAdvisor(
    result["ranked"]
)


portfolio = advisor.build(
    InvestorProfile(
        capital=500_000_000,
        risk="medium",
        horizon="6m"
    )
)


print("="*50)
print("SMART PORTFOLIO v1.4.1")
print("="*50)

print("\nAllocation:")

for k,v in portfolio["allocation"].items():
    print(k, v, "%")


print("\nSelected Funds:")

for x in portfolio["funds"]:
    print(
        x["symbol"],
        "|",
        x["type"],
        "| score:",
        x["score"],
        "| weight:",
        x["weight"],
        "%"
    )
