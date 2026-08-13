"""سرویس انتشار گزارش در تلگرام با تحلیل حباب و فرمت بهبود یافته."""

import logging
from typing import Optional, List, Any
from core.bubble_analyzer import BubbleAnalyzer

logger = logging.getLogger(__name__)


class TelegramReportFormatter:
    """فرمت‌کننده پیام‌های تلگرام برای صندوق‌ها."""

    @staticmethod
    def format_fund_card(assessment: Any, include_bubble: bool = True) -> str:
        """
        فرمت یک کارت صندوق برای تلگرام.
        
        مثال خروجی:
        ┌─ 1️⃣ تصدی (فولاد)
        ├─ امتیاز: 87.5/100 | خرید قوی 🟢
        ├─ قیمت: 125,000 | تغیر: +3.5%
        ├─ حجم: 2.5M | ارزش: 312.5B
        └─ 📊 حباب 2.3% (معقول)
        """
        lines = []
        
        # ردیف اول: نام و رنک
        rank_emoji = TelegramReportFormatter._get_rank_emoji(assessment.rank)
        lines.append(f"{rank_emoji} {assessment.symbol} ({assessment.name})")
        
        # امتیاز و توصیه
        rec_emoji = TelegramReportFormatter._get_rec_emoji(assessment.recommendation)
        lines.append(f"  امتیاز: {assessment.final_score:.1f}/100 | {rec_emoji} {assessment.recommendation_label}")
        
        # قیمت و تغیر
        price_str = f"{assessment.last_price:,.0f}" if assessment.last_price else "-"
        change = f"+{assessment.change_pct:.2f}%" if assessment.change_pct and assessment.change_pct > 0 else f"{assessment.change_pct:.2f}%" if assessment.change_pct else "-"
        lines.append(f"  قیمت: {price_str} | تغیر: {change}")
        
        # حجم و ارزش
        volume_str = TelegramReportFormatter._fmt_number(assessment.volume)
        value_str = TelegramReportFormatter._fmt_number(assessment.value)
        lines.append(f"  حجم: {volume_str} | ارزش: {value_str}")
        
        # تحلیل حباب/تخفیف NAV
        if include_bubble and assessment.premium_pct is not None:
            bubble_insight = BubbleAnalyzer.generate_bubble_insight(assessment.premium_pct, assessment.rank or 0)
            lines.append(f"  {bubble_insight}")
        
        # دلایل اصلی (حداکثر 2 دلیل)
        if assessment.summary_reasons:
            for reason in assessment.summary_reasons[:2]:
                lines.append(f"  💡 {reason}")
        
        return "\n".join(lines)

    @staticmethod
    def format_top_funds_matrix(assessments: List[Any], top_n: int = 10) -> str:
        """
        فرمت ماتریسی صندوق‌های برتر برای هر نوع.
        
        مثال خروجی:
        ┏━━━━━ 🏆 صندوق‌های برتر ━━━━━┓
        ┃ رتبه │ نماد    │ امتیاز │ نوع        ┃
        ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
        ┃  1  │ تصدی   │  87.5  │ فولاد ☑️   ┃
        ┃  2  │ ایران  │  85.2  │ بانک ☑️    ┃
        ┃  3  │ فروغ   │  83.1  │ انرژی ☑️   ┃
        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
        """
        lines = []
        lines.append("┏━━━━ 🏆 صندوق‌های برتر ━━━━┓")
        lines.append("┃ # │ نماد      │ امتیاز │ توصیه     ┃")
        lines.append("┣━━━━━━━━━━━━━━━━━━━━━━━━━━┫")
        
        for assessment in assessments[:top_n]:
            rank = assessment.rank or 0
            symbol = assessment.symbol[:8].ljust(8)
            score = f"{assessment.final_score:.1f}".rjust(6)
            rec_emoji = TelegramReportFormatter._get_rec_emoji(assessment.recommendation)
            lines.append(f"┃ {rank:2d} │ {symbol} │ {score} │ {rec_emoji}        ┃")
        
        lines.append("┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
        return "\n".join(lines)

    @staticmethod
    def format_bubble_summary(assessments: List[Any]) -> str:
        """
        خلاصه تحلیل حباب و تخفیف تمام صندوق‌ها.
        
        مثال خروجی:
        📊 تحلیل حباب و تخفیف NAV:
        
        🔴 حباب زیاد (5+): 8 صندوق
         • تصدی: 8.3%  • ایران: 6.2%  • فروغ: 5.8%
        
        🟡 حباب متوسط: 15 صندوق
        
        ✅ متعادل: 32 صندوق
        
        🟢 تخفیف (فرصت): 12 صندوق
         • حق: -4.2%  • رقم: -3.1%
        """
        lines = []
        lines.append("📊 تحلیل حباب و تخفیف NAV:")
        lines.append("")
        
        # دسته‌بندی
        expensive = [a for a in assessments if a.premium_pct and a.premium_pct > 5]
        bubble_mod = [a for a in assessments if a.premium_pct and 2 < a.premium_pct <= 5]
        neutral = [a for a in assessments if a.premium_pct and -2 <= a.premium_pct <= 2]
        discount = [a for a in assessments if a.premium_pct and a.premium_pct < -2]
        
        # حباب زیاد
        if expensive:
            lines.append(f"🔴 حباب زیاد (5%+): {len(expensive)} صندوق")
            symbols_str = "  • " + "  • ".join([f"{a.symbol}: {a.premium_pct:.1f}%" for a in expensive[:4]])
            lines.append(symbols_str)
            lines.append("")
        
        # حباب متوسط
        if bubble_mod:
            lines.append(f"🟡 حباب متوسط: {len(bubble_mod)} صندوق")
            lines.append("")
        
        # متعادل
        if neutral:
            lines.append(f"✅ متعادل: {len(neutral)} صندوق")
            lines.append("")
        
        # تخفیف (فرصت)
        if discount:
            lines.append(f"🟢 تخفیف (فرصت خرید): {len(discount)} صندوق")
            symbols_str = "  • " + "  • ".join([f"{a.symbol}: {a.premium_pct:.1f}%" for a in discount[:4]])
            lines.append(symbols_str)
            lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def format_daily_ranking_report(assessments: List[Any], top_n: int = 15) -> str:
        """
        گزارش کامل رنکینگ روزانه برای تلگرام.
        """
        lines = []
        lines.append("📈 گزارش رنکینگ صندوق‌های قابل‌معامله")
        lines.append("=" * 50)
        lines.append("")
        
        # خلاصه تحلیل حباب
        lines.append(TelegramReportFormatter.format_bubble_summary(assessments))
        lines.append("")
        
        # ماتریس صندوق‌های برتر
        lines.append(TelegramReportFormatter.format_top_funds_matrix(assessments, top_n))
        lines.append("")
        
        # صندوق‌های برتر با جزئیات
        lines.append("🏆 صندوق‌های برتر (جزئیات):")
        lines.append("─" * 50)
        for assessment in assessments[:5]:
            lines.append("")
            lines.append(TelegramReportFormatter.format_fund_card(assessment))
        
        lines.append("")
        lines.append("=" * 50)
        lines.append("📊 امتیاز بر اساس: نقدشوندگی + پیش‌سفارش + جریان + مومنتوم + حجم + NAV")
        
        return "\n".join(lines)

    @staticmethod
    def _get_rec_emoji(recommendation: str) -> str:
        """emoji برای توصیه."""
        rec_map = {
            "strong_buy": "🟢🟢",
            "buy": "🟢",
            "hold": "🟡",
            "sell": "🔴",
            "strong_sell": "🔴🔴",
        }
        return rec_map.get(recommendation, "⚪")

    @staticmethod
    def _get_rank_emoji(rank: Optional[int]) -> str:
        """emoji برای رتبه."""
        if not rank:
            return "📌"
        if rank == 1:
            return "🥇"
        if rank == 2:
            return "🥈"
        if rank == 3:
            return "🥉"
        return f"{rank}️⃣"

    @staticmethod
    def _fmt_number(value: Any) -> str:
        """فرمت عدد برای نمایش."""
        if value is None:
            return "-"
        try:
            v = float(value)
            if v >= 1_000_000_000:
                return f"{v/1_000_000_000:.1f}B"
            elif v >= 1_000_000:
                return f"{v/1_000_000:.1f}M"
            elif v >= 1_000:
                return f"{v/1_000:.0f}K"
            return f"{v:.0f}"
        except:
            return str(value)


# نمونه استفاده برای تست
if __name__ == "__main__":
    from dataclasses import dataclass
    
    @dataclass
    class SampleAssessment:
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
    
    # نمونه داده‌ها
    samples = [
        SampleAssessment(
            rank=1, symbol="تصدی", name="تصدی فولاد",
            final_score=87.5, recommendation="strong_buy", recommendation_label="خرید قوی",
            last_price=125000, change_pct=3.5, volume=2500000, value=312500000000,
            premium_pct=2.3, summary_reasons=["نقدشوندگی بالا", "تقاضای قوی"]
        ),
        SampleAssessment(
            rank=2, symbol="ایران", name="ایران بانک",
            final_score=85.2, recommendation="buy", recommendation_label="خرید",
            last_price=98000, change_pct=2.1, volume=1800000, value=176400000000,
            premium_pct=-1.5, summary_reasons=["تخفیف جزئی", "پتانسیل بالا"]
        ),
        SampleAssessment(
            rank=3, symbol="فروغ", name="فروغ انرژی",
            final_score=83.1, recommendation="buy", recommendation_label="خرید",
            last_price=156000, change_pct=1.8, volume=950000, value=148200000000,
            premium_pct=6.2, summary_reasons=["حباب متوسط", "مومنتوم مثبت"]
        ),
    ]
    
    # تست فرمت‌کننده
    formatter = TelegramReportFormatter()
    
    print("=" * 60)
    print("تست فرمت کارت صندوق:")
    print("=" * 60)
    for sample in samples:
        print(formatter.format_fund_card(sample))
        print()
    
    print("=" * 60)
    print("تست گزارش کامل:")
    print("=" * 60)
    print(formatter.format_daily_ranking_report(samples, top_n=3))
