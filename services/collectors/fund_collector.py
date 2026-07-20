from datetime import datetime


class FundCollector:


    def __init__(
        self,
        provider,
        storage
    ):

        self.provider = provider

        self.storage = storage



    def collect(self, fund_name):


        data = self.provider.get_nav(
            fund_name
        )


        record = {

            "name": fund_name,

            "nav": data["nav"],

            "date": datetime.now().isoformat()

        }


        self.storage.save(
            record
        )


        return record
