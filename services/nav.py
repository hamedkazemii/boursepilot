from datetime import datetime


class NAVService:

    def get_nav(self, fund_name: str) -> dict:
        """
        Temporary NAV provider.
        Later connected to real market API.
        """

        return {
            "name": fund_name,
            "nav": 125430,
            "date": datetime.now().isoformat()
        }
