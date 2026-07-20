import json


FILE="data/fund_registry.json"


with open(
    FILE,
    encoding="utf-8"
) as f:

    data=json.load(f)


for f in data:

    if f["type"]=="UNKNOWN":

        print("="*70)
        print("نماد:",f["symbol"])
        print("نام:",f["name"])
        print("کد:",f["ins_code"])
