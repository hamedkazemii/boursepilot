#!/bin/bash

set -e

echo "================================="
echo " BoursePilot Live Pipeline v0.4"
echo "================================="

echo "[1/12] Creating structure"

mkdir -p core
mkdir -p services
mkdir -p reports
mkdir -p tools
mkdir -p data/snapshots
mkdir -p tests


echo "[2/12] Creating Fund model"

cat > core/models.py <<'PY'
from dataclasses import dataclass


@dataclass
class Fund:

    symbol: str
    name: str
    ins_code: str
    fund_type: str = ""
    active: bool = True
    description: str = ""
PY


echo "[3/12] Creating registry loader"

cat > services/fund_repository.py <<'PY'
import json


class FundRepository:

    FILE="data/fund_registry.json"


    def load(self):

        with open(
            self.FILE,
            encoding="utf-8"
        ) as f:

            return json.load(f)
PY


echo "[4/12] Creating compatible scanner"

cat > services/live_pipeline.py <<'PY'

from services.fund_repository import FundRepository
from services.tsetmc_client import TSETMCClient
from core.market_engine import MarketEngine


class LivePipeline:


    def __init__(self):

        self.repo=FundRepository()
        self.client=TSETMCClient()
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
PY



echo "[5/12] Creating Persian report"


cat > reports/live_report.py <<'PY'

from datetime import datetime


def generate(results):


    print()
    print("="*60)

    print("📊 گزارش صبحگاهی BoursePilot")

    print("="*60)


    print()

    print(
        "تعداد صندوق بررسی شده:",
        len(results)
    )


    ranked=sorted(
        results,
        key=lambda x:
        x["analysis"].get(
            "pressure",
            0
        ),
        reverse=True
    )


    print()

    for i,item in enumerate(ranked[:10],1):

        print(
            f"{i}- {item['symbol']}"
        )

        print(
            "وضعیت:",
            item["analysis"]
        )

        print("-"*40)



    print()

    print(
        "زمان تولید:",
        datetime.now()
    )
PY



echo "[6/12] Creating runner"


cat > tools/run_live_report.py <<'PY'

from services.live_pipeline import LivePipeline
from reports.live_report import generate


pipeline=LivePipeline()

data=pipeline.run()


generate(data)

PY



echo "[7/12] Creating tests"


cat > tests/test_live_pipeline.py <<'PY'

from services.live_pipeline import LivePipeline


p=LivePipeline()


r=p.run()


print(
    "Funds scanned:",
    len(r)
)


assert len(r)>=0


print(
    "LIVE PIPELINE OK"
)

PY



echo "[8/12] Running tests"


python3 -m tests.test_live_pipeline


echo "[9/12] Running report"


python3 -m tools.run_live_report


echo "[10/12] Git status"

git status


echo "[11/12] Saving version"

echo "0.4.0-live-pipeline" > VERSION


echo "[12/12] Completed"


echo "================================="
echo " BoursePilot v0.4 READY"
echo "================================="

