import json
import os


class FundRegistry:

    FILE = "data/funds.json"


    def load(self):

        if not os.path.exists(self.FILE):
            return []

        with open(
            self.FILE,
            encoding="utf-8"
        ) as f:

            return json.load(f)


    def save(self, funds):

        with open(
            self.FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                funds,
                f,
                ensure_ascii=False,
                indent=4
            )
