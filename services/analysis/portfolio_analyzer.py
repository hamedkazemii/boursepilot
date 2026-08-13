"""
Portfolio Analysis — تحلیل هوشمند سبد کاربر برای برند صندوقچی.

خروجی (دو سطح):
LEVEL 1 — تحلیل تک‌تک دارایی‌ها (هر holding: قیمت/NAV/حباب/بازده/ریسک/KODAL/نقاط قوت)
LEVEL 2 — تحلیل کل سبد (تمرکز/تنوع/نوسان/افت/هم‌جهتی/مواجهه حباب)
+ پیشنهادهای آگاهانه (Actionable, بدون سیگنال قطعی خرید/فروش)

اصل داده:
- هر مقداری که BRS ارائه می‌کند (last_price, NAV, volume, ...) همان استفاده می‌شود.
- فقط شاخص‌هایی که API ارائه نمی‌کند (Bubble, RSI, MACD, Volatility, Drawdown,
  Trend, Momentum, Concentration, Correlation) محاسبه می‌شوند.
- اگر داده‌ای نباشد → «نامشخص» نمایش داده می‌شود، نه صفر.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

from core.database.connection import get_database
from services.analysis.fund_deepdive import FundDeepDiveBuilder, FundDeepDive
from services.discovery.universe_store import get_valid_fund
from services.providers.factory import get_market_data_provider

logger = logging.getLogger(__name__)


@dataclass
class PortfolioHolding:
    """یک نگهدارنده در سبد — شامل تحلیل مستقل همان صندوق."""
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
    """تحلیل کامل سبد — دو سطح + پیشنهادها."""
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
    avg_bubble_na_count: int = 0
    avg_momentum: float = 0.0
    avg_momentum_na_count: int = 0
    avg_volatility_20: float = 0.0
    avg_drawdown_90: float = 0.0
    risk_score: float = 0.0
    co_movement: str = ""
    co_movement_details: str = ""

    # ۴. پیشنهادات
    suggestions: list[str] = field(default_factory=list)

    # متا
    generated_at: str = ""
    data_quality: str = "complete"


class PortfolioAnalyzer:
    """موتور تحلیل سبد — از FundDeepDiveBuilder برای تحلیل هر صندوق استفاده می‌کند."""

    def __init__(self, db=None):
        self.db = db or get_database()
        self.deepdive_builder = FundDeepDiveBuilder(db)
        self.provider = get_market_data_provider()

    def analyze_portfolio(self, user_id: int, portfolio_id: int) -> PortfolioAnalysis:
        """تحلیل کامل یک سبد: LEVEL 1 (هر دارایی) + LEVEL 2 (کل سبد)."""
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

        # قیمت‌های فعلی — مستقیم از BRS (Source of Truth)
        symbols = [item["symbol"] for item in items]
        quotes = {}
        for sym in symbols:
            try:
                q = self.provider.get_symbol(sym)
                quotes[sym] = q
            except Exception as e:
                logger.warning("Failed to get quote for %s: %s", sym, e)

        # LEVEL 1 — تحلیل هر نگهدارنده
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

            # تحلیل اختصاصی همین صندوق (Deep Dive)
            dive = self.deepdive_builder.build(sym)

            holding = PortfolioHolding(
                symbol=sym,
                name=dive.name,
                quantity=item["quantity"],
                avg_cost=item["avg_cost"],
                current_price=current_price,
                current_value=current_value,
                weight_pct=0,  # بعداً محاسبه می‌شود
                unrealized_pnl=pnl,
                unrealized_pnl_pct=pnl_pct,
                deep_dive=dive,
            )
            analysis.holdings.append(holding)

        if not analysis.holdings:
            analysis.data_quality = "no_prices"
            return analysis

        # محاسبه وزن‌ها و جمع‌ها — از داده واقعی
        total_value = sum(h.current_value for h in analysis.holdings)
        total_cost = sum(h.quantity * h.avg_cost for h in analysis.holdings)

        for h in analysis.holdings:
            h.weight_pct = (h.current_value / total_value * 100) if total_value > 0 else 0

        analysis.total_value = total_value
        analysis.total_cost = total_cost
        analysis.total_pnl = total_value - total_cost
        analysis.total_pnl_pct = (analysis.total_pnl / total_cost * 100) if total_cost > 0 else 0
        analysis.holdings_count = len(analysis.holdings)

        # LEVEL 2 — تحلیل ترکیب
        self._analyze_composition(analysis)

        # پیشنهادها
        self._generate_suggestions(analysis)

        return analysis

    # ------------------------------------------------------------------
    # LEVEL 2 — تحلیل ترکیب کل سبد
    # ------------------------------------------------------------------

    def _analyze_composition(self, analysis: PortfolioAnalysis) -> None:
        """تحلیل ترکیب سبد: تمرکز واقعی، تنوع، حباب، ریسک، هم‌جهتی."""
        if not analysis.holdings:
            return

        # تنوع: تعداد صندوق‌های با وزن معنادار (>5%)
        significant = [h for h in analysis.holdings if h.weight_pct >= 5]
        analysis.diversification_score = min(len(significant) * 15, 100)

        # تمرکز — اعداد واقعی
        weights = sorted([h.weight_pct for h in analysis.holdings], reverse=True)
        max_weight = weights[0] if weights else 0
        top_2_weight = sum(weights[:2])
        top_3_weight = sum(weights[:3])
        total = sum(weights) or 1

        if max_weight > 50:
            analysis.concentration_risk = "بسیار بالا"
            analysis.concentration_details = (
                f"{analysis.holdings[weights.index(max_weight)].symbol} {max_weight:.0f}٪ از ارزش سبد را تشکیل می‌دهد"
            )
        elif top_2_weight > 70:
            analysis.concentration_risk = "بالا"
            analysis.concentration_details = (
                f"دو صندوق اول {top_2_weight:.0f}٪ از ارزش سبد را در اختیار دارند"
            )
        elif top_3_weight > 70:
            analysis.concentration_risk = "متوسط به بالا"
            analysis.concentration_details = (
                f"سه صندوق اول {top_3_weight:.0f}٪ از ارزش سبد را تشکیل می‌دهند"
            )
        else:
            analysis.concentration_risk = "مناسب"
            analysis.concentration_details = (
                f"توزیع نسبتاً متعادل — سه صندوق اول {top_3_weight:.0f}٪ از ارزش سبد"
            )

        # میانگین حباب — فقط از دارایی‌هایی که NAV دارند
        bubbles = [
            h.deep_dive.bubble_pct for h in analysis.holdings
            if h.deep_dive and h.deep_dive.bubble_pct is not None
        ]
        analysis.avg_bubble = sum(bubbles) / len(bubbles) if bubbles else 0.0
        analysis.avg_bubble_na_count = len(analysis.holdings) - len(bubbles)

        # میانگین مومنتوم — فقط از دارایی‌هایی که داده دارند
        momentums = [
            h.deep_dive.momentum_score for h in analysis.holdings
            if h.deep_dive and h.deep_dive.momentum_score is not None
        ]
        analysis.avg_momentum = sum(momentums) / len(momentums) if momentums else 0.0
        analysis.avg_momentum_na_count = len(analysis.holdings) - len(momentums)

        # میانگین نوسان و افت — از داده واقعی fund_indicators
        vols = [
            h.deep_dive.volatility_20 for h in analysis.holdings
            if h.deep_dive and h.deep_dive.volatility_20 is not None
        ]
        analysis.avg_volatility_20 = sum(vols) / len(vols) if vols else 0.0

        draws = [
            h.deep_dive.max_drawdown_90 for h in analysis.holdings
            if h.deep_dive and h.deep_dive.max_drawdown_90 is not None
        ]
        analysis.avg_drawdown_90 = sum(draws) / len(draws) if draws else 0.0

        # هم‌جهتی دارایی‌ها — بر اساس بازده‌های روزانه مشترک
        analysis.co_movement, analysis.co_movement_details = self._calc_co_movement(analysis)

        # امتیاز ریسک کلی — مبتنی بر داده واقعی (نه generic)
        risk_factors = []

        if analysis.concentration_risk in ("بسیار بالا", "بالا"):
            risk_factors.append(30)
        elif analysis.concentration_risk == "متوسط به بالا":
            risk_factors.append(15)

        if bubbles:
            avg_b = analysis.avg_bubble
            if avg_b > 10:
                risk_factors.append(25)
            elif avg_b > 5:
                risk_factors.append(15)
            elif avg_b < -5:
                risk_factors.append(-10)

        if momentums:
            if analysis.avg_momentum < 30:
                risk_factors.append(20)
            elif analysis.avg_momentum > 60:
                risk_factors.append(-10)

        if vols and analysis.avg_volatility_20 > 0:
            # نوسان بالا → ریسک بیشتر
            if analysis.avg_volatility_20 > 3.0:
                risk_factors.append(20)
            elif analysis.avg_volatility_20 > 1.5:
                risk_factors.append(10)

        if draws and analysis.avg_drawdown_90 < -15:
            risk_factors.append(15)
        elif draws and analysis.avg_drawdown_90 < -8:
            risk_factors.append(10)

        if analysis.total_pnl_pct < -20:
            risk_factors.append(15)

        if "هم‌جهت" in analysis.co_movement and "بالا" in analysis.co_movement:
            risk_factors.append(15)

        analysis.risk_score = max(0, min(100, 50 + sum(risk_factors)))

    def _calc_co_movement(self, analysis: PortfolioAnalysis) -> tuple[str, str]:
        """بررسی هم‌جهتی دارایی‌ها — از بازده‌های روزانه مشترک تاریخچه."""
        if len(analysis.holdings) < 2:
            return "نامشخص", "برای بررسی هم‌جهتی حداقل دو صندوق لازم است."

        # دریافت سری بازده روزانه هر holding از history
        series = {}
        with self.db.transaction() as conn:
            for h in analysis.holdings:
                fund_id = self._fund_id_for_symbol(h.symbol)
                if not fund_id:
                    continue
                rows = conn.execute("""
                    SELECT trade_date, close_price FROM history
                    WHERE fund_id = ? AND close_price IS NOT NULL
                    ORDER BY trade_date DESC LIMIT 120
                """, (fund_id,)).fetchall()
                prices = [r["close_price"] for r in rows]
                if len(prices) < 20:
                    continue
                # بازده‌های روزانه (فرمول ساده، از داده واقعی)
                rets = [
                    (prices[i] - prices[i + 1]) / prices[i + 1]
                    for i in range(len(prices) - 1)
                ]
                series[h.symbol] = rets[:60]

        if len(series) < 2:
            return "نامشخص", "تاریخچه کافی برای محاسبه هم‌جهتی موجود نیست."

        # میانگین همبستگی pairwise
        symbols = list(series.keys())
        corrs = []
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                a, b = series[symbols[i]], series[symbols[j]]
                n = min(len(a), len(b))
                if n < 10:
                    continue
                corr = self._pearson(a[:n], b[:n])
                corrs.append(corr)

        if not corrs:
            return "نامشخص", "داده کافی برای محاسبه همبستگی وجود ندارد."

        avg_corr = sum(corrs) / len(corrs)
        pairs = len(corrs)

        if avg_corr > 0.7:
            return (
                "بالا",
                f"میانگین همبستگی بازده روزانه {avg_corr:.2f} — دارایی‌ها عمدتاً هم‌جهت حرکت می‌کنند؛ "
                f"بنابراین تعداد صندوق‌ها بیشتر از تنوع واقعی است."
            )
        elif avg_corr > 0.4:
            return (
                "متوسط",
                f"میانگین همبستگی بازده روزانه {avg_corr:.2f} — تنوع نسبی بین دارایی‌ها وجود دارد."
            )
        else:
            return (
                "پایین",
                f"میانگین همبستگی بازده روزانه {avg_corr:.2f} — دارایی‌ها تا حدی مستقل حرکت می‌کنند."
            )

    @staticmethod
    def _pearson(a: list[float], b: list[float]) -> float:
        """همبستگی پیرسون بین دو سری."""
        n = len(a)
        if n < 2:
            return 0.0
        ma = sum(a) / n
        mb = sum(b) / n
        cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        va = sum((x - ma) ** 2 for x in a)
        vb = sum((y - mb) ** 2 for y in b)
        if va == 0 or vb == 0:
            return 0.0
        return cov / (va ** 0.5 * vb ** 0.5)

    def _fund_id_for_symbol(self, symbol: str) -> Optional[int]:
        """دریافت fund_id برای یک نماد — از funds (با fallback به fund_universe)."""
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id FROM funds WHERE symbol = ? AND is_active = 1", (symbol,)
            ).fetchone()
            if row:
                return row["id"]
            fund = get_valid_fund(symbol)
            if fund:
                row = conn.execute(
                    "SELECT id FROM funds WHERE isin = ? AND is_active = 1", (fund.isin,)
                ).fetchone()
                if row:
                    return row["id"]
        return None

    # ------------------------------------------------------------------
    # پیشنهادهای آگاهانه
    # ------------------------------------------------------------------

    def _generate_suggestions(self, analysis: PortfolioAnalysis) -> None:
        """تولید پیشنهادهای Actionable — هر پیشنهاد یک REASON واقعی دارد."""
        suggestions = []

        # تمرکز — با عدد واقعی
        if analysis.concentration_risk in ("بسیار بالا", "بالا"):
            suggestions.append(
                f"⚠️ ریسک تمرکز: {analysis.concentration_details}. "
                "بررسی کاهش وزن این صندوق‌ها یا افزودن صندوق از کلاس‌های دارایی متفاوت پیشنهاد می‌شود."
            )

        # حباب بالا — نام صندوق‌ها
        high_bubble = [
            h for h in analysis.holdings
            if h.deep_dive and h.deep_dive.bubble_pct is not None and h.deep_dive.bubble_pct > 10
        ]
        if high_bubble:
            names = "، ".join(f"{h.symbol} ({h.deep_dive.bubble_pct:+.1f}٪)" for h in high_bubble[:3])
            suggestions.append(
                f"🔴 حباب بالا: {names} بالاتر از NAV معامله می‌شوند؛ "
                "بررسی دلیل فاصله از NAV و ریسک اصلاح قیمت توصیه می‌شود."
            )

        # زیر NAV — فرصت نظارتی
        low_bubble = [
            h for h in analysis.holdings
            if h.deep_dive and h.deep_dive.bubble_pct is not None and h.deep_dive.bubble_pct < -5
        ]
        if low_bubble:
            names = "، ".join(f"{h.symbol} ({h.deep_dive.bubble_pct:+.1f}٪)" for h in low_bubble[:3])
            suggestions.append(
                f"🔵 زیر NAV: {names} پایین‌تر از ارزش دارایی معامله می‌شوند؛ "
                "بررسی علت و احتمال بازگشت به NAV قابل توجه است."
            )

        # مومنتوم ضعیف — با داده واقعی
        low_momentum = [
            h for h in analysis.holdings
            if h.deep_dive and h.deep_dive.momentum_score is not None
            and h.deep_dive.momentum_score < 30
        ]
        if low_momentum:
            names = "، ".join(h.symbol for h in low_momentum[:3])
            suggestions.append(
                f"📉 مومنتوم ضعیف: {names} مومنتوم پایین دارند؛ بررسی روند و علت ضعف توصیه می‌شود."
            )

        # هم‌جهتی بالا
        if analysis.co_movement == "بالا":
            suggestions.append(
                f"🔄 ریسک هم‌جهتی: {analysis.co_movement_details} "
                "افزودن دارایی از کلاس‌های متفاوت (طلا/سهام/درآمد ثابت) می‌تواند تنوع واقعی را افزایش دهد."
            )

        # تنوع کم
        if analysis.diversification_score < 40:
            suggestions.append(
                f"📊 تنوع محدود است (امتیاز: {analysis.diversification_score:.0f}/100). "
                "افزودن صندوق از کلاس‌های دارایی مختلف به کاهش ریسک کمک می‌کند."
            )

        # نوسان بالا
        if analysis.avg_volatility_20 > 3.0:
            suggestions.append(
                f"📈 نوسان سبد بالا است (میانگین نوسان ۲۰ روزه: {analysis.avg_volatility_20:.1f}٪). "
                "برای سبدهای کم‌ریسک، بررسی ترکیب با صندوق‌های درآمد ثابت پیشنهاد می‌شود."
            )

        # افت عمیق
        if analysis.avg_drawdown_90 < -15:
            suggestions.append(
                f"📉 افت اخیر سبد قابل توجه است (میانگین افت ۹۰ روزه: {analysis.avg_drawdown_90:.1f}٪). "
                "بازبینی استراتژی و اندازه‌گیری ریسک پیشنهاد می‌شود."
            )

        # سود/زیان کل
        if analysis.total_pnl_pct < -15:
            suggestions.append(
                f"📉 ضرر کل سبد: {analysis.total_pnl_pct:.1f}٪. "
                "بازبینی استراتژی و بررسی وزن‌های هدف توصیه می‌شود."
            )
        elif analysis.total_pnl_pct > 20:
            suggestions.append(
                f"🟢 سود کل سبد: {analysis.total_pnl_pct:+.1f}٪. "
                "به‌روزرسانی وزن‌های هدف و مدیریت ریسک سود توصیه می‌شود."
            )

        if not suggestions:
            suggestions.append(
                "✅ سبد در وضعیت نسبتاً متعادل است. ادامه نظارت منظم توصیه می‌شود."
            )

        analysis.suggestions = suggestions


# ----------------------------------------------------------------------
# Formatter — خروجی برند صندوقچی
# ----------------------------------------------------------------------

def _fmt_money(v: Optional[float]) -> str:
    return f"{v:,.0f}" if v is not None else "—"


def _pct(v: Optional[float], signed: bool = False) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}٪" if signed else f"{v:.2f}٪"


def format_portfolio_analysis_brand(analysis: PortfolioAnalysis) -> str:
    """فرمت خروجی تحلیل سبد — اول تحلیل، نه Overview.

    ترتیب: نتیجه → تحلیل تک‌تک → تحلیل کل → ریسک‌ها → نقاط قوت → پیشنهادها
    """
    if analysis.data_quality == "empty":
        return "📭 سبد شما خالی است. ابتدا صندوق اضافه کنید."

    if analysis.data_quality == "no_prices":
        return "❌ نمی‌توان قیمت‌های فعلی را دریافت کرد. بعداً تلاش کنید."

    lines = []

    # ================= Level 1 — تحلیل تک‌تک دارایی‌ها =================
    lines.append("📊 تحلیل سبد: " + analysis.portfolio_name)
    lines.append("")
    lines.append("## ۱️⃣ تحلیل صندوق‌ها")

    for i, h in enumerate(analysis.holdings, 1):
        d = h.deep_dive
        lines.append("")
        lines.append(f"### {i}. {h.name} ({h.symbol})")

        # FACT — داده واقعی بازار
        lines.append("📌 واقعیت‌ها:")
        lines.append(f"   ⚖️ وزن: {h.weight_pct:.1f}٪ | تعداد: {h.quantity:,.0f} واحد")
        lines.append(f"   💵 بهای تمام‌شده: {_fmt_money(h.avg_cost)} | قیمت فعلی: {_fmt_money(h.current_price)}")
        pnl_emoji = "🟢" if h.unrealized_pnl >= 0 else "🔴"
        lines.append(f"   {pnl_emoji} سود/زیان: {_fmt_money(h.unrealized_pnl)} ({_pct(h.unrealized_pnl_pct, signed=True)})")

        # NAV و حباب — از BRS
        if d:
            if d.nav_redeem is not None or d.nav_issue is not None:
                nav_val = d.nav_redeem if d.nav_redeem is not None else d.nav_issue
                lines.append(f"   🏦 NAV: {_fmt_money(nav_val)}" + (f" (تاریخ: {d.nav_date})" if d.nav_date else ""))
            if d.bubble_pct is not None:
                bub_emoji = "🔴" if d.bubble_pct > 10 else "🟡" if d.bubble_pct > 5 else "🟢" if d.bubble_pct > -5 else "🔵"
                lines.append(f"   {bub_emoji} حباب: {_pct(d.bubble_pct, signed=True)} — {d.bubble_label}")
            else:
                lines.append("   ⚪ حباب: نامشخص (NAV در دسترس نیست)")

            # بازده‌ها
            rets = [
                ("۱ روز", d.ret_1d), ("۵ روز", d.ret_5d), ("۲۰ روز", d.ret_20d),
                ("۶۰ روز", d.ret_60d), ("۹۰ روز", d.ret_90d),
            ]
            ret_parts = []
            for label, val in rets:
                if val is not None:
                    emoji = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                    ret_parts.append(f"{emoji} {label}: {_pct(val, signed=True)}")
            if ret_parts:
                lines.append("   📈 بازده‌ها: " + " | ".join(ret_parts))
            else:
                lines.append("   📈 بازده‌ها: داده ناکافی")

            # ANALYSIS — برداشت تحلیلی
            strengths = []
            concerns = []
            if d.bubble_pct is not None:
                if d.bubble_pct < -2:
                    strengths.append("قیمت زیر NAV")
                elif d.bubble_pct > 10:
                    concerns.append(f"حباب بالا ({d.bubble_pct:+.1f}٪)")
            if d.rsi14 is not None:
                if d.rsi14 < 35:
                    strengths.append("RSI در محدوده اشباع فروش")
                elif d.rsi14 > 70:
                    concerns.append("RSI در محدوده اشباع خرید")
            if d.momentum_score is not None:
                if d.momentum_score > 60:
                    strengths.append("مومنتوم قوی")
                elif d.momentum_score < 30:
                    concerns.append("مومنتوم ضعیف")
            if d.trend_score is not None:
                if d.trend_score > 60:
                    strengths.append("روند صعودی")
                elif d.trend_score < 40:
                    concerns.append("روند نزولی")
            if d.volatility_20 is not None and d.volatility_20 > 3.0:
                concerns.append(f"نوسان بالا ({d.volatility_20:.1f}٪)")
            if d.max_drawdown_90 is not None and d.max_drawdown_90 < -15:
                concerns.append(f"افت عمیق ۹۰ روزه ({d.max_drawdown_90:.1f}٪)")

            if strengths:
                lines.append("   ✅ نقاط قوت: " + "، ".join(strengths))
            if concerns:
                lines.append("   ⚠️ قابل بررسی: " + "، ".join(concerns))

            # KODAL — FACT + اثر احتمالی
            if d.codal_disclosures:
                lines.append("   📰 کدال:")
                for disc in d.codal_disclosures[:2]:
                    title = (disc.get("title") or "بدون عنوان")[:70]
                    date = (disc.get("published_at") or "")[:10]
                    imp = disc.get("importance", "low")
                    imp_emoji = "🔴" if imp == "high" else "🟡" if imp == "medium" else "🟢"
                    cat = disc.get("category", "other")
                    cat_fa = {
                        "financial_report": "گزارش مالی",
                        "general_assembly": "مجمع عمومی",
                        "capital_change": "تغییر سرمایه",
                        "dividend": "تقسیم سود",
                        "board_change": "تغییر هیئت",
                    }.get(cat, "سایر")
                    lines.append(f"      {imp_emoji} [{cat_fa}] {date} — {title}")
                if len(d.codal_disclosures) > 2:
                    lines.append(f"      ... و {len(d.codal_disclosures) - 2} اطلاعیه دیگر")
                # ANALYSIS — اثر احتمالی (تفکیک از FACT)
                high_imp = [x for x in d.codal_disclosures if x.get("importance") == "high"]
                if high_imp:
                    lines.append(
                        "      💡 تحلیل: وجود اطلاعیه‌های با اهمیت بالا (مثل گزارش مالی یا تغییر سرمایه) "
                        "می‌تواند برای ارزیابی وضعیت صندوق قابل توجه باشد."
                    )
            else:
                lines.append("   📰 کدال: اطلاعیه مهمی یافت نشد")

    # ================= Level 2 — تحلیل کل سبد =================
    lines.append("")
    lines.append("## ۲️⃣ تحلیل کلی سبد")
    lines.append(f"📦 تعداد صندوق: {analysis.holdings_count}")
    lines.append(f"💰 ارزش کل: {_fmt_money(analysis.total_value)} | بهای تمام‌شده: {_fmt_money(analysis.total_cost)}")
    pnl_emoji = "🟢" if analysis.total_pnl >= 0 else "🔴"
    lines.append(f"{pnl_emoji} سود/زیان کل: {_fmt_money(analysis.total_pnl)} ({_pct(analysis.total_pnl_pct, signed=True)})")
    lines.append("")

    # تمرکز — عدد واقعی
    lines.append(f"⚠️ تمرکز: {analysis.concentration_risk} — {analysis.concentration_details}")

    # تنوع
    if analysis.diversification_score >= 70:
        lines.append(f"📊 تنوع: {analysis.diversification_score:.0f}/100 — ✅ تنوع مناسب")
    elif analysis.diversification_score >= 40:
        lines.append(f"📊 تنوع: {analysis.diversification_score:.0f}/100 — 🟡 تنوع متوسط")
    else:
        lines.append(f"📊 تنوع: {analysis.diversification_score:.0f}/100 — 🔴 تنوع محدود")

    # حباب
    if analysis.avg_bubble_na_count == analysis.holdings_count:
        lines.append("💎 حباب: نامشخص (NAV برای هیچ‌کدام از صندوق‌ها در دسترس نیست)")
    else:
        bub_line = f"💎 حباب میانگین: {_pct(analysis.avg_bubble, signed=True)}"
        if analysis.avg_bubble > 10:
            bub_line += " — 🔴 سبد بالای NAV"
        elif analysis.avg_bubble > 5:
            bub_line += " — 🟡 حباب ملایم"
        elif analysis.avg_bubble > -5:
            bub_line += " — 🟢 نزدیک NAV"
        else:
            bub_line += " — 🔵 زیر NAV"
        if analysis.avg_bubble_na_count > 0:
            bub_line += f" ({analysis.avg_bubble_na_count} صندوق بدون NAV)"
        lines.append(bub_line)

    # مومنتوم
    if analysis.avg_momentum_na_count == analysis.holdings_count:
        lines.append("⚡ مومنتوم: نامشخص (داده کافی موجود نیست)")
    else:
        mom_line = f"⚡ مومنتوم میانگین: {analysis.avg_momentum:.0f}/100"
        if analysis.avg_momentum > 60:
            mom_line += " — 🟢 مثبت"
        elif analysis.avg_momentum > 40:
            mom_line += " — 🟡 خنثی"
        else:
            mom_line += " — 🔴 ضعیف"
        if analysis.avg_momentum_na_count > 0:
            mom_line += f" ({analysis.avg_momentum_na_count} صندوق بدون داده)"
        lines.append(mom_line)

    # نوسان / افت — اگر داده موجود باشد
    if analysis.avg_volatility_20 > 0:
        vol_emoji = "🔴" if analysis.avg_volatility_20 > 3.0 else "🟡" if analysis.avg_volatility_20 > 1.5 else "🟢"
        lines.append(f"{vol_emoji} نوسان ۲۰ روزه میانگین: {analysis.avg_volatility_20:.2f}٪")
    else:
        lines.append("📈 نوسان: نامشخص (داده کافی موجود نیست)")
    if analysis.avg_drawdown_90 < 0:
        dd_emoji = "🔴" if analysis.avg_drawdown_90 < -15 else "🟡" if analysis.avg_drawdown_90 < -8 else "🟢"
        lines.append(f"{dd_emoji} افت ۹۰ روزه میانگین: {analysis.avg_drawdown_90:.1f}٪")
    else:
        lines.append("📉 افت: نامشخص (داده کافی موجود نیست)")

    # هم‌جهتی
    if analysis.co_movement == "بالا":
        lines.append(f"🔄 هم‌جهتی: {analysis.co_movement_details}")
    elif analysis.co_movement == "متوسط":
        lines.append(f"🔄 هم‌جهتی: {analysis.co_movement_details}")
    elif analysis.co_movement == "پایین":
        lines.append(f"🔄 هم‌جهتی: {analysis.co_movement_details}")
    else:
        lines.append(f"🔄 هم‌جهتی: {analysis.co_movement_details}")

    # ریسک کلی
    if analysis.risk_score < 30:
        lines.append(f"🛡 ریسک کلی: {analysis.risk_score:.0f}/100 — 🟢 کم‌ریسک")
    elif analysis.risk_score < 60:
        lines.append(f"🛡 ریسک کلی: {analysis.risk_score:.0f}/100 — 🟡 متوسط")
    else:
        lines.append(f"🛡 ریسک کلی: {analysis.risk_score:.0f}/100 — 🔴 پرریسک")

    # ================= پیشنهادها =================
    lines.append("")
    lines.append("## ۳️⃣ پیشنهادهای صندوقچی")
    for i, s in enumerate(analysis.suggestions, 1):
        lines.append(f"{i}. {s}")

    lines.append("")
    lines.append("———")
    lines.append("⚠️ این تحلیل برای کمک به تصمیم‌گیری است، نه سیگنال خرید/فروش.")
    lines.append("«هر تصمیم، شایسته آگاهی است.»")

    return "\n".join(lines)


def get_portfolio_analysis(user_id: int, portfolio_id: int) -> str:
    """تابع راحتی برای دریافت تحلیل سبد."""
    analyzer = PortfolioAnalyzer()
    analysis = analyzer.analyze_portfolio(user_id, portfolio_id)
    return format_portfolio_analysis_brand(analysis)
