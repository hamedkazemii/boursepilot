
class Indicators:


    def demand_ratio(self, market):

        buy = market.get(
            "buy_volume",
            0
        )

        sell = market.get(
            "sell_volume",
            0
        )


        if sell == 0:

            return 100


        return round(
            buy / sell,
            2
        )



    def queue_score(self, market):

        if market.get(
            "queue_buy"
        ):

            return 100


        if market.get(
            "queue_sell"
        ):

            return 0


        return 50



    def trend_score(self, change):

        if change >= 3:

            return 100


        if change >= 0:

            return 70


        return 30

