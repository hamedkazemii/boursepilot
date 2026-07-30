"""تحلیل حباب (Premium) و تخفیف (Discount) NAV صندوق‌ها."""

from typing import Optional, Dict, Any, List


class BubbleAnalysis:
    """تحلیل و دسته‌بندی وضعیت حباب/تخفیف NAV صندوق‌ها."""

    # دسته‌بندی بر اساس درصد premium
    CATEGORIES = {
        "bubble_severe": {"range": (5, float('inf')), "emoji": "🔴", "status": "حباب شدید", "risk": "خطر"},
        "bubble_moderate": {"range": (2, 5), "emoji": "🟠", "status": "حباب متوسط", "risk": "احتیاط"},
        "bubble_light": {"range": (0, 2), "emoji": "📈", "status": "حباب جزئی", "risk": "معقول"},
        "neutral": {"range": (-2, 0), "emoji": "⚪", "status": "متعادل", "risk": "معقول"},
        "discount_light": {"range": (-5, -2), "emoji": "📉", "status": "تخفیف جزئی", "risk": "فرصت"},
        "discount_moderate": {"range": (-10, -5), "emoji": "🟢", "status": "تخفیف متوسط", "risk": "فرصت خوب"},
        "discount_severe": {"range": (float('-inf'), -10), "emoji": "🟢🟢", "status": "تخفیف عمیق", "risk": "فرصت عالی"},
    }

    @staticmethod
    def categorize(premium_pct: Optional[float]) -> Dict[str, Any]:
        """
        دسته‌بندی صندوق بر اساس درصد حباب/تخفیف.
        
        Args:
            premium_pct: درصد حباب (مثبت) یا تخفیف (منفی)
            
        Returns:
            dict شامل: category, emoji, status, risk, explanation
        """
        if premium_pct is None:
            return {
                "category": "unknown",
                "emoji": "❓",
                "status": "نامعلوم",
                "risk": "نامعلوم",
                "premium_pct": None,
                "explanation": "داده NAV در دسترس نیست"
            }

        for cat_key, cat_info in BubbleAnalysis.CATEGORIES.items():
            min_val, max_val = cat_info["range"]
            if min_val <= premium_pct < max_val:
                return {
                    "category": cat_key,
                    "emoji": cat_info["emoji"],
                    "status": cat_info["status"],
                    "risk": cat_info["risk"],
                    "premium_pct": round(premium_pct, 2),
                    "explanation": BubbleAnalysis._get_explanation(premium_pct, cat_key)
                }
        
        # fallback
        return {
            "category": "unknown",
            "emoji": "❓",
            "status": "نامعلوم",
            "risk": "نامعلوم",
            "premium_pct": premium_pct,
            "explanation": "داده خارج از محدوده"
        }

    @staticmethod
    def _get_explanation(premium_pct: float, category: str) -> str:
        """توضیح فارسی برای هر دسته."""
        explanations = {
            "bubble_severe": f"صندوق {abs(premium_pct):.1f}% گرانتر از NAV معاملات می‌شود - خطر اورقیمتی شدید",
            "bubble_moderate": f"حباب {abs(premium_pct):.1f}% بالای NAV - احتیاط در خرید توصیه می‌شود",
            "bubble_light": f"حباب جزئی {abs(premium_pct):.1f}% - وضعیت نسبتاً عادی",
            "neutral": "قیمت تقریباً برابر NAV - وضعیت متعادل",
            "discount_light": f"تخفیف {abs(premium_pct):.1f}% - فرصت خرید با قیمت مناسب",
            "discount_moderate": f"تخفیف {abs(premium_pct):.1f}% - فرصت جذاب برای خریداران",
            "discount_severe": f"تخفیف عمیق {abs(premium_pct):.1f}% - سیگنال خرید قوی (بررسی دلایل ضروری)",
        }
        return explanations.get(category, "وضعیت نامشخص")

    @staticmethod
    def compare_all(assessments: List[Any]) -> Dict[str, Any]:
        """
        تحلیل جامع حباب/تخفیف برای تمام صندوق‌ها.
        
        Args:
            assessments: لیست FundAssessment
            
        Returns:
            آمار و تحلیل دسته‌بندی شده
        """
        results = {
            "total": len(assessments),
            "with_nav_data": 0,
            "categories": {k: [] for k in BubbleAnalysis.CATEGORIES.keys()},
            "statistics": {},
            "summary": ""
        }

        premiums = []
        for assessment in assessments:
            if assessment.premium_pct is not None:
                results["with_nav_data"] += 1
                premiums.append(assessment.premium_pct)
                
                # دسته‌بندی
                analysis = BubbleAnalysis.categorize(assessment.premium_pct)
                category = analysis["category"]
                if category in results["categories"]:
                    results["categories"][category].append({
                        "symbol": assessment.symbol,
                        "premium_pct": assessment.premium_pct,
                        "final_score": assessment.final_score,
                        "recommendation_label": assessment.recommendation_label
                    })

        if premiums:
            results["statistics"] = {
                "avg_premium": round(sum(premiums) / len(premiums), 2),
                "max_premium": round(max(premiums), 2),
                "min_premium": round(min(premiums), 2),
                "bubble_count": len([p for p in premiums if p > 2]),
                "neutral_count": len([p for p in premiums if -2 <= p <= 2]),
                "discount_count": len([p for p in premiums if p < -2]),
            }
            results["summary"] = BubbleAnalysis._generate_summary(results["statistics"])
        
        return results

    @staticmethod
    def _generate_summary(stats: Dict[str, Any]) -> str:
        """خلاصه وضعیت بازار."""
        bubble = stats.get("bubble_count", 0)
        neutral = stats.get("neutral_count", 0)
        discount = stats.get("discount_count", 0)
        
        if bubble > discount:
            return "⚠️ بازار در وضعیت اورقیمتی - بیشتر صندوق‌ها حباب دارند"
        elif discount > bubble:
            return "🎯 فرصت‌های خریدی - بیشتر صندوق‌ها تخفیف دارند"
        else:
            return "⚪ بازار متعادل - تخصیص مناسب حباب و تخفیف"

    @staticmethod
    def get_top_opportunities(assessments: List[Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        بهترین فرصت‌های خرید (تخفیف بیشتر + امتیاز بالاتر).
        
        Args:
            assessments: لیست FundAssessment
            limit: تعداد نتایج
            
        Returns:
            لیست صندوق‌های با تخفیف و امتیاز خوب
        """
        opportunities = []
        for a in assessments:
            if a.premium_pct is not None and a.premium_pct < -2:
                opportunities.append({
                    "symbol": a.symbol,
                    "name": a.name,
                    "premium_pct": round(a.premium_pct, 2),
                    "final_score": round(a.final_score, 1),
                    "recommendation_label": a.recommendation_label,
                    "score_rank": a.rank or 999
                })
        
        # مرتب‌سازی: تخفیف بیشتر و امتیاز بالاتر
        opportunities.sort(key=lambda x: (-abs(x["premium_pct"]), -x["final_score"]))
        return opportunities[:limit]

    @staticmethod
    def get_warning_bubbles(assessments: List[Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        صندوق‌های با حباب شدید (احتیاط لازم).
        
        Args:
            assessments: لیست FundAssessment
            limit: تعداد نتایج
            
        Returns:
            لیست صندوق‌های با حباب بیشتر
        """
        warnings = []
        for a in assessments:
            if a.premium_pct is not None and a.premium_pct > 2:
                warnings.append({
                    "symbol": a.symbol,
                    "name": a.name,
                    "premium_pct": round(a.premium_pct, 2),
                    "final_score": round(a.final_score, 1),
                    "recommendation_label": a.recommendation_label,
                    "risk_level": "شدید" if a.premium_pct > 5 else "متوسط"
                })
        
        # مرتب‌سازی: حباب بیشتر
        warnings.sort(key=lambda x: -x["premium_pct"])
        return warnings[:limit]
