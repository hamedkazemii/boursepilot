class MarketAnalyzer:

    def analyze(self, market):

        buy_volume = market["buy_volume"]
        sell_volume = market["sell_volume"]

        buy_orders = market["buy_orders"]
        sell_orders = market["sell_orders"]

        change = market["change_percent"]

        queue_buy = market["queue_buy"]
        queue_sell = market["queue_sell"]

        report = {}

        # -----------------------------
        # قدرت تقاضا
        # -----------------------------

        if buy_volume > sell_volume * 5:
            report["demand"] = "بسیار قوی"

        elif buy_volume > sell_volume * 2:
            report["demand"] = "قوی"

        elif buy_volume > sell_volume:
            report["demand"] = "متعادل"

        else:
            report["demand"] = "ضعیف"

        # -----------------------------
        # قدرت عرضه
        # -----------------------------

        if sell_volume == 0:
            report["supply"] = "تقریباً وجود ندارد"

        elif sell_volume > buy_volume:
            report["supply"] = "زیاد"

        else:
            report["supply"] = "عادی"

        # -----------------------------
        # وضعیت صف
        # -----------------------------

        if queue_buy:

            report["queue"] = "صف خرید"

        elif queue_sell:

            report["queue"] = "صف فروش"

        else:

            report["queue"] = "بدون صف"

        # -----------------------------
        # روند قیمت
        # -----------------------------

        if change > 2:

            report["trend"] = "صعودی"

        elif change < -2:

            report["trend"] = "نزولی"

        else:

            report["trend"] = "خنثی"

        # -----------------------------
        # جمع‌بندی
        # -----------------------------

        if queue_buy and report["demand"] == "بسیار قوی":

            report["summary"] = (
                "قدرت خریداران بسیار بالاست و در حال حاضر "
                "فشار فروش مؤثری مشاهده نمی‌شود."
            )

        elif queue_sell:

            report["summary"] = (
                "قدرت فروشندگان بالاست و ورود سرمایه "
                "با ریسک همراه است."
            )

        else:

            report["summary"] = (
                "بازار در وضعیت متعادل قرار دارد."
            )

        return report
