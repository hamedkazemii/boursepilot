#!/bin/bash

set -e

echo "=========================================="
echo " BoursePilot Release 0.5 Migration"
echo "=========================================="

mkdir -p core
mkdir -p services
mkdir -p reports
mkdir -p data

echo "Creating Fund Registry..."

cat > services/fund_registry.py <<'PY'
import json
import os


class FundRegistry:

    FILE = "data/funds.json"


    def load(self):

        if not os.path.exists(self.FILE):
            return []

        with open(
            self.FILE,
            encoding="utf-8"
        ) as f:

            return json.load(f)


    def save(self, funds):

        with open(
            self.FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                funds,
                f,
                ensure_ascii=False,
                indent=4
            )
PY


echo "Creating classifier..."

cat > services/fund_classifier.py <<'PY'
from services.tsetmc_client import TSETMCClient


class FundClassifier:


    def __init__(self):

        self.client = TSETMCClient()


    def classify(self, fund):

        try:

            data = self.client.instrument(
                fund["ins_code"]
            )

            info = data["instrumentInfo"]


            desc = (
                info.get("faraDesc")
                or ""
            )


            group = (
                info.get("cgrValCotTitle")
                or ""
            )


            if "اهرمی" in desc:
                return "اهرمی"


            if "ثابت" in desc:
                return "درآمد ثابت"


            if "طلا" in fund["name"]:
                return "طلا"


            if "صندوق" in group:
                return "سهامی"


        except Exception:

            pass


        return "UNKNOWN"
PY


echo "Creating recommendation engine..."

cat > core/recommendation.py <<'PY'
from dataclasses import dataclass



@dataclass
class Recommendation:

    symbol:str
    name:str
    score:int
    decision:str



class RecommendationEngine:


    def evaluate(
        self,
        fund,
        market,
        analysis
    ):


        score = 50


        text = str(
            analysis
        )


        if "قوی" in text:
            score += 20


        if "صف خرید" in text:
            score += 15


        if "فروش" in text:
            score -= 15



        score = max(
            0,
            min(
                score,
                100
            )
        )


        if score >= 80:

            decision="BUY"

        elif score >=60:

            decision="HOLD"

        else:

            decision="AVOID"



        return Recommendation(

            symbol=fund["symbol"],

            name=fund["name"],

            score=score,

            decision=decision

        )
PY


echo "Creating market scanner..."

cat > core/real_market_scanner.py <<'PY'
from services.tsetmc_client import TSETMCClient
from services.fund_registry import FundRegistry
from services.fund_classifier import FundClassifier
from core.market_engine import MarketEngine
from core.market_analyzer import MarketAnalyzer
from core.recommendation import RecommendationEngine



class RealMarketScanner:


    def __init__(self):

        self.client=TSETMCClient()

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
PY


echo "Creating report generator..."

cat > reports/recommendation_report.py <<'PY'
import json
import os


def save_report(data):

    os.makedirs(
        "reports",
        exist_ok=True
    )


    with open(
        "reports/recommendations.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )



    with open(
        "reports/recommendations.txt",
        "w",
        encoding="utf-8"
    ) as f:


        for x in data[:20]:

            f.write(
                f'{x["symbol"]} | '
                f'{x["type"]} | '
                f'{x["score"]} | '
                f'{x["decision"]}\n'
            )
PY


echo "Creating runner..."

cat > app.py <<'PY'
from core.real_market_scanner import RealMarketScanner
from reports.recommendation_report import save_report



print("="*60)
print("BoursePilot Real Market Scan")
print("="*60)


scanner=RealMarketScanner()


results=scanner.scan()


print()
print("="*60)
print("TOP RECOMMENDATIONS")
print("="*60)


for r in results[:20]:

    print(
        r["symbol"],
        "|",
        r["type"],
        "|",
        r["score"],
        "|",
        r["decision"]
    )


save_report(results)


print()
print("Saved:")
print("reports/recommendations.json")
print("reports/recommendations.txt")
PY



echo ""
echo "=========================================="
echo "Migration Finished"
echo "=========================================="

