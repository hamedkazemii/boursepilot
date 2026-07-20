from datetime import datetime


class MockMarketProvider:

    def get_fund_data(self, fund_name):

        data = {

            "دارونو": {
                "daily_return": 1.2,
                "weekly_return": 3.8,
                "monthly_return": 8.5,
                "nav": 125430
            },

            "عیار": {
                "daily_return": 0.7,
                "weekly_return": 2.1,
                "monthly_return": 5.2,
                "nav": 108200
            },

            "سیمانو": {
                "daily_return": -0.2,
                "weekly_return": 0.5,
                "monthly_return": 1.4,
                "nav": 97500
            }

        }


        result = data.get(
            fund_name,
            {
                "daily_return": 0,
                "weekly_return": 0,
                "monthly_return": 0,
                "nav": 100000
            }
        )


        return {
            "name": fund_name,
            **result,
            "date": datetime.now().isoformat()
        }
