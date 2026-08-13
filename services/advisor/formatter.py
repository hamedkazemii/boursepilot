def percentile_text(rank,total):

    if not total:
        return ""

    pct=round((1-rank/total)*100)

    return f"بهتر از حدود {pct}% صندوق‌های بازار"


def risk_messages(factors):

    result=[]

    for f in factors:

        title=f.get("title","")
        score=f.get("score",0)

        if score < 40:

            if "مومنتوم" in title:
                result.append(
                    "⚠️ روند کوتاه‌مدت ضعیف شده است"
                )

            elif "فشار" in title:
                result.append(
                    "⚠️ فشار عرضه در بازار وجود دارد"
                )

            else:
                result.append(
                    f"⚠️ {title} نیاز به بررسی دارد"
                )


    return result



def strength_messages(factors):

    result=[]

    for f in factors:

        if f.get("score",0)>=85:

            result.append(
                f"✅ {f['title']} وضعیت بسیار مناسب دارد"
            )

    return result



def build_user_report(data):

    lines=[]

    lines.append(
        f"📊 تحلیل صندوق {data['symbol']}"
    )

    lines.append("")

    lines.append(
        f"🏆 رتبه: {data['rank']} از {data['total_funds']}"
    )


    lines.append(
        percentile_text(
            data['rank'],
            data['total_funds']
        )
    )


    lines.append("")

    lines.append(
        f"امتیاز: {data['score']}/100"
    )

    lines.append("")

    lines.append(
        f"وضعیت: {data['recommendation']}"
    )


    return "\n".join(lines)

