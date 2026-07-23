import json
from datetime import datetime

from services.tsetmc_client import TSETMCClient

INPUT = "data/fund_registry.json"
OUTPUT = "data/fund_scores.json"


client = TSETMCClient()


funds = json.load(
    open(INPUT, encoding="utf-8")
)


result = []


for i, fund in enumerate(funds,1):

    print(
        i,
        "/",
        len(funds),
        fund["symbol"]
    )


    try:

        data = client.instrument(
            fund["ins_code"]
        )


        info = data["instrumentInfo"]


        item = {

            "symbol":
                fund["symbol"],

            "name":
                fund["name"],

            "type":
                fund["type"],

            "ins_code":
                fund["ins_code"],


            "nav":
                info.get("nav",0),


            "description":
                info.get("faraDesc",""),


            "sector":
                info.get(
                    "sector",
                    {}
                ).get(
                    "lSecVal",
                    ""
                ),


            "date":
                datetime.now().isoformat()

        }


        result.append(item)


    except Exception as e:

        print(
            "ERROR",
            fund["symbol"],
            e
        )



json.dump(
    result,
    open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ),
    ensure_ascii=False,
    indent=4
)


print()
print("DONE")
print(
    "COUNT:",
    len(result)
)
