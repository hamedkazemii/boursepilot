from dataclasses import dataclass


@dataclass
class DecisionResult:
    action: str
    description: str
    confidence: str


class DecisionEngine:

    def decide(self, bpi_score: int) -> DecisionResult:

        if bpi_score >= 85:
            return DecisionResult(
                action="افزایش موقعیت",
                description=(
                    "امتیاز BPI در محدوده جذاب قرار دارد. "
                    "ترکیب عملکرد، روند و ریسک صندوق مناسب ارزیابی شده است. "
                    "افزایش سرمایه‌گذاری به صورت تدریجی قابل بررسی است."
                ),
                confidence="بالا"
            )

        elif bpi_score >= 70:
            return DecisionResult(
                action="نگهداری",
                description=(
                    "وضعیت صندوق متعادل ارزیابی می‌شود. "
                    "در شرایط فعلی سیگنال قوی برای خرید بیشتر یا خروج وجود ندارد."
                ),
                confidence="متوسط"
            )

        elif bpi_score >= 50:
            return DecisionResult(
                action="کاهش تدریجی موقعیت / بررسی سیو سود",
                description=(
                    "جذابیت نسبی صندوق کاهش پیدا کرده است. "
                    "اگر سرمایه‌گذار در سود است، شناسایی بخشی از سود می‌تواند بررسی شود. "
                    "این تصمیم به معنی فروش کامل صندوق نیست."
                ),
                confidence="متوسط"
            )

        else:
            return DecisionResult(
                action="بررسی خروج",
                description=(
                    "امتیاز صندوق وارد محدوده ضعیف شده است. "
                    "بررسی کاهش جدی موقعیت و عوامل بنیادی توصیه می‌شود."
                ),
                confidence="بالا"
            )
