"""
Fund Deep Dive Analysis — تحلیل جامع صندوق برای برند صندوقچی.

هر تحلیل شامل:
1. اطلاعات پایه (نام، نماد، نوع)
2. قیمت و NAV (آخرین قیمت، NAV، حباب)
3. عملکرد (بازده‌های مختلف)
4. تکنیکال (RSI، MACD، EMA، Trend، Momentum)
5. روند تاریخی (1 ماه، 3 ماه، 1 سال)
6. کدال (آخرین اطلاعیه‌های مهم)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from core.database.connection import get_database
from services.discovery.universe_store import get_universe_store, get_valid_fund
from services.discovery.codal_storage import get_codal_storage
from services.providers.factory import get_market_data_provider
from services.providers.models import NavData, SymbolQuote

logger = logging.getLogger(__name__)


@dataclass
class FundDeepDive:
    """خروجی کامل تحلیل عمیق صندوق"""
    symbol: str
    name: str
    fund_type: str
    
    # قیمت و NAV
    last_price: Optional[float] = None
    close_price: Optional[float] = None
    yesterday_price: Optional[float] = None
    nav_issue: Optional[float] = None
    nav_redeem: Optional[float] = None
    nav_date: Optional[str] = None
    bubble_pct: Optional[float] = None
    bubble_label: str = ""
    
    # عملکرد
    ret_1d: Optional[float] = None
    ret_5d: Optional[float] = None
    ret_20d: Optional[float] = None
    ret_60d: Optional[float] = None
    ret_90d: Optional[float] = None
    ret_180d: Optional[float] = None
    ret_365d: Optional[float] = None
    
    # تکنیکال
    rsi14: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    ema200: Optional[float] = None
    trend_score: Optional[float] = None
    momentum_score: Optional[float] = None
    
    # روند تاریخی
    chart_1m: str = ""
    chart_3m: str = ""
    chart_1y: str = ""
    
    # کدال
    codal_disclosures: list[dict] = field(default_factory=list)
    
    # متا
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    data_quality: str = "complete"  # complete | partial | insufficient


class FundDeepDiveBuilder:
    """سازنده تحلیل عمیق صندوق"""
    
    def __init__(self, db=None):
        self.db = db or get_database()
        self.universe_store = get_universe_store()
        self.codal_storage = get_codal_storage()
        self.provider = get_market_data_provider()
    
    def build(self, symbol: str) -> FundDeepDive:
        """ساخت تحلیل کامل برای یک نماد"""
        # Validate universe
        fund = get_valid_fund(symbol)
        if not fund:
            logger.warning("Symbol %s not in fund_universe", symbol)
            return FundDeepDive(
                symbol=symbol,
                name="نامعتبر",
                fund_type="نامعتبر",
                data_quality="not_in_universe"
            )
        
        dive = FundDeepDive(
            symbol=fund.symbol,
            name=fund.name,
            fund_type=fund.board or fund.cs or "صندوق سرمایه‌گذاری"
        )
        
        # 1. قیمت و NAV
        self._fill_price_and_nav(dive, fund)
        
        # 2. عملکرد (از تاریخچه)
        self._fill_returns(dive, fund)
        
        # 3. تکنیکال (از اندیکاتورها)
        self._fill_technical(dive, fund)
        
        # 4. نمودارها
        self._fill_charts(dive, fund)
        
        # 5. کدال
        self._fill_codal(dive, fund)
        
        return dive
    
    def _fill_price_and_nav(self, dive: FundDeepDive, fund) -> None:
        """پر کردن قیمت، NAV و حباب"""
        try:
            quote = self.provider.get_symbol(dive.symbol)
            dive.last_price = quote.last_price
            dive.close_price = quote.close_price
            dive.yesterday_price = quote.yesterday_price
        except Exception as e:
            logger.warning("Failed to get symbol quote for %s: %s", dive.symbol, e)
        
        try:
            nav = self.provider.get_nav(dive.symbol)
            dive.nav_issue = nav.issue_nav
            dive.nav_redeem = nav.redeem_nav
            dive.nav_date = nav.date
        except Exception as e:
            logger.warning("Failed to get NAV for %s: %s", dive.symbol, e)
        
        # محاسبه حباب
        nav_ref = dive.nav_redeem or dive.nav_issue
        if nav_ref and nav_ref > 0 and dive.last_price:
            dive.bubble_pct = ((dive.last_price - nav_ref) / nav_ref) * 100
            dive.bubble_label = self._interpret_bubble(dive.bubble_pct)
    
    def _interpret_bubble(self, bubble_pct: float) -> str:
        """تفسیر حباب"""
        if bubble_pct < -5:
            return "⚠️ معامله بسیار پایین‌تر از NAV (ارزش‌گذاری جذاب)"
        elif bubble_pct < -1:
            return "🔵 زیر NAV — فرصت احتمالی"
        elif bubble_pct <= 5:
            return "🟢 نزدیک NAV — متعادل"
        elif bubble_pct <= 15:
            return "🟡 بالای NAV — حباب ملایم"
        else:
            return "🔴 حباب قوی — احتیاط"
    
    def _fill_returns(self, dive: FundDeepDive, fund) -> None:
        """محاسبه بازده‌های مختلف از تاریخچه"""
        fund_id = self._get_fund_id(fund)
        if not fund_id:
            return
        
        with self.db.transaction() as conn:
            # دریافت 400 روز اخیر برای محاسبه همه بازده‌ها
            rows = conn.execute("""
                SELECT trade_date, close_price
                FROM history
                WHERE fund_id = ? AND close_price IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT 400
            """, (fund_id,)).fetchall()
        
        if not rows or len(rows) < 2:
            dive.data_quality = "insufficient_history"
            return
        
        prices = [r["close_price"] for r in rows]
        dates = [r["trade_date"] for r in rows]
        
        # بازده‌ها
        dive.ret_1d = self._calc_return(prices, 1)
        dive.ret_5d = self._calc_return(prices, 5)
        dive.ret_20d = self._calc_return(prices, 20)
        dive.ret_60d = self._calc_return(prices, 60)
        dive.ret_90d = self._calc_return(prices, 90)
        dive.ret_180d = self._calc_return(prices, 180)
        dive.ret_365d = self._calc_return(prices, 365)
    
    def _calc_return(self, prices: list[float], days: int) -> Optional[float]:
        """محاسبه بازده N روزه"""
        if len(prices) <= days:
            return None
        return ((prices[0] - prices[days]) / prices[days]) * 100
    
    def _fill_technical(self, dive: FundDeepDive, fund) -> None:
        """پر کردن اندیکاتورهای تکنیکال از fund_indicators"""
        fund_id = self._get_fund_id(fund)
        if not fund_id:
            return
        
        with self.db.transaction() as conn:
            row = conn.execute("""
                SELECT rsi14, macd, macd_signal, ema20, ema50, ema200,
                       trend_score, momentum_score
                FROM fund_indicators
                WHERE fund_id = ?
                ORDER BY as_of_date DESC
                LIMIT 1
            """, (fund_id,)).fetchone()
        
        if row:
            dive.rsi14 = row["rsi14"]
            dive.macd = row["macd"]
            dive.macd_signal = row["macd_signal"]
            dive.ema20 = row["ema20"]
            dive.ema50 = row["ema50"]
            dive.ema200 = row["ema200"]
            dive.trend_score = row["trend_score"]
            dive.momentum_score = row["momentum_score"]
    
    def _fill_charts(self, dive: FundDeepDive, fund) -> None:
        """ساخت نمودارهای متنی برای 1 ماه، 3 ماه، 1 سال"""
        fund_id = self._get_fund_id(fund)
        if not fund_id:
            return
        
        with self.db.transaction() as conn:
            rows = conn.execute("""
                SELECT trade_date, close_price
                FROM history
                WHERE fund_id = ? AND close_price IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT 365
            """, (fund_id,)).fetchall()
        
        if not rows:
            return
        
        prices = [r["close_price"] for r in rows]
        dates = [r["trade_date"] for r in rows]
        
        # نمودار 1 ماه (30 روز)
        dive.chart_1m = self._make_sparkline(prices[:30], "1M")
        # نمودار 3 ماه (90 روز)
        dive.chart_3m = self._make_sparkline(prices[:90], "3M")
        # نمودار 1 سال (365 روز)
        dive.chart_1y = self._make_sparkline(prices[:365], "1Y")
    
    def _make_sparkline(self, prices: list[float], label: str) -> str:
        """ساخت اسپارک‌لاین متنی ساده"""
        if len(prices) < 2:
            return f"{label}: داده ناکافی"
        
        # نرمال‌سازی به 0-100
        min_p = min(prices)
        max_p = max(prices)
        if max_p == min_p:
            return f"{label}: ثابت"
        
        normalized = [(p - min_p) / (max_p - min_p) * 100 for p in prices]
        
        # کاراکترهای اسпарکلاین
        chars = "▁▂▃▄▅▆▇█"
        spark = "".join(chars[min(int(v / 100 * 7), 7)] for v in normalized)
        
        change = ((prices[0] - prices[-1]) / prices[-1]) * 100
        trend = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        
        return f"{label}: {spark} {change:+.1f}% {trend}"
    
    def _fill_codal(self, dive: FundDeepDive, fund) -> None:
        """پر کردن اطلاعیه‌های کدال"""
        try:
            disclosures = self.codal_storage.get_latest_for_symbol(dive.symbol, limit=5)
            dive.codal_disclosures = disclosures
        except Exception as e:
            logger.warning("Failed to get CODAL for %s: %s", dive.symbol, e)
    
    def _get_fund_id(self, fund) -> Optional[int]:
        """دریافت fund_id از جدول قدیمی funds"""
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id FROM funds WHERE symbol = ? AND is_active = 1",
                (fund.symbol,)
            ).fetchone()
            if row:
                return row["id"]
            
            # تلاش با ISIN
            if fund.isin:
                row = conn.execute(
                    "SELECT id FROM funds WHERE isin = ? AND is_active = 1",
                    (fund.isin,)
                ).fetchone()
                if row:
                    return row["id"]
        return None


def format_fund_deepdive_brand(dive: FundDeepDive) -> str:
    """فرمت خروجی تحلیل عمیق با لحن برند صندوقچی"""
    if dive.data_quality == "not_in_universe":
        return f"❌ نماد {dive.symbol} در'univers صندوق‌های معتبر یافت نشد."
    
    lines = []
    
    # Header
    lines.append(f"📊 {dive.name} ({dive.symbol})")
    lines.append(f"نوع: {dive.fund_type}")
    lines.append("")
    
    # ۱. اطلاعات پایه + قیمت و NAV
    lines.append("💰 ارزش‌گذاری")
    lines.append(f"قیمت بازار: {dive.last_price:,.0f}" if dive.last_price else "قیمت بازار: —")
    lines.append(f"NAV (ابطال): {dive.nav_redeem:,.0f}" if dive.nav_redeem else "NAV: —")
    if dive.bubble_pct is not None:
        lines.append(f"حباب: {dive.bubble_pct:+.2f}% — {dive.bubble_label}")
    lines.append("")
    
    # ۲. عملکرد
    lines.append("📈 عملکرد")
    returns = [
        ("1 روزه", dive.ret_1d),
        ("5 روزه", dive.ret_5d),
        ("20 روزه (1 ماه)", dive.ret_20d),
        ("60 روزه (3 ماه)", dive.ret_60d),
        ("90 روزه", dive.ret_90d),
        ("180 روزه (6 ماه)", dive.ret_180d),
        ("365 روزه (1 سال)", dive.ret_365d),
    ]
    for label, val in returns:
        if val is not None:
            emoji = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
            lines.append(f"  {emoji} {label}: {val:+.2f}%")
        else:
            lines.append(f"  ⚪ {label}: داده ناکافی")
    lines.append("")
    
    # ۳. تکنیکال
    lines.append("📊 تکنیکال")
    if dive.rsi14 is not None:
        rsi_emoji = "🔴" if dive.rsi14 > 70 else "🟢" if dive.rsi14 < 30 else "🟡"
        lines.append(f"  {rsi_emoji} RSI(14): {dive.rsi14:.1f}")
    if dive.macd is not None and dive.macd_signal is not None:
        macd_emoji = "🟢" if dive.macd > dive.macd_signal else "🔴"
        lines.append(f"  {macd_emoji} MACD: {dive.macd:.2f} / سیگنال: {dive.macd_signal:.2f}")
    if dive.ema20 is not None and dive.ema50 is not None:
        ema_emoji = "🟢" if dive.ema20 > dive.ema50 else "🔴"
        lines.append(f"  {ema_emoji} EMA: 20={dive.ema20:,.0f} / 50={dive.ema50:,.0f}")
    if dive.trend_score is not None:
        lines.append(f"  📊 Trend Score: {dive.trend_score:.0f}/100")
    if dive.momentum_score is not None:
        lines.append(f"  ⚡ Momentum Score: {dive.momentum_score:.0f}/100")
    lines.append("")
    
    # ۴. روند تاریخی
    lines.append("📉 روند تاریخی")
    if dive.chart_1m:
        lines.append(f"  {dive.chart_1m}")
    if dive.chart_3m:
        lines.append(f"  {dive.chart_3m}")
    if dive.chart_1y:
        lines.append(f"  {dive.chart_1y}")
    lines.append("")
    
    # ۵. کدال
    if dive.codal_disclosures:
        lines.append("📋 اطلاعیه‌های کدال (آخرین ۵)")
        for i, d in enumerate(dive.codal_disclosures[:3], 1):
            title = d.get("title", "بدون عنوان")[:80]
            date = d.get("published_at", "")[:10]
            imp = d.get("importance", "low")
            imp_emoji = "🔴" if imp == "high" else "🟡" if imp == "medium" else "🟢"
            cat = d.get("category", "other")
            cat_fa = {
                "financial_report": "گزارش مالی",
                "general_assembly": "مجمع عمومی",
                "capital_change": "تغییر سرمایه",
                "dividend": "تقسیم سود",
                "board_change": "تغییر هیئت",
            }.get(cat, "سایر")
            lines.append(f"  {imp_emoji} [{cat_fa}] {date} — {title}...")
        if len(dive.codal_disclosures) > 3:
            lines.append(f"  ... و {len(dive.codal_disclosures) - 3} اطلاعیه دیگر")
    else:
        lines.append("📋 اطلاعیه‌های کدال: یافت نشد")
    lines.append("")
    
    # Footer
    lines.append(f"⏱ تولید شده: {dive.generated_at[:16].replace('T', ' ')}")
    lines.append("———")
    lines.append("⚠️ این تحلیل برای کمک به تصمیم‌گیری است، نه سیگنال خرید/فروش.")
    lines.append("«هر تصمیم، شایسته آگاهی است.»")
    
    return "\n".join(lines)


def get_fund_deepdive(symbol: str) -> str:
    """تابع راحتی برای دریافت تحلیل کامل صندوق"""
    builder = FundDeepDiveBuilder()
    dive = builder.build(symbol)
    return format_fund_deepdive_brand(dive)