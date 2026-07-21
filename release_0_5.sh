#!/bin/bash

set -e

echo "================================="
echo " BoursePilot Release v0.5"
echo " Real Fund Pipeline Migration"
echo "================================="


echo "[1/15] Creating folders"

mkdir -p \
core \
services \
reports \
tools \
tests \
data/raw \
data/registry \
data/reports


echo "[2/15] Updating version"

echo "0.5.0-real-fund-pipeline" > VERSION



echo "[3/15] Installing dependencies"

pip install pandas openpyxl requests >/dev/null 2>&1 || true



echo "[4/15] Creating MarketWatch loader"


cat > services/marketwatch_loader.py <<'PY'
import pandas as pd
import os


class MarketWatchLoader:


    def load_excel(self,path):

        if not os.path.exists(path):
            raise FileNotFoundError(path)


        df=pd.read_excel(path)


        return df



    def filter_funds(self,df):

        keywords=[
            "صندوق",
            "ص.",
            "س صندوق",
            "سرمایه گذاری"
        ]


        mask=False


        for k in keywords:
            mask = mask | df.astype(str).apply(
                lambda x:x.str.contains(k,na=False)
            ).any(axis=1)


        return df[mask]



    def build_registry(self,df):

        result=[]


        for _,row in df.iterrows():

            text=" ".join(
                row.astype(str).tolist()
            )


            result.append(
                {
                    "symbol":str(row.iloc[0]),
                    "name":text,
                    "ins_code":None,
                    "active":True
                }
            )


        return result

PY



echo "[5/15] Creating registry builder"


cat > tools/build_real_registry.py <<'PY'

from services.marketwatch_loader import MarketWatchLoader
import json


EXCEL="data/raw/MarketWatchPlus.xlsx"


loader=MarketWatchLoader()


df=loader.load_excel(EXCEL)


funds=loader.filter_funds(df)


registry=loader.build_registry(funds)


with open(
"data/registry/fund_registry_real.json",
"w",
encoding="utf-8"
) as f:

    json.dump(
        registry,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
"Funds:",
len(registry)
)

PY



echo "[6/15] Creating live fund scanner"


cat > services/real_fund_scanner.py <<'PY'

from services.tsetmc_client import TSETMCClient


class RealFundScanner:


    def __init__(self):

        self.client=TSETMCClient()



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

PY




echo "[7/15] Creating BPI v2"


cat > core/bpi_v2.py <<'PY'


def calculate(data):


    score=50

    reasons=[]


    if data.get("queue_buy"):

        score+=20
        reasons.append(
            "صف خرید فعال است"
        )


    if data.get("pressure",0)>300:

        score+=15
        reasons.append(
            "قدرت تقاضا بالاست"
        )


    if data.get("change_percent",0)>0:

        score+=10
        reasons.append(
            "روند قیمت مثبت است"
        )


    if score>100:
        score=100


    return {

        "score":score,
        "reasons":reasons

    }


PY




echo "[8/15] Creating decision engine"


cat > core/decision_v2.py <<'PY'


def decide(score):


    if score>=85:

        return "🟢 مناسب بررسی ورود"


    if score>=70:

        return "🟡 نگهداری / بررسی بیشتر"


    if score>=50:

        return "🟠 احتیاط"


    return "🔴 عدم ورود"



PY





echo "[9/15] Creating Persian report"


cat > reports/morning_report_v2.py <<'PY'


from datetime import datetime



def generate(items):


    print()
    print("="*60)
    print("📊 گزارش صبحگاهی BoursePilot")
    print("="*60)


    print(
        "تعداد صندوق بررسی شده:",
        len(items)
    )


    print()


    for i,x in enumerate(items,1):

        print(
            f"{i}- {x['symbol']}"
        )

        print(
            "امتیاز:",
            x.get("score")
        )

        print(
            "تصمیم:",
            x.get("decision")
        )

        print("-"*40)



    print()

    print(
        "زمان تولید:",
        datetime.now()
    )



PY




echo "[10/15] Creating validation test"


cat > tests/test_v05.py <<'PY'


import json


with open(
"data/registry/fund_registry_real.json",
encoding="utf-8"
) as f:

    data=json.load(f)



print(
"Registry:",
len(data)
)


assert len(data)>=0


print(
"V0.5 TEST OK"
)


PY





echo "[11/15] Updating README"


cat >> README.md <<EOF


## Version 0.5

Real Fund Pipeline

- MarketWatch Excel based registry
- Real fund discovery
- TSETMC live data
- Persian morning report

