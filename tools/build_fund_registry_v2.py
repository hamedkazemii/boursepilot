import json
from services.fund_discovery import FundDiscovery


OUTPUT = "data/fund_registry.json"


def main():

    print("=" * 70)
    print("ساخت Fund Registry")
    print("=" * 70)


    discovery = FundDiscovery()


    funds = discovery.discover()


    cleaned = []


    for f in funds:

        cleaned.append({

            "symbol": f["symbol"],

            "name": f["name"],

            "ins_code": f["ins_code"],

            "type": "UNKNOWN",

            "active": True

        })


    with open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cleaned,
            file,
            ensure_ascii=False,
            indent=4
        )


    print()
    print("تعداد ثبت شده:", len(cleaned))
    print()
    print("ذخیره شد:")
    print(OUTPUT)



if __name__ == "__main__":
    main()
