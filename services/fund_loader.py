import json


class FundLoader:

    def load(self):

        with open(
            "data/funds.json",
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)
