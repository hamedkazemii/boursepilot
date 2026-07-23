
from services.fund_loader import FundLoader
from services.tsetmc_client import TSETMCClient


class FundValidator:


    def __init__(self):

        self.loader = FundLoader()

        self.client = TSETMCClient()



    def validate(self):


        funds = self.loader.load()


        valid = []


        print()

        print("="*60)

        print(
            "🔍 بررسی اعتبار صندوق‌ها"
        )

        print("="*60)



        for fund in funds:


            try:


                price = self.client.closing_price(

                    fund["ins_code"]

                )


                if price:


                    print(

                        "✅",

                        fund["name"]

                    )


                    valid.append(
                        fund
                    )



            except Exception:


                print(

                    "❌",

                    fund["name"],

                    "نامعتبر"

                )



        print()

        print(
            "صندوق معتبر:",
            len(valid)
        )


        return valid



if __name__ == "__main__":


    validator = FundValidator()


    validator.validate()

