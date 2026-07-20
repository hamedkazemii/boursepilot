from datetime import datetime


class NAVService:

    def get_nav(self, fund_name):

        mock_nav = {

            "دارونو": 125430,

            "عیار": 108200,

            "سیمانو": 97500

        }


        return {
            "name": fund_name,
            "nav": mock_nav.get(
                fund_name,
                100000
            ),
            "date": datetime.now().isoformat()
        }
