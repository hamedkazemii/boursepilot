class MarketScore:

    def calculate(self, market):

        score = 50
        reasons = []
        risks = []

        if market.get("queue_buy"):
            score += 20
            reasons.append(
                "صف خرید فعال است"
            )

        if market.get("pressure",0) > 70:
            score += 15
            reasons.append(
                "قدرت تقاضا بالاست"
            )

        if market.get("change_percent",0) > 0:
            score += 10
            reasons.append(
                "روند قیمت مثبت است"
            )

        if market.get("sell_volume",0) == 0:
            risks.append(
                "فروشنده فعال مشاهده نشد"
            )


        score=min(score,100)


        return {

            "score":score,
            "reasons":reasons,
            "risks":risks

        }
