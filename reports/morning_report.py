

def create_report(items):


    lines = []


    lines.append(
        "📊 گزارش صبحگاهی Sandoghchi"
    )


    lines.append(
        "="*45
    )


    for index,item in enumerate(items,1):


        lines.append("")


        lines.append(
            f"🏆 رتبه {index}: {item['name']}"
        )


        lines.append(
            f"⭐ امتیاز BPI: {item['bpi']} از 100"
        )


        lines.append(
            "📌 تحلیل:"
        )


        lines.append(
            item.get(
                "summary",
                "اطلاعات تکمیلی موجود نیست"
            )
        )


        lines.append(
            "-"*45
        )


    return "\n".join(lines)


