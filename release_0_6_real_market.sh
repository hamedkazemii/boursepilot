#!/bin/bash

set -e

echo "================================="
echo " BoursePilot v0.6 Real Market"
echo "================================="


mkdir -p data/raw
mkdir -p data/registry
mkdir -p data/reports
mkdir -p services/data_provider


echo "[1] Installing excel dependencies"

pip install pandas openpyxl requests -q


echo "[2] Creating MarketWatch downloader"


cat > services/data_provider/marketwatch_excel.py <<'PY'

import requests
from pathlib import Path


URL="https://old.tsetmc.com/tsev2/excel/MarketWatchPlus.aspx?d=0&format=0"


def download():

    path=Path("data/raw/marketwatch.xlsx")

    r=requests.get(
        URL,
        headers={
            "User-Agent":
            "Mozilla/5.0"
        },
        timeout=20
    )

    path.write_bytes(r.content)

    return path


if __name__=="__main__":
    print(download())

PY



echo "[3] Creating fund registry builder"


cat > tools/build_real_registry.py <<'PY'

import pandas as pd
import json
from pathlib import Path


KEYWORDS=[
"صندوق",
"ص.",
"صن",
"سرمایه گذاری",
"سرمایه‌گذاری"
]


src="data/raw/marketwatch.xlsx"

df=pd.read_excel(src)


funds=[]


for _,r in df.iterrows():

    text=" ".join(
        str(x)
        for x in r.values
    )

    if any(k in text for k in KEYWORDS):

        item={

        "symbol":
        str(r.iloc[0]),

        "name":
        text,

        "active":
        True

        }

        funds.append(item)



Path(
"data/registry"
).mkdir(
exist_ok=True
)


with open(
"data/registry/fund_registry_real.json",
"w",
encoding="utf8"
) as f:

    json.dump(
        funds,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
"FUNDS:",
len(funds)
)

PY



echo "[4] Download marketwatch"


python3 -m services.data_provider.marketwatch_excel


echo "[5] Build registry"


python3 tools.build_real_registry.py


echo "[6] Validate"


python3 - <<'PY'

import json

x=json.load(
open(
"data/registry/fund_registry_real.json",
encoding="utf8"
)
)

print(
"Registry:",
len(x)
)

assert len(x)>100

print("REAL REGISTRY OK")

PY


echo "[7] Git"


git add .


git commit -m \
"BoursePilot v0.6 real marketwatch fund registry pipeline" || true



echo "================================="
echo " v0.6 READY"
echo "================================="

