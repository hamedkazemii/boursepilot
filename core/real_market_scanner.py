from services.brsapi.all_symbols import BRSClient
from services.fund_registry import FundRegistry
from services.fund_classifier import FundClassifier
from core.market_engine import MarketEngine
from core.market_analyzer import MarketAnalyzer
from core.recommendation import RecommendationEngine



class RealMarketScanner:


    def __init__(self):

        self.client=BRSClient()

        self.registry=FundRegistry()

        self.classifier=FundClassifier()

        self.engine=MarketEngine()

        self.analyzer=MarketAnalyzer()

        self.recommender=RecommendationEngine()



    def scan(self):


        funds=self.registry.load()

        output=[]


        for fund in funds:


            try:

                print(
                    "Scanning:",
                    fund["symbol"]
                )


                category=self.classifier.classify(
                    fund
                )


                price=self.client.closing_price(
                    fund["ins_code"]
                )


                book=self.client.orderbook(
                    fund["ins_code"]
                )


                market=self.engine.analyze(
                    book,
                    price
                )


                analysis=self.analyzer.analyze(
                    market
                )


                rec=self.recommender.evaluate(
                    fund,
                    market,
                    analysis
                )


                output.append({

                    "symbol":rec.symbol,

                    "name":rec.name,

                    "type":category,

                    "score":rec.score,

                    "decision":rec.decision

                })


            except Exception as e:

                print(
                    "ERROR",
                    fund.get("symbol"),
                    e
                )


        return sorted(
            output,
            key=lambda x:x["score"],
            reverse=True
        )
