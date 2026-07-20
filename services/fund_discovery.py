import requests


class FundDiscovery:

    SEARCH_URL = "https://old.tsetmc.com/tsev2/data/search.aspx"

    KEYWORDS = [
        "صندوق",
        "طلا",
        "ثابت",
        "اهرم",
        "دارا",
        "کمند",
        "افران",
        "عیار"
    ]


    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0"
            }
        )


    def search(self, keyword):

        r = self.session.get(
            self.SEARCH_URL,
            params={
                "skey": keyword
            },
            timeout=20
        )

        r.raise_for_status()

        return r.text


    def parse(self, text):

        results = []

        rows = text.split(";")

        for row in rows:

            row = row.strip()

            if not row:
                continue

            parts = row.split(",")

            if len(parts) < 5:
                continue

            results.append({

                "symbol": parts[0].strip(),

                "name": parts[1].strip(),

                "ins_code": parts[2].strip()

            })

        return results


    def discover(self):

        all_items = {}

        for keyword in self.KEYWORDS:

            print("جستجو:", keyword)

            raw = self.search(keyword)

            items = self.parse(raw)

            for item in items:

                all_items[item["ins_code"]] = item

        return list(all_items.values())
