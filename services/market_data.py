from services.providers.mock_provider import MockMarketProvider


class MarketDataService:

    def __init__(self):

        self.provider = MockMarketProvider()


    def get_fund_performance(self, fund_name):

        data = self.provider.get_fund_data(
            fund_name
        )


        return {

            "daily_return": data["daily_return"],

            "weekly_return": data["weekly_return"],

            "monthly_return": data["monthly_return"]

        }
