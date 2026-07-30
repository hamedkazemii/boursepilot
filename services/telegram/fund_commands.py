from services.analysis.fund_explainer import explain_fund


def format_fund_explain(symbol: str) -> str:
    data = explain_fund(symbol)

    if not data:
        return f"❌ صندوق {symbol} پیدا نشد"

    lines=[]

    lines.append(f"📊 تحلیل صندوق {data['symbol']}")
    lines.append("")
    lines.append(f"رتبه بازار: {data['rank']}")
    lines.append(f"امتیاز: {data['score']}")
    lines.append("")
    lines.append(
        f"وضعیت: {data['recommendation']}"
    )

    lines.append("")
    lines.append("نقاط کلیدی:")

    for f in data.get("raw",{}).get("factors",[])[:5]:
        lines.append(
            f"• {f['title']}: {f['label']} ({f['score']})"
        )

    return "\n".join(lines)
