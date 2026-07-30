#!/usr/bin/env bash
set -e

echo "🚀 BoursePilot Fund Explain v1 upgrade"

mkdir -p services/analysis

cat > services/analysis/fund_explainer.py <<'PY'
from __future__ import annotations

from core.database.connection import get_database
from core.pipeline.daily_analysis import DailyAnalysisPipeline
from services.providers.factory import get_market_data_provider


def _recommendation(score: float) -> str:
    if score >= 75:
        return "🟢 بررسی برای خرید"
    if score >= 60:
        return "🟡 نگهداری / بررسی بیشتر"
    return "🔴 کاهش وزن / عدم اولویت"


def explain_fund(symbol: str) -> dict:

    provider = get_market_data_provider()

    pipe = DailyAnalysisPipeline(
        provider=provider,
        allow_offline_seed=False
    )

    result = pipe.run()

    ranked = result["ranked"]

    target = None

    for item in ranked:
        if item.symbol == symbol:
            target = item
            break

    if target is None:
        return {
            "symbol": symbol,
            "error": "صندوق پیدا نشد"
        }


    position = ranked.index(target) + 1
    total = len(ranked)

    data = target.to_dict()


    factors = data.get("factors", [])

    strengths=[]
    risks=[]

    for f in factors:

        score=f.get("score",0)

        if score >=80:
            strengths.append(
                f"{f.get('title')} وضعیت عالی دارد"
            )

        elif score <40:
            risks.append(
                f"{f.get('title')} وضعیت ضعیف دارد"
            )


    return {

        "symbol":symbol,

        "rank":position,

        "total_funds":total,

        "percentile":
            round((1-position/total)*100,1),

        "score":
            round(float(data.get("final_score",0)),2),

        "recommendation":
            _recommendation(
                float(data.get("final_score",0))
            ),

        "strengths":strengths,

        "risks":risks,

        "raw":data
    }


if __name__=="__main__":

    import sys

    symbol=sys.argv[1] if len(sys.argv)>1 else "یاقوت"

    import json

    print(
        json.dumps(
            explain_fund(symbol),
            ensure_ascii=False,
            indent=2
        )
    )
PY


echo "✅ created services/analysis/fund_explainer.py"


cat > tools/test_explain.py <<'PY'
from services.analysis.fund_explainer import explain_fund
import sys,json

symbol=sys.argv[1] if len(sys.argv)>1 else "یاقوت"

x=explain_fund(symbol)

print(json.dumps(
    x,
    ensure_ascii=False,
    indent=2
))
PY


echo "🧪 running test"

python tools/test_explain.py یاقوت


echo "✅ DONE"

