#!/usr/bin/env python3
"""
اسکریپت تست: نمایش نمونه پیام بهبود یافته برای تلگرام
بدون نیاز به API واقعی - فقط نمایش خروجی
"""

from dataclasses import dataclass
from services.telegram_report_formatter import TelegramReportFormatter


@dataclass
class MockAssessment:
    """کلاس نمونه برای تست"""
    rank: int
    symbol: str
    name: str
    final_score: float
    recommendation: str
    recommendation_label: str
    last_price: float
    change_pct: float
    volume: int
    value: int
    premium_pct: float
    summary_reasons: list


def create_sample_funds():
    """ایجاد نمونه صندوق‌ها برای تست"""
    return [
        MockAssessment(
            rank=1, symbol="تصدی", name="تصدی فولاد",
            final_score=87.5, recommendation="strong_buy", recommendation_label="خرید قوی 🟢🟢",
            last_price=125000, change_pct=3.5, volume=2500000, value=312500000000,
            premium_pct=2.3, 
            summary_reasons=["نقدشوندگی بالا", "صف خرید قوی", "مومنتوم مثبت"]
        ),
        MockAssessment(
            rank=2, symbol="ایران", name="ایران بانک",
            final_score=85.2, recommendation="buy", recommendation_label="خرید 🟢",
            last_price=98000, change_pct=2.1, volume=1800000, value=176400000000,
            premium_pct=-1.5, 
            summary_reasons=["تخفیف جزئی", "پتانسیل بالا", "نقدشوندگی خوب"]
        ),
        MockAssessment(
            rank=3, symbol="فروغ", name="فروغ انرژی",
            final_score=83.1, recommendation="buy", recommendation_label="خرید 🟢",
            last_price=156000, change_pct=1.8, volume=950000, value=148200000000,
            premium_pct=6.2, 
            summary_reasons=["حباب متوسط اما قابل تحمل", "مومنتوم مثبت", "حجم معاملات خوب"]
        ),
        MockAssessment(
            rank=4, symbol="رقم", name="رقم بانک",
            final_score=78.3, recommendation="hold", recommendation_label="نگهدارش 🟡",
            last_price=87500, change_pct=0.5, volume=650000, value=56875000000,
            premium_pct=-3.2, 
            summary_reasons=["تخفیف متوسط", "نقدشوندگی متوسط"]
        ),
        MockAssessment(
            rank=5, symbol="حق", name="حق تقدم",
            final_score=72.1, recommendation="hold", recommendation_label="نگهدارش 🟡",
            last_price=45000, change_pct=-1.2, volume=420000, value=18900000000,
            premium_pct=-4.8, 
            summary_reasons=["تخفیف جذاب", "ریسک متوسط"]
        ),
        MockAssessment(
            rank=6, symbol="رسا", name="رسا انرژی",
            final_score=68.5, recommendation="sell", recommendation_label="فروش 🔴",
            last_price=156000, change_pct=-2.3, volume=320000, value=49920000000,
            premium_pct=8.7, 
            summary_reasons=["حباب شدید", "نقدشوندگی ضعیف", "مومنتوم منفی"]
        ),
    ]


def print_separator(title: str = ""):
    """چاپ جداکننده"""
    if title:
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    else:
        print(f"\n{'─'*60}\n")


def main():
    print("\n🚀 تست نمونه پیام‌های تلگرام بهبود یافته\n")
    
    samples = create_sample_funds()
    formatter = TelegramReportFormatter()
    
    # تست 1: کارت فردی صندوق
    print_separator("1️⃣ تست کارت صندوق فردی")
    for fund in samples[:3]:
        print(formatter.format_fund_card(fund))
        print_separator()
    
    # تست 2: ماتریس صندوق‌های برتر
    print_separator("2️⃣ تست ماتریس صندوق‌های برتر")
    print(formatter.format_top_funds_matrix(samples, top_n=5))
    
    # تست 3: خلاصه حباب و تخفیف
    print_separator("3️⃣ تست تحلیل حباب و تخفیف")
    print(formatter.format_bubble_summary(samples))
    
    # تست 4: گزارش کامل (آنچه به تلگرام فرستاده می‌شود)
    print_separator("4️⃣ گزارش کامل برای تلگرام (نسخه نهایی)")
    full_report = formatter.format_daily_ranking_report(samples, top_n=5)
    print(full_report)
    
    print_separator()
    print("✅ تست تکمیل شد!")
    print("\n📱 این پیام به تلگرام فرستاده می‌شود:")
    print(f"طول پیام: {len(full_report)} کاراکتر")
    print(f"تعداد خطوط: {len(full_report.split(chr(10)))} خط")
    

if __name__ == "__main__":
    main()
