
import json
import os


class MarketLoader:


    def __init__(self):

        self.file = "data/funds.json"



    def load(self):

        if not os.path.exists(self.file):

            return []


        with open(
            self.file,
            encoding="utf-8"
        ) as f:

            return json.load(f)



    def save(self, funds):

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


