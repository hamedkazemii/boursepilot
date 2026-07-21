import json


class FundRepository:

    FILE="data/fund_registry.json"


    def load(self):

        with open(
            self.FILE,
            encoding="utf-8"
        ) as f:

            return json.load(f)
