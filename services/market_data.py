class MarketDataService:

    def get_fund_performance(self, fund_name: str) -> dict:

        return {
            "name": fund_name,
            "daily_return": 1.2,
            "weekly_return": 3.8,
            "monthly_return": 8.5
        }
