import json
from collections import Counter


data=json.load(
open(
"data/fund_ranking.json",
encoding="utf-8"
)
)


print("="*70)
print("گزارش صندوق‌ها")
print("="*70)


print(
"تعداد کل:",
len(data)
)


print()


for k,v in Counter(
x["type"]
for x in data
).items():

    print(
        k,
        ":",
        v
    )


print()
print("="*70)
print("TOP 20")
print("="*70)



for i,x in enumerate(
    data[:20],
    1
):

    print(
        i,
        x["symbol"],
        "|",
        x["type"],
        "| SCORE:",
        x["score"]
    )
