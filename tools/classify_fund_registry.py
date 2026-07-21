import json

from services.brsapi.all_symbols import BRSClient
from services.fund_classifier import FundClassifier


INPUT = "data/fund_registry.json"


def main():

    client = BRSClient()

    classifier = FundClassifier()


    with open(
        INPUT,
        encoding="utf-8"
    ) as f:

        funds = json.load(f)



    total = len(funds)


    for i, fund in enumerate(funds,1):

        print(
            i,
            "/",
            total,
            fund["symbol"]
        )


        try:

            data = client.instrument(
                fund["ins_code"]
            )


            info = data["instrumentInfo"]


            fund["type"] = classifier.classify(
                info
            )


        except Exception as e:

            print(
                "خطا:",
                fund["symbol"],
                e
            )



    with open(
        INPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            funds,
            f,
            ensure_ascii=False,
            indent=4
        )



    print()
    print("Classification تمام شد")



if __name__ == "__main__":
    main()
