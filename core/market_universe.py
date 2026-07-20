
import json
import os


class MarketUniverse:



    def __init__(self):

        self.file = (
            "data/market_universe.json"
        )



    def save(
        self,
        data
    ):


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
                data,
                f,
                ensure_ascii=False,
                indent=4
            )



    def load(self):


        if not os.path.exists(
            self.file
        ):

            return []


        with open(
            self.file,
            encoding="utf-8"
        ) as f:


            return json.load(f)


