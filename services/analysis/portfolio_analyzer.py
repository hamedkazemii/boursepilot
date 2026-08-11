"""
Portfolio Analysis — تحلیل هوشمند سبد کاربر برای برند صندوقچی.

خروجی:
1. خلاصه کلی سبد
2. تحلیل جداگانه هر صندوق
3. تحلیل ترکیب کل سبد (تنوع، تمرکز، ریسک)
4. پیشنهادهای آگاهانه (نه سیگنال خرید/فروش)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from core.database.connection import get_database
from services.discovery.universe_store import get_valid_fund, get_valid_fund_symbols
from services.analysis.fund_deepdive import FundDeepDiveBuilder, FundDeepDive
from services.providers.factory import get_market_data_provider

logger = logging.getLogger(__name__)


@dataclass
class PortfolioHolding:
    """یک نگهدارنده در سبد"""
    symbol: str
    name: str
    quantity: float
    avg_cost: float
    current_price: float
    current_value: float
    weight_pct: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    
    # تحلیل صندوق
    deep_dive: Optional[FundDeepDive] = None


@dataclass
class PortfolioAnalysis:
    """تحلیل کامل سبد"""
    user_id: int
    portfolio_name: str
    
    # ۱. خلاصه کلی
    total_value: float = 0.0
    total_cost: float = 0.0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    holdings_count: int = 0
    
    # ۲. نگهدارنده‌ها
    holdings: list[PortfolioHolding] = field(default_factory=list)
    
    # ۳. تحلیل ترکیب
    diversification_score: float = 0.0
    concentration_risk: str = ""
    concentration_details: str = ""
    avg_bubble: float = 0.0
    avg_momentum: float = 0.0
    risk_score: float = 0.0
    
    # ۴. پیشنهادات
    suggestions: list[str] = field(default_factory=list)
    
    # متا
    generated_at: str = ""
    data_quality: str = "complete"


class PortfolioAnalyzer:
    """موتور تحلیل سبد"""
    
    def __init__(self, db=None):
        self.db = db or get_database()
        self.deepdive_builder = FundDeepDiveBuilder(db)
        self.provider = get_market_data_provider()
    
    def analyze_portfolio(self, user_id: int, portfolio_id: int) -> PortfolioAnalysis:
        """تحلیل کامل یک سبد"""
        # دریافت اطلاعات سبد
        with self.db.transaction() as conn:
            portfolio = conn.execute(
                "SELECT id, user_id, name FROM portfolios WHERE id = ? AND user_id = ?",
                (portfolio_id, user_id)
            ).fetchone()
            
            if not portfolio:
                raise ValueError(f"Portfolio {portfolio_id} not found for user {user_id}")
            
            items = conn.execute("""
                SELECT pi.symbol, pi.quantity, pi.avg_cost, pi.weight_target
                FROM portfolio_items pi
                WHERE pi.portfolio_id = ?
            """, (portfolio_id,)).fetchall()
        
        if not items:
            return PortfolioAnalysis(
                user_id=user_id,
                portfolio_name=portfolio["name"],
                generated_at="",
                data_quality="empty"
            )
        
        analysis = PortfolioAnalysis(
            user_id=user_id,
            portfolio_name=portfolio["name"],
        )
        
        # قیمت‌های فعلی
        symbols = [item["symbol"] for item in items]
        quotes = {}
        for sym in symbols:
            try:
                q = self.provider.get_symbol(sym)
                quotes[sym] = q
            except Exception as e:
                logger.warning("Failed to get quote for %s: %s", sym, e)
        
        # محاسبه هر نگهدارنده
        for item in items:
            sym = item["symbol"]
            quote = quotes.get(sym)
            current_price = quote.last_price if quote else None
            
            if not current_price:
                logger.warning("No price for %s, skipping", sym)
                continue
            
            current_value = item["quantity"] * current_price
            cost_basis = item["quantity"] * item["avg_cost"]
            pnl = current_value - cost_basis
            pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            # Deep dive برای تحلیل کامل
            dive = self.deepdive_builder.build(sym)
            
            holding = PortfolioHolding(
                symbol=sym,
                name=dive.name,
                quantity=item["quantity"],
                avg_cost=item["avg_cost"],
                current_price=current_price,
                current_value=current_value,
                weight_pct=0,  # محاسبه می‌شود بعد
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                deep_dive=dive,
            )
            analysis.holdings.append(holding)
        
        if not analysis.holdings:
            analysis.data_quality = "no_prices"
            return analysis
        
        # محاسبه وزن‌ها و جمع‌ها
        total_value = sum(h.current_value for h in analysis.holdings)
        total_cost = sum(h.quantity * h.avg_cost for h in analysis.holdings)
        
        for h in analysis.holdings:
            h.weight_pct = (h.current_value / total_value * 100) if total_value > 0 else 0
        
        analysis.total_value = total_value
        analysis.total_cost = total_cost
        analysis.total_pnl = total_value - total_cost
        analysis.total_pnl_pct = (analysis.total_pnl / total_cost * 100) if total_cost > 0 else 0
        analysis.holdings_count = len(analysis.holdings)
        
        # ۳. تحلیل ترکیب
        self._analyze_composition(analysis)
        
        # ۴. پیشنهادها
        self._generate_suggestions(analysis)
        
        return analysis
    
    def _analyze_composition(self, analysis: PortfolioAnalysis) -> None:
        """تحلیل ترکیب سبد"""
        if not analysis.holdings:
            return
        
        # تنوع: تعداد صندوق‌های با وزن معنادار (>5%)
        significant = [h for h in analysis.holdings if h.weight_pct >= 5]
        analysis.diversification_score = min(len(significant) * 15, 100)  # ماکزیمم 100
        
        # تمرکز: بیشترین وزن
        max_weight = max(h.weight_pct for h in analysis.holdings)
        top_3_weight = sum(sorted([h.weight_pct for h in analysis.holdings], reverse=True)[:3])
        
        if max_weight > 50:
            analysis.concentration_risk = "بسیار بالا"
            analysis.concentration_details = f"یک صندوق {max_weight:.0f}% سبد را تشکیل می‌دهد"
        elif max_weight > 30:
            analysis.concentration_risk = "بالا"
            analysis.concentration_details = f"بیشترین وزن: {max_weight:.0f}%"
        elif top_3_weight > 70:
            analysis.concentration_risk = "متوسط به بالا"
            analysis.concentration_details = f"۳ صندوق اول {top_3_weight:.0f}% سبد"
        else:
            analysis.concentration_risk = "مناسب"
            analysis.concentration_details = f"توزیع نسبتا متعادل (تاپ ۳: {top_3_weight:.0f}%)"
        
        # میانگین حباب
        bubbles = [h.deep_dive.bubble_pct for h in analysis.holdings if h.deep_dive and h.deep_dive.bubble_pct is not None]
        analysis.avg_bubble = sum(bubbles) / len(bubbles) if bubbles else 0
        
        # میانگین مومنتوم
        momentums = [h.deep_dive.momentum_score for h in analysis.holdings if h.deep_dive and h.deep_dive.momentum_score is not None]
        analysis.avg_momentum = sum(momentums) / len(momentums) if momentums else 0
        
        # امتیاز ریسک کلی
        risk_factors = []
        if analysis.concentration_risk in ("بسیار بالا", "بالا"):
            risk_factors.append(30)
        elif analysis.concentration_risk == "متوسط به بالا":
            risk_factors.append(15)
        
        if analysis.avg_bubble > 10:
            risk_factors.append(25)
        elif analysis.avg_bubble > 5:
            risk_factors.append(15)
        elif analysis.avg_bubble < -5:
            risk_factors.append(-10)  # حباب منفی = فرصت
        
        if analysis.avg_momentum < 30:
            risk_factors.append(20)
        
        if analysis.total_pnl_pct < -20:
            risk_factors.append(15)
        
        analysis.risk_score = max(0, min(100, 50 + sum(risk_factors)))
    
    def _generate_suggestions(self, analysis: PortfolioAnalysis) -> None:
        """تولید پیشنهادهای آگاهانه"""
        suggestions = []
        
        # تمرکز
        if analysis.concentration_risk in ("بسیار بالا", "بالا"):
            suggestions.append(
                f"⚠️ ریسک تمرکز: {analysis.concentration_details}. "
                "کاهش تمرکز با اضافه کردن صندوق‌های دیگر پیشنهادی است."
            )
        
        # حباب
        high_bubble = [h for h in analysis.holdings 
                      if h.deep_dive and h.deep_dive.bubble_pct and h.deep_dive.bubble_pct > 10]
        if high_bubble:
            names = ", ".join(h.symbol for h in high_bubble[:3])
            suggestions.append(
                f"🔴 صندوق‌های با حباب بالا: {names}. "
                "بررسی دلیل حباب و احتمال اصلاح قیمت توصیه می‌شود."
            )
        
        # زیر NAV
        low_bubble = [h for h in analysis.holdings 
                     if h.deep_dive and h.deep_dive.bubble_pct and h.deep_dive.bubble_pct < -5]
        if low_bubble:
            names = ", ".join(h.symbol for h in low_bubble[:3])
            suggestions.append(
                f"🔵 صندوق‌های زیر NAV: {names}. "
                "امکان خرید در قیمت جذاب‌تر وجود دارد."
            )
        
        # مومنتوم ضعیف
        low_momentum = [h for h in analysis.holdings 
                       if h.deep_dive and h.deep_dive.momentum_score is not None 
                       and h.deep_dive.momentum_score < 30]
        if low_momentum:
            names = ", ".join(h.symbol for h in low_momentum[:3])
            suggestions.append(
                f"📉 صندوق‌های با مومنتوم ضعیف: {names}. "
                "بررسی روند و احتمالی تغییر استراتژی."
            )
        
        # تنوع
        if analysis.diversification_score < 40:
            suggestions.append(
                f"📊 تنوع سبد محدود است (امتیاز: {analysis.diversification_score:.0f}/100). "
                "افزودن صندوق از کلاس‌های دارایی مختلف (طلا، سهام، درآمد ثابت) به کاهش ریسک کمک می‌کند."
            )
        
        # سود/زیان کل
        if analysis.total_pnl_pct < -15:
            suggestions.append(
                f"📉 ضرر کل سبد: {analysis.total_pnl_pct:.1f}%. "
                "بازبینی استراتژی و احتمالاً Rébalance کردن سبد ضروری است."
            )
        elif analysis.total_pnl_pct > 20:
            suggestions.append(
                f"🟢 سود کل سبد: {analysis.total_pnl_pct:+.1f}%. "
                "به‌روزرسانی وزن‌های هدف برای قفل کردن سود در نظر بگیرید."
            )
        
        if not suggestions:
            suggestions.append(
                "✅ سبد در وضعیت نسبتا متعادل است. ادامه نظارت منظم توصیه می‌شود."
            )
        
        analysis.suggestions = suggestions


def format_portfolio_analysis_brand(analysis: PortfolioAnalysis) -> str:
    """فرمت خروجی تحلیل سبد با لحن برند صندوقچی"""
    if analysis.data_quality == "empty":
        return "📭 سبد شما خالی است. ابتدا صندوق اضافه کنید."
    
    if analysis.data_quality == "no_prices":
        return "❌ نمی‌توان قیمت‌های فعلی را دریافت کرد. بعداً تلاش کنید."
    
    lines = []
    
    # Header
    lines.append(f"📊 تحلیل سبد: {analysis.portfolio_name}")
    lines.append("")
    
    # ۱. خلاصه کلی
    lines.append("## ۱️⃣ خلاصه کلی")
    lines.append(f"💰 ارزش کل: {analysis.total_value:,.0f} ریال")
    lines.append(f"💵 هزینه خرید: {analysis.total_cost:,.0f} ریال")
    pnl_emoji = "🟢" if analysis.total_pnl >= 0 else "🔴"
    lines.append(f"{pnl_emoji} سود/زیان: {analysis.total_pnl:+,.0f} ({analysis.total_pnl_pct:+.2f}%)")
    lines.append(f"📦 تعداد صندوق: {analysis.holdings_count}")
    lines.append(f"🎯 تنوع: {analysis.diversification_score:.0f}/100")
    lines.append(f"⚠️ ریسک تمرکز: {analysis.concentration_risk} — {analysis.concentration_details}")
    lines.append(f"💎 میانگین حباب: {analysis.avg_bubble:+.2f}%")
    lines.append(f"⚡ میانگین مومنتوم: {analysis.avg_momentum:.0f}/100")
    lines.append(f"🛡 امتیاز ریسک: {analysis.risk_score:.0f}/100")
    lines.append("")
    
    # ۲. تحلیل جداگانه هر صندوق
    lines.append("## ۲️⃣ تحلیل صندوق‌ها")
    for i, h in enumerate(analysis.holdings, 1):
        lines.append(f"\n### {i}. {h.name} ({h.symbol})")
        lines.append(f"   ⚖️ وزن: {h.weight_pct:.1f}% | تعداد: {h.quantity:,.0f}")
        lines.append(f"   💵 خرید: {h.avg_cost:,.0f} | 💰 فعلی: {h.current_price:,.0f}")
        pnl_emoji = "🟢" if h.unrealized_pnl >= 0 else "🔴"
        lines.append(f"   {pnl_emoji} سود/زیان: {h.unrealized_pnl:+,.0f} ({h.unrealized_pnl_pct:+.2f}%)")
        
        if h.deep_dive:
            d = h.deep_dive
            if d.bubble_pct is not None:
                bub_emoji = "🔴" if d.bubble_pct > 10 else "🟡" if d.bubble_pct > 5 else "🟢" if d.bubble_pct > -5 else "🔵"
                lines.append(f"   {bub_emoji} حباب: {d.bubble_pct:+.2f}%")
            if d.rsi14 is not None:
                rsi_emoji = "🔴" if d.rsi14 > 70 else "🟢" if d.rsi14 < 30 else "🟡"
                lines.append(f"   {rsi_emoji} RSI: {d.rsi14:.1f}")
            if d.trend_score is not None:
                lines.append(f"   📊 Trend: {d.trend_score:.0f}/100")
            if d.momentum_score is not None:
                mom_emoji = "🟢" if d.momentum_score > 60 else "🔴" if d.momentum_score < 30 else "🟡"
                lines.append(f"   {mom_emoji} Momentum: {d.momentum_score:.0f}/100")
            
            # نقاط قوت/قابل بررسی
            strengths = []
            concerns = []
            if d.bubble_pct is not None and d.bubble_pct < -2:
                strengths.append("قیمت زیر NAV")
            if d.rsi14 is not None and d.rsi14 < 35:
                strengths.append("RSI در محدوده اشباع فروش")
            if d.momentum_score is not None and d.momentum_score > 60:
                strengths.append("مومنتوم قوی")
            if d.trend_score is not None and d.trend_score > 60:
                strengths.append("روند صاعد")
            
            if d.bubble_pct is not None and d.bubble_pct > 10:
                concerns.append("حباب بالا")
            if d.rsi14 is not None and d.rsi14 > 70:
                concerns.append("RSI در محدوده اشباع خرید")
            if d.momentum_score is not None and d.momentum_score < 30:
                concerns.append("مومنتوم ضعیف")
            if d.trend_score is not None and d.trend_score < 40:
                concerns.append("روند نزولی")
            
            if strengths:
                lines.append(f"   ✅ نقاط قوت: {', '.join(strengths)}")
            if concerns:
                lines.append(f"   ⚠️ قابل بررسی: {', '.join(concerns)}")
    
    # ۳. تحلیل ترکیب کل
    lines.append("\n## ۳️⃣ تحلیل ترکیب کل سبد")
    lines.append(f"📊 تنوع: {analysis.diversification_score:.0f}/100 — ")
    if analysis.diversification_score >= 70:
        lines[-1] += "✅ تنوع مناسب"
    elif analysis.diversification_score >= 40:
        lines[-1] += "🟡 تنوع متوسط"
    else:
        lines[-1] += "🔴 تنوع محدود"
    
    lines.append(f"⚠️ تمرکز: {analysis.concentration_risk} — {analysis.concentration_details}")
    lines.append(f"💎 حباب میانگین: {analysis.avg_bubble:+.2f}% — ")
    if analysis.avg_bubble > 10:
        lines[-1] += "🔴 سبد در حباب مثبت"
    elif analysis.avg_bubble > 5:
        lines[-1] += "🟡 حباب ملایم"
    elif analysis.avg_bubble > -5:
        lines[-1] += "🟢 متعادل"
    else:
        lines[-1] += "🔵 زیر NAV (فرصت)"
    
    lines.append(f"🛡 ریسک کلی: {analysis.risk_score:.0f}/100 — ")
    if analysis.risk_score < 30:
        lines[-1] += "🟢 کم‌ریسک"
    elif analysis.risk_score < 60:
        lines[-1] += "🟡 متوسط"
    else:
        lines[-1] += "🔴 پرریسک"
    
    # ۴. پیشنهادها
    lines.append("\n## ۴️⃣ پیشنهادهای آگاهانه")
    for i, s in enumerate(analysis.suggestions, 1):
        lines.append(f"{i}. {s}")
    
    lines.append("\n———")
    lines.append("⚠️ این تحلیل برای کمک به تصمیم‌گیری است، نه سیگنال خرید/فروش.")
    lines.append("«هر تصمیم، شایسته آگاهی است.»")
    
    return "\n".join(lines)


def get_portfolio_analysis(user_id: int, portfolio_id: int) -> str:
    """تابع راحتی برای دریافت تحلیل سبد"""
    analyzer = PortfolioAnalyzer()
    analysis = analyzer.analyze_portfolio(user_id, portfolio_id)
    return format_portfolio_analysis_brand(analysis)