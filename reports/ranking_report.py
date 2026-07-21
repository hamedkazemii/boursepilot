from datetime import datetime


class RankingReport:

    def generate(self, ranked_funds):

        if not ranked_funds:
            return "داده‌ای برای تحلیل وجود ندارد."

        lines = []

        lines.append(
            "📊 گزارش صبحگاهی Sandoghchi"
        )

        lines.append(
            "============================"
        )

        lines.append(
            "\n🏆 رتبه‌بندی صندوق‌ها\n"
        )


        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]


        for index, fund in enumerate(ranked_funds, start=1):

            medal = (
                medals[index-1]
                if index <= 3
                else f"{index})"
            )


            lines.append(
                f"""
{medal} {fund.name}

⭐ امتیاز BPI:
{fund.score} از 100

📌 اقدام:
{fund.decision}
"""
            )


        best = ranked_funds[0]

        weakest = ranked_funds[-1]


        lines.append(
            f"""
⭐ بهترین گزینه امروز:
{best.name}

⚠️ نیازمند بررسی بیشتر:
{weakest.name}

🕘 زمان تولید:
{datetime.now().strftime("%Y/%m/%d - %H:%M")}
"""
        )


        return "\n".join(lines)
