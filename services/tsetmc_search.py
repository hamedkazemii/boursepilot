import requests


class TSETMCSearch:

    BASE_URL = "https://old.tsetmc.com/tsev2/data/search.aspx"

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://old.tsetmc.com/"
            }
        )

    def search(self, keyword):

        response = self.session.get(
            self.BASE_URL,
            params={
                "skey": keyword
            },
            timeout=20
        )

        response.raise_for_status()

        return self.parse(response.text)

    def parse(self, text):

        results = []

        rows = text.split(";")

        for row in rows:

            row = row.strip()

            if not row:
                continue

            cols = row.split(",")

            if len(cols) < 3:
                continue

            results.append(
                {
                    "symbol": cols[0].strip(),
                    "title": cols[1].strip(),
                    "ins_code": cols[2].strip(),
                    "raw": cols
                }
            )

        return results
