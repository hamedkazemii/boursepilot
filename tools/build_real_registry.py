
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

