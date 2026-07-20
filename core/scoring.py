from dataclasses import dataclass


@dataclass
class FundMetrics:
    name: str
    nav: int
    daily_return: float
    weekly_return: float
    monthly_return: float


class BPIScorer:

    def calculate_performance_score(
        self,
        daily: float,
        weekly: float,
        monthly: float
    ) -> float:

        score = (
            daily * 5
            + weekly * 3
            + monthly * 2
        )

        return min(max(score, 0), 100)


    def calculate_nav_score(self, nav: int) -> float:
        """
        Temporary NAV scoring.
        Later replaced by historical NAV analysis.
        """

        if nav > 120000:
            return 90

        if nav > 100000:
            return 75

        return 60


    def calculate_risk_score(
        self,
        monthly_return: float
    ) -> float:

        if monthly_return > 10:
            return 90

        if monthly_return > 5:
            return 80

        return 65


    def calculate(self, metrics: FundMetrics) -> int:

        nav_score = self.calculate_nav_score(metrics.nav)

        performance_score = self.calculate_performance_score(
            metrics.daily_return,
            metrics.weekly_return,
            metrics.monthly_return
        )

        risk_score = self.calculate_risk_score(
            metrics.monthly_return
        )

        final_score = (
            nav_score * 0.35
            + performance_score * 0.45
            + risk_score * 0.20
        )

        return round(final_score)
