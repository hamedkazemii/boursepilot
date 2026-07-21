
import json
from datetime import datetime

from core.market_score import MarketScore
from core.decision_engine import DecisionEngine
from services.brsapi.all_symbols import BRSClient


REGISTRY="data/fund_registry.json"


def load_registry():

    with open(
        REGISTRY,
        encoding="utf-8"
    ) as f:

        return json.load(f)



def main():

    print()
    print("="*60)
    print("📊 گزارش صبحگاهی Sandoghchi")
    print("="*60)

    print()

    client=BRSClient()

    scorer=MarketScore()

    decision=DecisionEngine()


    funds=load_registry()


    results=[]


    checked=0


    for fund in funds:


        ins=fund.get(
            "insCode"
        )


        name=fund.get(
            "name",
            "نامشخص"
        )


        if not ins:

            continue


        try:


            book=client.orderbook(
                ins
            )


            price=client.closing_price(
                ins
            )


            market={}


            limits=book.get(
                "bestLimits",
                []
            )


            buy_volume=sum(
                x.get("qTitMeDem",0)
                for x in limits
            )


            sell_volume=sum(
                x.get("qTitMeOf",0)
                for x in limits
            )


            market["buy_volume"]=buy_volume
            market["sell_volume"]=sell_volume


            market["queue_buy"]=(
                buy_volume>0 and sell_volume==0
            )


            market["pressure"]=100 if buy_volume>sell_volume else 30


            info=price.get(
                "closingPriceInfo",
                {}
            )


            last=info.get(
                "pClosing",
                0
            )


            yesterday=info.get(
                "priceYesterday",
                last
            )


            if yesterday:

                market["change_percent"]=round(
                    ((last-yesterday)/yesterday)*100,
                    2
                )

            else:

                market["change_percent"]=0



            analysis=scorer.calculate(
                market
            )


            dec=decision.decide(
                analysis["score"]
            )


            results.append({

                "name":name,

                "score":
                    analysis["score"],

                "reasons":
                    analysis["reasons"],

                "risks":
                    analysis["risks"],

                "decision":
                    dec

            })


            checked+=1


        except Exception as e:

            print(
                "خطا در",
                name,
                e
            )


    results.sort(
        key=lambda x:x["score"],
        reverse=True
    )


    print()

    print(
        "تعداد صندوق بررسی شده:",
        checked
    )


    print()

    for i,item in enumerate(results[:10],1):

        print("-"*50)

        print(
            f"رتبه {i}: {item['name']}"
        )

        print(
            "امتیاز BPI:",
            item["score"],
            "از 100"
        )


        print(
            "وضعیت:",
            item["decision"]["status"]
        )


        print(
            "تصمیم:",
            item["decision"]["action"]
        )


        print(
            "دلایل:"
        )

        for r in item["reasons"]:

            print(
                " ✓",
                r
            )


        if item["risks"]:

            print(
                "هشدار:"
            )

            for r in item["risks"]:

                print(
                    " ⚠",
                    r
                )



    print()

    print(
        "زمان تولید گزارش:",
        datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )
    )


    with open(
        "data/reports/latest_ranking.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            results,
            f,
            ensure_ascii=False,
            indent=2
        )



if __name__=="__main__":

    main()

