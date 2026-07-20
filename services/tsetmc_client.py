import requests


class TSETMCClient:

    BASE_URL = "https://cdn.tsetmc.com/api"

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0"
            }
        )

    def _get(self, endpoint):

        response = self.session.get(
            f"{self.BASE_URL}/{endpoint}",
            timeout=20
        )

        response.raise_for_status()

        return response.json()

    def instrument(self, ins_code):

        return self._get(
            f"Instrument/GetInstrumentInfo/{ins_code}"
        )

    def closing_price(self, ins_code):

        return self._get(
            f"ClosingPrice/GetClosingPriceInfo/{ins_code}"
        )

    def orderbook(self, ins_code):

        return self._get(
            f"BestLimits/{ins_code}"
        )

    def trades(self, ins_code):

        return self._get(
            f"Trade/GetTrade/{ins_code}"
        )

    def history(self, ins_code):

        return self._get(
            f"ClosingPrice/GetClosingPriceDailyList/{ins_code}/0"
        )
