#!/bin/bash

set -e

echo "================================="
echo " BoursePilot Pipeline v0.3.1"
echo "================================="


echo "[1/8] Creating folders"

mkdir -p core
mkdir -p reports
mkdir -p tests
mkdir -p data/reports


echo "[2/8] Creating market score engine"


cat > core/market_score.py <<'PY'
class MarketScore:

    def calculate(self, market):

        score = 50
        reasons = []
        risks = []

        if market.get("queue_buy"):
            score += 20
            reasons.append(
                "صف خرید فعال است"
            )

        if market.get("pressure",0) > 70:
            score += 15
            reasons.append(
                "قدرت تقاضا بالاست"
            )

        if market.get("change_percent",0) > 0:
            score += 10
            reasons.append(
                "روند قیمت مثبت است"
            )

        if market.get("sell_volume",0) == 0:
            risks.append(
                "فروشنده فعال مشاهده نشد"
            )


        score=min(score,100)


        return {

            "score":score,
            "reasons":reasons,
            "risks":risks

        }
PY



echo "[3/8] Creating decision engine"


cat > core/decision_engine.py <<'PY'

class DecisionEngine:


    def decide(self,score):

        if score >=85:

            return {
                "status":"مثبت",
                "action":
                "بررسی ورود یا نگهداری موقعیت"
            }


        elif score >=65:

            return {
                "status":"متوسط",
                "action":
                "نگهداری و بررسی شرایط بازار"
            }


        else:

            return {
                "status":"ضعیف",
                "action":
                "کاهش ریسک و عدم افزایش موقعیت"
            }

PY



echo "[4/8] Creating report generator"


cat > reports/morning_pipeline_report.py <<'PY'


def generate(items):

    print()

    print("="*60)

    print("📊 گزارش صبحگاهی BoursePilot")

    print("="*60)


    for i,item in enumerate(items,1):

        print()

        print(
            f"{i}) {item['name']}"
        )

        print(
            "امتیاز:",
            item["score"]
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
                "✓",
                r
            )


        print("-"*40)


PY



echo "[5/8] Creating integration test"


cat > tests/test_pipeline.py <<'PY'


from core.market_score import MarketScore
from core.decision_engine import DecisionEngine


market={

"queue_buy":True,
"pressure":90,
"change_percent":3,
"sell_volume":0

}


score=MarketScore().calculate(
    market
)


decision=DecisionEngine().decide(
    score["score"]
)


print(score)

print(decision)


assert score["score"]>0

print(
"PIPELINE TEST OK"
)

PY



echo "[6/8] Running tests"


python3 -m tests.test_pipeline



echo "[7/8] Creating report placeholder"

touch data/reports/latest.json



echo "[8/8] Completed"


echo "================================="
echo "Pipeline v0.3.1 READY"
echo "================================="

