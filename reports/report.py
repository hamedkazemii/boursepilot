from core.scoring import FundScore


class MorningReport:

    def generate(self) -> str:

        fund = FundScore(
            name="دارونو",
            nav_score=90,
            performance_score=85,
            risk_score=80,
        )

        score = fund.calculate_bpi()

        report = f"""
📊 BoursePilot Morning Report
----------------------------

🏆 صندوق:
{fund.name}

⭐ BPI Score:
{score}/100

🟢 System:
READY
"""

        return report.strip()
