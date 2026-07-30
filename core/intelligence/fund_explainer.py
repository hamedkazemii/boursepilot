from __future__ import annotations

import json
from typing import Any

from core.database.connection import get_database

from core.intelligence.templates import (
    STRENGTH_MESSAGES,
    RISK_MESSAGES,
    RECOMMENDATION_LABELS,
)


class FundExplainer:
    """
    توضیح هوشمند رتبه صندوق
    """

    def __init__(self):
        self.db = get_database()


    def explain(self, symbol: str) -> dict[str, Any]:

        row = self.db.fetchone(
            """
            SELECT
                f.symbol,
                f.name,
                f.fund_type,

                d.score_date,
                d.rank,
                d.final_score,
                d.recommendation,

                d.trend_score,
                d.liquidity_score,
                d.risk_score,
                d.money_flow_score,
                d.volume_score,
                d.technical_score,
                d.historical_return_score,

                d.factors_json,
                d.reasons_json

            FROM daily_scores d

            JOIN funds f
            ON f.id=d.fund_id

            WHERE f.symbol=?

            ORDER BY d.score_date DESC
            LIMIT 1
            """,
            (symbol,),
        )


        if not row:
            return {
                "error": "صندوق پیدا نشد"
            }


        data=dict(row)


        strengths=[]
        risks=[]


        for key,(threshold,msg) in STRENGTH_MESSAGES.items():

            value=data.get(key)

            if value is not None and value >= threshold:
                strengths.append(msg)



        for key,(threshold,msg) in RISK_MESSAGES.items():

            value=data.get(key)

            if value is not None and value <= threshold:
                risks.append(msg)



        return {

            "symbol": data["symbol"],
            "name": data["name"],
            "type": data["fund_type"],

            "date": data["score_date"],

            "rank": data["rank"],
            "score": round(data["final_score"],2),

            "recommendation":
                RECOMMENDATION_LABELS.get(
                    data["recommendation"],
                    data["recommendation"]
                ),

            "strengths": strengths,
            "risks": risks,

            "raw": {
                "factors":
                    json.loads(data["factors_json"])
                    if data["factors_json"]
                    else {},

                "reasons":
                    json.loads(data["reasons_json"])
                    if data["reasons_json"]
                    else {},
            }
        }



def explain_fund(symbol:str):

    return FundExplainer().explain(symbol)
