
from core.indicators import Indicators


class BPIEngine:


    def __init__(self):

        self.indicators = Indicators()



    def calculate(self, market):


        score = 0


        demand = self.indicators.demand_ratio(
            market
        )


        if demand >= 5:

            score += 30

        elif demand >= 2:

            score += 20

        else:

            score += 10



        score += (
            self.indicators.queue_score(
                market
            ) * 0.3
        )



        score += (
            self.indicators.trend_score(
                market.get(
                    "change_percent",
                    0
                )
            ) * 0.3
        )


        return min(
            int(score),
            100
        )

