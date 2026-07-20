import requests


class PublicFundProvider:


    def __init__(self, url=None):

        self.url = url



    def fetch(self, fund_name):

        if not self.url:

            raise ValueError(
                "Public fund data URL is not configured"
            )


        response = requests.get(
            self.url,
            timeout=10
        )


        response.raise_for_status()


        return response.json()
