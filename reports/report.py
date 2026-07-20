from datetime import datetime

from services.nav import NAVService
from services.market_data import MarketDataService

from core.scoring import BPIScorer, FundMetrics
from core.decision import DecisionEngine


class MorningReport:

    def generate(self, fund_name: str) -> str:

        nav_data = NAVService().get_nav(fund_name)

        market_data = MarketDataService().get_fund_performance(
            fund_name
        )

        metrics = FundMetrics(
            name=fund_name,
            nav=nav_data["nav"],
            daily_return=market_data["daily_return"],
            weekly_return=market_data["weekly_return"],
            monthly_return=market_data["monthly_return"],
        )

        scorer = BPIScorer()

        score = scorer.calculate(metrics)

        decision = DecisionEngine().decide(score)

        now = datetime.now().strftime(
            "%Y/%m/%d - %H:%M"
        )

        report = f"""
📊 گزارش صبحگاهی BoursePilot
----------------------------

🏆 صندوق:
{fund_name}

💰 ارزش خالص دارایی (NAV):
{nav_data["nav"]}

📈 بازده روزانه:
{market_data["daily_return"]}٪

📈 بازده هفتگی:
{market_data["weekly_return"]}٪

📈 بازده ماهانه:
{market_data["monthly_return"]}٪

⭐ امتیاز BPI:
{score} از 100

📌 اقدام پیشنهادی:
{decision.action}

🔎 توضیح تحلیل:
{decision.description}

⚠️ سطح اطمینان:
{decision.confidence}

🕘 زمان تولید:
{now}
"""

        return report.strip()
