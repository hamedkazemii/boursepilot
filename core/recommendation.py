from dataclasses import dataclass


@dataclass
class Recommendation:

    symbol:str
    name:str
    score:int
    decision:str



class RecommendationEngine:


    def evaluate(
        self,
        fund,
        market,
        analysis
    ):


        score = 50


        text = str(
            analysis
        )


        if "قوی" in text:
            score += 20


        if "صف خرید" in text:
            score += 15


        if "فروش" in text:
            score -= 15



        score = max(
            0,
            min(
                score,
                100
            )
        )


        if score >= 80:

            decision="BUY"

        elif score >=60:

            decision="HOLD"

        else:

            decision="AVOID"



        return Recommendation(

            symbol=fund["symbol"],

            name=fund["name"],

            score=score,

            decision=decision

        )
