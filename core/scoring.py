from dataclasses import dataclass


@dataclass
class FundScore:
    name: str
    nav_score: float
    performance_score: float
    risk_score: float

    def calculate_bpi(self) -> int:
        """
        BoursePilot Index
        Range: 0 - 100
        """

        score = (
            self.nav_score * 0.35
            + self.performance_score * 0.45
            + self.risk_score * 0.20
        )

        return round(min(max(score, 0), 100))
