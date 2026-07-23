from core.decision import DecisionEngine
from core.scoring import BPIScorer, FundMetrics
from services.market_data import MarketDataService
from services.nav import NAVService

fund = "دارونو"

nav = NAVService().get_nav(fund)
performance = MarketDataService().get_fund_performance(fund)


metrics = FundMetrics(
    name=fund,
    nav=nav["nav"],
    daily_return=performance["daily_return"],
    weekly_return=performance["weekly_return"],
    monthly_return=performance["monthly_return"],
)


score = BPIScorer().calculate(metrics)

decision = DecisionEngine().decide(score)


print("📊 BoursePilot")
print("----------------")
print(f"Fund: {fund}")
print(f"BPI: {score}/100")
print(f"Decision: {decision}")
