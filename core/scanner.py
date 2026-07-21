
from services.brsapi.all_symbols import BRSClient
from services.fund_loader import FundLoader

from core.market_engine import MarketEngine
from core.market_analyzer import MarketAnalyzer



class MarketScanner:



    def __init__(self):

        self.client = BRSClient()

        self.loader = FundLoader()

        self.engine = MarketEngine()

        self.analyzer = MarketAnalyzer()



    def scan(self):


        funds = self.loader.load()


        results = []



        print()

        print(
            "📡 شروع اسکن صندوق‌ها"
        )

        print(
            "-" * 50
        )



        for fund in funds:


            try:


                print(
                    "بررسی:",
                    fund["name"]
                )



                book = self.client.orderbook(

                    fund["ins_code"]

                )


                price = self.client.closing_price(

                    fund["ins_code"]

                )



                market = self.engine.analyze(

                    book,

                    price

                )



                analysis = self.analyzer.analyze(

                    market

                )



                results.append({

                    "name":
                    fund["name"],


                    "type":
                    fund["type"],


                    "market":
                    market,


                    "analysis":
                    analysis

                })



            except Exception as e:


                print(

                    "❌ خطا در",

                    fund["name"],

                    ":",

                    e

                )



        return results

