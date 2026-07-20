
import requests


class TSETMCMarket:


    def __init__(self):

        self.url = (
            "https://www.tsetmc.com/Loader.aspx"
        )



    def get_market_symbols(self):

        """
        دریافت لیست نمادها
        """

        symbols = []


        try:

            params = {

                "ParTree": "15131M"

            }


            response = requests.get(

                self.url,

                params=params,

                headers={

                    "User-Agent":
                    "Mozilla/5.0"

                },

                timeout=30

            )


            response.raise_for_status()


            text = response.text



            # بررسی اولیه پاسخ

            if len(text) < 100:

                print(
                    "پاسخ بازار معتبر نیست"
                )

                return []



            print(
                "داده خام بازار دریافت شد"
            )



        except Exception as e:


            print(
                "❌ خطا در اتصال TSETMC:",
                e
            )



        return symbols



    def filter_funds(
        self,
        symbols
    ):


        funds = []


        keywords = [

            "صندوق",

            "دارا",

            "کمند",

            "عیار",

            "طلا",

            "اهرم",

            "توان",

            "ثابت"

        ]



        for item in symbols:


            name = item.get(
                "name",
                ""
            )


            if any(
                k in name
                for k in keywords
            ):


                funds.append(item)



        return funds


