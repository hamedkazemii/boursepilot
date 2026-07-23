#!/bin/bash
set -e

echo "🚀 BoursePilot Fund Explain v1.2"

mkdir -p services/analysis


cat > services/analysis/fund_explainer.py <<'PY'
from __future__ import annotations

from core.database.connection import get_database
from core.pipeline.daily_analysis import DailyAnalysisPipeline
from services.providers.factory import get_market_data_provider


def explain_fund(symbol: str):

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

    if not target:
        return {
            "error": f"صندوق {symbol} پیدا نشد"
        }


    factors = []

    for f in target.factors:
        factors.append(
            {
                "title": f.title,
                "score": round(f.score,2),
                "label": f.label,
                "reasons": f.reasons
            }
        )


    return {

        "symbol": target.symbol,
        "rank": target.rank,
        "score": round(target.final_score,2),
        "recommendation": target.recommendation_label,

        "summary": build_summary(target),

        "factors": factors
    }



def build_summary(item):

    if item.final_score >= 75:
        return "این صندوق در شرایط فعلی جزو گزینه‌های قابل بررسی برای سرمایه‌گذاری است."

    if item.final_score >=60:
        return "این صندوق وضعیت متوسط رو به خوب دارد و نیازمند بررسی بیشتر است."

    return "شرایط فعلی صندوق ضعیف‌تر از میانگین بازار است."

PY


cat > tools/test_explain_v12.py <<'PY'

from services.analysis.fund_explainer import explain_fund


for s in ["یاقوت","اهرم","سیگلو"]:

    x=explain_fund(s)

    print("="*40)
    print("📊",x["symbol"])
    print("رتبه:",x["rank"])
    print("امتیاز:",x["score"])
    print(x["summary"])

    for f in x["factors"][:5]:
        print(
            "-",
            f["title"],
            ":",
            f["label"],
            f["score"]
        )

PY


echo "🧪 TEST"

PYTHONPATH=. python tools/test_explain_v12.py


echo "✅ Fund Explain v1.2 READY"

