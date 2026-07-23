"""
گزارش فارسی و کاربرپسند صندوقچی
v0.6
"""

from datetime import datetime


class HumanReportFormatter:

    def build(self, funds):

        now = datetime.now().strftime("%Y/%m/%d %H:%M")

        lines = []

        lines.append("📊 گزارش هوشمند صندوقچی")
        lines.append(f"🗓 {now}")
        lines.append("")
        lines.append("🟢 خلاصه وضعیت امروز بازار")
        lines.append("")
        lines.append(
            "این گزارش بر اساس بررسی صندوق‌های سرمایه‌گذاری، "
            "امتیازدهی هوشمند و وضعیت فعلی بازار تهیه شده است."
        )

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")

        if not funds:
            lines.append("امروز داده معتبری دریافت نشد.")
            return "\n".join(lines)

        medals = ["🥇", "🥈", "🥉"]

        for i, fund in enumerate(funds[:10]):

            medal = medals[i] if i < 3 else "⭐"

            name = (
                fund.get("name")
                or fund.get("symbol")
                or "نامشخص"
            )

            score = fund.get("score", 0)
            nav = fund.get("nav", "-")
            ret = fund.get("return_percent", "-")

            lines.append(f"{medal} رتبه {i+1}")
            lines.append("")
            lines.append(f"📌 {name}")
            lines.append("")
            lines.append(f"⭐ امتیاز کلی : {score}")
            lines.append(f"📈 بازده امروز : {ret}")
            lines.append(f"💰 NAV : {nav}")
            lines.append("")

            if isinstance(score, (int, float)):

                if score >= 90:
                    level = "بسیار عالی"
                    risk = "ریسک متوسط تا زیاد"
                    reason = (
                        "این صندوق امروز یکی از بهترین عملکردهای بازار را داشته "
                        "و از نظر امتیاز کلی در وضعیت بسیار مناسبی قرار دارد."
                    )

                elif score >= 80:
                    level = "مناسب"
                    risk = "ریسک متوسط"
                    reason = (
                        "عملکرد صندوق مطلوب ارزیابی شده و "
                        "برای بررسی بیشتر گزینه مناسبی محسوب می‌شود."
                    )

                elif score >= 70:
                    level = "قابل قبول"
                    risk = "ریسک متوسط"
                    reason = (
                        "صندوق شرایط قابل قبولی دارد اما "
                        "قبل از سرمایه‌گذاری بهتر است وضعیت بازار نیز بررسی شود."
                    )

                else:
                    level = "ضعیف"
                    risk = "ریسک بالا"
                    reason = (
                        "در حال حاضر امتیاز صندوق پایین بوده و "
                        "نیاز به بررسی بیشتری دارد."
                    )

            else:
                level = "-"
                risk = "-"
                reason = "اطلاعات کافی برای تحلیل وجود ندارد."

            lines.append("✅ تحلیل صندوق")
            lines.append(reason)
            lines.append("")
            lines.append(f"🏅 وضعیت : {level}")
            lines.append(f"⚠️ ریسک : {risk}")

            lines.append("")

            lines.append("👤 مناسب برای")

            if score >= 90:
                lines.append("سرمایه‌گذاران با دید میان‌مدت و ریسک‌پذیر")

            elif score >= 80:
                lines.append("سرمایه‌گذاران با ریسک متعادل")

            else:
                lines.append("افرادی که قبل از سرمایه‌گذاری تحلیل بیشتری انجام می‌دهند")

            lines.append("")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")

        lines.append("📌 جمع‌بندی")
        lines.append("")
        lines.append(
            "رتبه‌بندی فوق صرفاً یک ابزار کمکی برای تصمیم‌گیری است "
            "و نباید به تنهایی مبنای خرید یا فروش قرار گیرد."
        )

        lines.append("")
        lines.append("🤖 ارائه شده توسط صندوقچی")

        return "\n".join(lines)
