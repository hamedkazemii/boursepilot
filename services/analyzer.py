from core.decision import DecisionEngine
from core.ranking import FundRanking
from core.scoring import BPIScorer, FundMetrics
from services.market_data import MarketDataService
from services.nav import NAVService


class FundAnalyzer:

    def analyze(self, fund_name):

        nav_data = NAVService().get_nav(
            fund_name
        )

        market_data = MarketDataService().get_fund_performance(
            fund_name
        )


        metrics = FundMetrics(
            name=fund_name,
            nav=nav_data["nav"],
            daily_return=market_data["daily_return"],
            weekly_return=market_data["weekly_return"],
            monthly_return=market_data["monthly_return"]
        )


        score = BPIScorer().calculate(
            metrics
        )


        decision = DecisionEngine().decide(
            score
        )


        return FundRanking(
            name=fund_name,
            score=score,
            decision=decision.action
        )
