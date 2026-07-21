
from services.brsapi.all_symbols import BRSClient


class RealFundScanner:


    def __init__(self):

        self.client=BRSClient()



    def scan(self,fund):

        code=fund.get("ins_code")


        if not code:
            return None


        price=self.client.closing_price(code)

        book=self.client.orderbook(code)


        return {

            "symbol":fund["symbol"],
            "price":price,
            "orderbook":book

        }

