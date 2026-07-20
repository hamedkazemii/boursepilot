from dataclasses import dataclass


@dataclass
class FundRanking:
    name: str
    score: int
    decision: str


class RankingEngine:

    def rank(self, funds):

        return sorted(
            funds,
            key=lambda x: x.score,
            reverse=True
        )


    def get_summary(self, ranked):

        if not ranked:
            return None

        return {
            "best": ranked[0],
            "weakest": ranked[-1]
        }
