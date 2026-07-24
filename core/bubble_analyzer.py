"""تحلیل حباب (Premium) و تخفیف (Discount) NAV صندوق‌ها."""

from typing import Optional, Dict, Any


class BubbleAnalyzer:
    """تحلیل کمی و کیفی حباب و تخفیف قیمت نسبت به NAV."""

    @staticmethod
    def analyze_bubble(premium_pct: Optional[float]) -> Dict[str, Any]:
        """
        تحلیل وضعیت حباب/تخفیف صندوق.
        
        Args:
            premium_pct: درصد حباب (مثبت) یا تخفیف (منفی)
        
        Returns:
            dict شامل: status, risk_level, explanation
        """
        if premium_pct is None:
            return {
                "status": "نامعلوم",
                "risk_level": "نامعلوم",
                "explanation": "داده NAV موجود نیست"
            }

        if premium_pct > 5:
            return {
                "status": "حباب زیاد",
                "risk_level": "⛔ خطر",
                "emoji": "📈",
                "explanation": f"صندوق {premium_pct:.2f}% گرانتر از NAV معاملات می‌شود. خطر بالا برای ورود جدید."
            }
        elif premium_pct > 2:
            return {
                "status": "حباب متوسط",
                "risk_level": "⚠️ احتیاط",
                "emoji": "📊",
                "explanation": f"حباب {premium_pct:.2f}% بالای NAV. احتیاط در خرید توصیه می‌شود."
            }
        elif premium_pct > 0:
            return {
                "status": "حباب کم",
                "risk_level": "✅ معقول",
                "emoji": "📈",
                "explanation": f"حباب جزئی {premium_pct:.2f}%. وضعیت نرمال برای صندوق‌های پرگردش."
            }
        elif premium_pct > -2:
            return {
                "status": "تخفیف کم",
                "risk_level": "✅ فرصت",
                "emoji": "📉",
                "explanation": f"تخفیف جزئی {abs(premium_pct):.2f}%. فرصت خرید با تخفیف."
            }
        elif premium_pct > -5:
            return {
                "status": "تخفیف متوسط",
                "risk_level": "🎯 فرصت خوب",
                "emoji": "📉",
                "explanation": f"تخفیف {abs(premium_pct):.2f}% نسبت به NAV. فرصت جذاب برای خریداران."
            }
        else:
            return {
                "status": "تخفیف بسیار زیاد",
                "risk_level": "🎯 فرصت عالی",
                "emoji": "📉",
                "explanation": f"تخفیف {abs(premium_pct):.2f}% عمیق! سیگنال خرید قوی (بررسی دلایل ضروری است)."
            }

    @staticmethod
    def compare_bubbles(assessments: list[Any]) -> Dict[str, Any]:
        """
        مقایسه و تحلیل حباب‌های صندوق‌ها.
        
        Args:
            assessments: لیست FundAssessment
        
        Returns:
            آمار و تحلیل جامع
        """
        valid = [a for a in assessments if a.premium_pct is not None]
        
        if not valid:
            return {"count": 0, "message": "داده NAV موجود نیست"}
        
        premiums = [a.premium_pct for a in valid]
        
        expensive = [a for a in valid if a.premium_pct > 5]
        discounted = [a for a in valid if a.premium_pct < -2]
        neutral = [a for a in valid if -2 <= a.premium_pct <= 2]
        
        return {
            "total_analyzed": len(valid),
            "avg_premium": sum(premiums) / len(premiums),
            "max_premium": max(premiums),
            "min_premium": min(premiums),
            "expensive_count": len(expensive),
            "expensive_funds": [(a.symbol, a.premium_pct) for a in expensive[:5]],
            "discounted_count": len(discounted),
            "discounted_funds": [(a.symbol, a.premium_pct) for a in discounted[:5]],
            "neutral_count": len(neutral),
        }

    @staticmethod
    def generate_bubble_insight(premium_pct: Optional[float], rank: int) -> str:
        """خط توضیح کوتاه برای پیام تلگرام."""
        if premium_pct is None:
            return ""
        
        analysis = BubbleAnalyzer.analyze_bubble(premium_pct)
        emoji = analysis.get("emoji", "")
        status = analysis.get("status", "")
        
        if premium_pct > 5:
            return f"{emoji} حباب {premium_pct:.1f}% - احتیاط!"
        elif premium_pct < -2:
            return f"{emoji} تخفیف {abs(premium_pct):.1f}% - فرصت"
        else:
            return f"{emoji} NAV: {status}"
