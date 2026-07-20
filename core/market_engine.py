class MarketEngine:

    def analyze(self, orderbook, closing_price):

        rows = orderbook["bestLimits"]

        buy_volume = sum(x["qTitMeDem"] for x in rows)
        sell_volume = sum(x["qTitMeOf"] for x in rows)

        buy_orders = sum(x["zOrdMeDem"] for x in rows)
        sell_orders = sum(x["zOrdMeOf"] for x in rows)

        last_price = closing_price["closingPriceInfo"]["pClosing"]
        yesterday = closing_price["closingPriceInfo"]["priceYesterday"]

        change_percent = (
            (last_price - yesterday)
            / yesterday
        ) * 100

        imbalance = buy_volume - sell_volume

        if sell_volume == 0:
            pressure = 100
        else:
            pressure = round(
                buy_volume / sell_volume,
                2
            )

        return {

            "buy_volume": buy_volume,

            "sell_volume": sell_volume,

            "buy_orders": buy_orders,

            "sell_orders": sell_orders,

            "change_percent": round(change_percent,2),

            "pressure": pressure,

            "imbalance": imbalance,

            "queue_buy": sell_volume == 0,

            "queue_sell": buy_volume == 0

        }
