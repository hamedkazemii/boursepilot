from services.fund_classifier import FundClassifier
from services.tsetmc_client import TSETMCClient

client = TSETMCClient()

classifier = FundClassifier()


codes = {

"دارونو":"34074071043606558",

"عیار":"PUT_REAL_CODE_HERE"

}


for name,code in codes.items():

    print("="*60)

    try:

        data = client.instrument(code)

        info = data["instrumentInfo"]

        print(
            name
        )

        print(
            "نماد:",
            info.get("lVal18AFC")
        )


        print(
            "نوع:",
            classifier.classify(info)
        )


    except Exception as e:

        print(
            "ERROR",
            e
        )
