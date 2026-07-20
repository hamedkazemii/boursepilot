import json
import os


class FundRegistry:


    def __init__(self):

        self.file = "data/fund_registry.json"



    def save(self, funds):

        os.makedirs(
            "data",
            exist_ok=True
        )

        with open(
            self.file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                funds,
                f,
                ensure_ascii=False,
                indent=4
            )



    def load(self):

        if not os.path.exists(self.file):

            return []


        with open(
            self.file,
            encoding="utf-8"
        ) as f:

            return json.load(f)
