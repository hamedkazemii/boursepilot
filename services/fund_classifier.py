class FundClassifier:


    def classify(self, info):

        sector = info.get(
            "sector",
            {}
        ).get(
            "lSecVal",
            ""
        )


        desc = info.get(
            "faraDesc",
            ""
        )


        group = info.get(
            "cgrValCotTitle",
            ""
        )


        text = (
            sector +
            desc +
            group
        )


        if "صندوق" not in text and "ETF" not in text:

            return "UNKNOWN"


        if "اهرم" in text:

            return "اهرمی"


        if "طلا" in text:

            return "طلا"


        if "ثابت" in text:

            return "درآمد ثابت"


        return "سهامی"
