import json
from pathlib import Path


class FundRepository:

    def __init__(self):

        self.file = Path("data/funds.json")

    def load(self):

        if not self.file.exists():
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

    def add(self, fund):

        funds = self.load()

        codes = {
            item["ins_code"]
            for item in funds
        }

        if fund["ins_code"] not in codes:

            funds.append(fund)

            self.save(funds)

    def find(self, ins_code):

        for item in self.load():

            if item["ins_code"] == ins_code:

                return item

        return None
