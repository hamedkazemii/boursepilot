class FundParser:


    def parse(self, raw_data):

        return {

            "name": raw_data.get("name"),

            "nav": self._to_number(
                raw_data.get("nav")
            ),

            "issue_price": self._to_number(
                raw_data.get("issue_price")
            ),

            "cancel_price": self._to_number(
                raw_data.get("cancel_price")
            )

        }


    def _to_number(self, value):

        if value is None:
            return 0


        if isinstance(value, int):
            return value


        value = (
            str(value)
            .replace(",", "")
            .strip()
        )


        try:
            return int(value)

        except ValueError:
            return 0
