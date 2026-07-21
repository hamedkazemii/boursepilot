
import json
from datetime import datetime

from services.brsapi.all_symbols import BRSClient


class LiveScanner:


    def __init__(self):

        self.client = BRSClient()



    def load_registry(self):

        with open(
            "data/fund_registry.json",
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)



    def analyze_fund(self, fund):


        ins_code = fund.get(
            "ins_code"
        )


        if not ins_code:

            return None


        try:

            price = self.client.closing_price(
                ins_code
            )


            book = self.client.orderbook(
                ins_code
            )


            info = self.client.instrument(
                ins_code
            )


            closing = price.get(
                "closingPriceInfo",
                {}
            )


            limits = book.get(
                "bestLimits",
                []
            )


            buy_volume = 0
            sell_volume = 0


            for row in limits:

                buy_volume += row.get(
                    "qTitMeDem",
                    0
                )


                sell_volume += row.get(
                    "qTitMeOf",
                    0
                )



            result = {

                "name":
                    fund.get(
                        "name"
                    ),


                "ins_code":
                    ins_code,


                "price":
                    closing.get(
                        "pClosing",
                        0
                    ),


                "change":
                    closing.get(
                        "priceChange",
                        0
                    ),


                "volume":
                    closing.get(
                        "qTotTran5J",
                        0
                    ),


                "buy_volume":
                    buy_volume,


                "sell_volume":
                    sell_volume,


                "queue_buy":
                    buy_volume > sell_volume,


                "queue_sell":
                    sell_volume > buy_volume,


                "updated_at":
                    datetime.now().isoformat()

            }


            return result



        except Exception as e:


            return {

                "name":
                    fund.get(
                        "name"
                    ),

                "error":
                    str(e)

            }



    def scan(self):


        funds = self.load_registry()


        results=[]


        for fund in funds:


            data = self.analyze_fund(
                fund
            )


            if data:

                results.append(
                    data
                )


        return results



    def save(self, data):


        filename = (
            "data/live/"
            "market_snapshot.json"
        )


        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2
            )


