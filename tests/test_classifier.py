from services.fund_classifier import FundClassifier
from services.tsetmc_client import TSETMCClient

client = TSETMCClient()

classifier = FundClassifier()



funds = {


    "دارونو":
    "34074071043606558",


    "عیار":
    "19040514831923530",


    "اهرم":
    "123456789"

}



for name, code in funds.items():


    print("="*60)

    print(name)


    try:

        info = client.instrument(
            code
        )


        result = classifier.classify(
            info
        )


        print(
            "نوع:",
            result
        )


    except Exception as e:

        print(
            "خطا:",
            e
        )

