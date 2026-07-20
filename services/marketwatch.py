

class MarketWatchParser:


    def parse(self,file):

        return []



    def extract_etf(self,data):

        funds=[]


        for row in data:

            name=str(
                row.get(
                    "name",
                    ""
                )
            )


            if "صندوق" in name:

                funds.append(row)


        return funds

