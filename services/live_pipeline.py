
from services.fund_repository import FundRepository
from services.brsapi.all_symbols import BRSClient
from core.market_engine import MarketEngine


class LivePipeline:


    def __init__(self):

        self.repo=FundRepository()
        self.client=BRSClient()
        self.engine=MarketEngine()



    def run(self):

        funds=self.repo.load()

        results=[]


        for fund in funds:

            if not fund.get("active",True):
                continue


            ins=fund.get("ins_code")

            if not ins:
                continue


            try:

                book=self.client.orderbook(ins)

                price=self.client.closing_price(ins)


                analysis=self.engine.analyze(
                    book,
                    price
                )


                results.append(
                    {
                    "symbol":fund["symbol"],
                    "name":fund["name"],
                    "analysis":analysis
                    }
                )


            except Exception as e:

                print(
                    "ERROR",
                    fund.get("symbol"),
                    e
                )


        return results
