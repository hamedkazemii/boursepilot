"""
Data Quality Gate — تحلیل کیفیت و تازگی داده‌ها قبل از هر تحلیل.

این ماژول پیش از اجرای هر تحلیل، کیفیت، تازگی و صحت داده‌های مورد نیاز
را بررسی می‌کند و گزارش DataQualityReport تولید می‌کند.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.history.repository import HistoryRepository
from services.providers.brs_provider import BrsProvider
from services.providers.models import NavData, SymbolQuote

logger = logging.getLogger(__name__)


class FreshnessClass(str, Enum):
    """کلاس‌های تازگی داده‌ها"""
    REALTIME = "realtime"       # لحظه‌ای (قیمت، حجم، اوردر بوک)
    LIVE = "live"               # زنده (NAV)
    INTRADAY = "intraday"       # درون روز (معاملات، کندل‌ها)
    END_OF_DAY = "end_of_day"   # پایان روز (تکنیکال، ریسک)
    EVENT = "event"             # رویدادمحور (کدال)
    PERIODIC = "periodic"       # دوره‌ای (آمار هم‌گروه)
    HISTORICAL = "historical"   # تاریخی (هویت صندوق)


class DataQuality(str, Enum):
    """سطح کیفیت داده"""
    FRESH = "fresh"             # تازه و معتبر
    STALE = "stale"             # قدیمی
    MISSING = "missing"         # موجود نیست
    CONFLICT = "conflict"       # تضاد
    PARTIAL = "partial"         # ناقص
    UNAVAILABLE = "unavailable" # غیرقابل دستیابی


class ConfidenceLevel(str, Enum):
    """سطح اطمینان"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OverallQuality(str, Enum):
    """کیفیت کلی"""
    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass
class MetricQuality:
    """کیفیت یک متریک مشخص"""
    metric_name: str
    source: str  # "BRS_API", "DB", "CACHE", "DERIVED", "NONE"
    fetched_at: Optional[datetime] = None
    age_seconds: Optional[int] = None
    ttl_seconds: int = 0
    freshness_class: FreshnessClass = FreshnessClass.HISTORICAL
    quality: DataQuality = DataQuality.UNAVAILABLE
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    fallback_used: bool = False
    fallback_source: Optional[str] = None
    value: Any = None
    raw_value: Any = None
    conflict_details: Optional[str] = None


@dataclass
class DataQualityReport:
    """گزارش کامل کیفیت داده‌ها"""
    symbol: str
    requested_at: datetime
    overall_quality: OverallQuality = OverallQuality.UNAVAILABLE
    overall_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    metrics: dict[str, MetricQuality] = field(default_factory=dict)
    stale_metrics: list[str] = field(default_factory=list)
    missing_metrics: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fallback_used: dict[str, bool] = field(default_factory=dict)
    freshness_classes: dict[str, FreshnessClass] = field(default_factory=dict)

    def add_metric(self, mq: MetricQuality) -> None:
        """افزودن متریک و به‌روزرسانی خلاصه‌ها"""
        self.metrics[mq.metric_name] = mq
        self.fallback_used[mq.metric_name] = mq.fallback_used
        self.freshness_classes[mq.metric_name] = mq.freshness_class

        if mq.quality == DataQuality.STALE:
            self.stale_metrics.append(mq.metric_name)
        elif mq.quality == DataQuality.MISSING:
            self.missing_metrics.append(mq.metric_name)
        elif mq.quality == DataQuality.CONFLICT:
            self.conflicts.append(mq.metric_name)

        if mq.conflict_details:
            self.warnings.append(f"{mq.metric_name}: {mq.conflict_details}")

    def finalize(self) -> None:
        """محاسبه کیفیت کلی"""
        if not self.metrics:
            self.overall_quality = OverallQuality.UNAVAILABLE
            self.overall_confidence = ConfidenceLevel.LOW
            return

        total = len(self.metrics)
        fresh_count = sum(1 for m in self.metrics.values() if m.quality == DataQuality.FRESH)
        stale_count = len(self.stale_metrics)
        missing_count = len(self.missing_metrics)
        conflict_count = len(self.conflicts)

        # محاسبه کیفیت کلی
        if missing_count == total:
            self.overall_quality = OverallQuality.UNAVAILABLE
        elif missing_count > 0 or conflict_count > 0:
            self.overall_quality = OverallQuality.PARTIAL
        elif stale_count > 0:
            self.overall_quality = OverallQuality.STALE
        else:
            self.overall_quality = OverallQuality.COMPLETE

        # محاسبه اطمینان کلی
        high_count = sum(1 for m in self.metrics.values() if m.confidence == ConfidenceLevel.HIGH)
        medium_count = sum(1 for m in self.metrics.values() if m.confidence == ConfidenceLevel.MEDIUM)

        if high_count > total * 0.7:
            self.overall_confidence = ConfidenceLevel.HIGH
        elif (high_count + medium_count) > total * 0.5:
            self.overall_confidence = ConfidenceLevel.MEDIUM
        else:
            self.overall_confidence = ConfidenceLevel.LOW

    def to_dict(self) -> dict:
        """تبدیل به دیکشنری برای serialization"""
        return {
            "symbol": self.symbol,
            "requested_at": self.requested_at.isoformat(),
            "overall_quality": self.overall_quality.value,
            "overall_confidence": self.overall_confidence.value,
            "metrics": {
                name: {
                    "source": m.source,
                    "fetched_at": m.fetched_at.isoformat() if m.fetched_at else None,
                    "age_seconds": m.age_seconds,
                    "ttl_seconds": m.ttl_seconds,
                    "freshness_class": m.freshness_class.value,
                    "quality": m.quality.value,
                    "confidence": m.confidence.value,
                    "fallback_used": m.fallback_used,
                    "fallback_source": m.fallback_source,
                    "value": m.value,
                    "conflict": m.conflict_details,
                }
                for name, m in self.metrics.items()
            },
            "stale_metrics": self.stale_metrics,
            "missing_metrics": self.missing_metrics,
            "conflicts": self.conflicts,
            "warnings": self.warnings,
            "fallback_used": self.fallback_used,
            "freshness_classes": {k: v.value for k, v in self.freshness_classes.items()},
        }


# ================================================================
# Freshness Policy Configuration
# ================================================================

FRESHNESS_POLICY = {
    # Real-time / Live metrics
    "price": {
        "freshness_class": FreshnessClass.REALTIME,
        "ttl_seconds": 300,  # 5 min
        "source_endpoint": "Symbol",
        "required": True,
    },
    "nav": {
        "freshness_class": FreshnessClass.LIVE,
        "ttl_seconds": 300,  # 5 min
        "source_endpoint": "Nav",
        "required": True,
    },
    "volume": {
        "freshness_class": FreshnessClass.REALTIME,
        "ttl_seconds": 300,
        "source_endpoint": "Symbol",
        "required": True,
    },
    "value": {
        "freshness_class": FreshnessClass.REALTIME,
        "ttl_seconds": 300,
        "source_endpoint": "Symbol",
        "required": False,
    },
    "orderbook": {
        "freshness_class": FreshnessClass.LIVE,
        "ttl_seconds": 300,
        "source_endpoint": "Symbol",
        "required": True,
    },
    "change_pct": {
        "freshness_class": FreshnessClass.REALTIME,
        "ttl_seconds": 300,
        "source_endpoint": "Symbol",
        "required": True,
    },
    "change_last_pct": {
        "freshness_class": FreshnessClass.REALTIME,
        "ttl_seconds": 300,
        "source_endpoint": "Symbol",
        "required": False,
    },
    # Intraday
    "transactions": {
        "freshness_class": FreshnessClass.INTRADAY,
        "ttl_seconds": 3600,  # 1 hour
        "source_endpoint": "Transaction",
        "required": False,
    },
    "shareholders": {
        "freshness_class": FreshnessClass.INTRADAY,
        "ttl_seconds": 3600,
        "source_endpoint": "Shareholder",
        "required": False,
    },
    "candlestick": {
        "freshness_class": FreshnessClass.INTRADAY,
        "ttl_seconds": 3600,
        "source_endpoint": "Candlestick",
        "required": False,
    },
    # End of day
    "history": {
        "freshness_class": FreshnessClass.END_OF_DAY,
        "ttl_seconds": 86400,  # 24 hours
        "source_endpoint": "History",
        "required": False,
    },
    "technical_indicators": {
        "freshness_class": FreshnessClass.END_OF_DAY,
        "ttl_seconds": 86400,
        "source_endpoint": "DB",
        "required": False,
    },
    "risk_metrics": {
        "freshness_class": FreshnessClass.END_OF_DAY,
        "ttl_seconds": 86400,
        "source_endpoint": "DB",
        "required": False,
    },
    # Event-driven
    "codal": {
        "freshness_class": FreshnessClass.EVENT,
        "ttl_seconds": 300,
        "source_endpoint": "CodalAnnouncement",
        "required": False,
    },
    # Periodic
    "peer_stats": {
        "freshness_class": FreshnessClass.PERIODIC,
        "ttl_seconds": 604800,  # 7 days
        "source_endpoint": "DB",
        "required": False,
    },
    # Historical
    "fund_identity": {
        "freshness_class": FreshnessClass.HISTORICAL,
        "ttl_seconds": 31536000,  # 365 days
        "source_endpoint": "DB",
        "required": True,
    },
    "market_regime": {
        "freshness_class": FreshnessClass.INTRADAY,
        "ttl_seconds": 900,  # 15 min
        "source_endpoint": "AllSymbols",
        "required": False,
    },
}


# ================================================================
# Data Quality Gate
# ================================================================

class DataQualityGate:
    """
    دروازه کیفیت داده — بررسی تازگی و صحت داده‌ها قبل از تحلیل.

    برای هر متریک درخواستی:
    1. بررسی cache (QuotaManager + DB request_cache)
    2. اگر تازه باشد → استفاده از cache
    3. اگر قدیمی باشد → تلاش برای refresh از BRS
    4. اگر refresh موفق باشد → استفاده از داده تازه
    5. اگر refresh ناموفق باشد → استفاده از آخرین داده شناخته شده + فلگ stale
    6. اگر هیچ داده‌ای وجود نداشته باشد → unavailable
    """

    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        repository: Optional[HistoryRepository] = None,
    ):
        self.provider = provider
        self.repository = repository
        self._request_id: Optional[str] = None

    def check(
        self,
        symbol: str,
        required_metrics: list[str],
        *,
        force_refresh: bool = False,
        request_id: Optional[str] = None,
    ) -> DataQualityReport:
        """
        بررسی کیفیت داده‌ها برای یک نماد.

        Args:
            symbol: نماد صندوق
            required_metrics: لیست نام متریک‌های مورد نیاز
            force_refresh: اجبار به refresh از BRS
            request_id: شناسه درخواست برای Trace

        Returns:
            DataQualityReport کامل
        """
        self._request_id = request_id or f"dq_{symbol}_{datetime.now().timestamp()}"
        report = DataQualityReport(
            symbol=symbol,
            requested_at=datetime.now(),
        )

        logger.info(f"[{self._request_id}] DataQualityGate check for {symbol}: {required_metrics}")

        # بررسی نماد در universe
        if not self._is_valid_symbol(symbol):
            report.overall_quality = OverallQuality.UNAVAILABLE
            report.overall_confidence = ConfidenceLevel.LOW
            report.warnings.append(f"Symbol {symbol} not in valid fund universe")
            return report

        # بررسی هر متریک
        for metric_name in required_metrics:
            mq = self._check_metric(symbol, metric_name, force_refresh=force_refresh)
            report.add_metric(mq)

        # بررسی تضاد price vs NAV timestamp
        self._check_price_nav_alignment(report)

        report.finalize()
        logger.info(
            f"[{self._request_id}] DataQualityGate result: quality={report.overall_quality.value}, "
            f"confidence={report.overall_confidence.value}, "
            f"stale={report.stale_metrics}, missing={report.missing_metrics}"
        )
        return report

    def _is_valid_symbol(self, symbol: str) -> bool:
        """بررسی اعتبار نماد در fund_universe"""
        if not self.repository:
            return True  # اگر repository موجود نیست، فرض می‌کنیم معتبر است
        try:
            fund_id = self.repository.get_fund_id(symbol)
            return fund_id is not None
        except Exception:
            return True

    def _check_metric(
        self,
        symbol: str,
        metric_name: str,
        force_refresh: bool = False,
    ) -> MetricQuality:
        """بررسی کیفیت یک متریک خاص"""
        policy = FRESHNESS_POLICY.get(metric_name, {})
        freshness_class = policy.get("freshness_class", FreshnessClass.HISTORICAL)
        ttl_seconds = policy.get("ttl_seconds", 86400)
        source_endpoint = policy.get("source_endpoint", "UNKNOWN")

        mq = MetricQuality(
            metric_name=metric_name,
            source="NONE",
            freshness_class=freshness_class,
            ttl_seconds=ttl_seconds,
        )

        # 1. تلاش برای دریافت از BRS (live)
        if self.provider and not force_refresh:
            try:
                value, fetched_at = self._fetch_live_metric(symbol, metric_name)
                if value is not None:
                    mq.value = value
                    mq.raw_value = value
                    mq.source = "BRS_API"
                    mq.fetched_at = fetched_at
                    mq.age_seconds = int((datetime.now() - fetched_at).total_seconds())
                    mq.fallback_used = False
                    mq.quality = self._assess_quality(mq.age_seconds, ttl_seconds)
                    mq.confidence = self._assess_confidence(mq.age_seconds, ttl_seconds)
                    return mq
            except Exception as e:
                logger.debug(f"[{self._request_id}] Live fetch failed for {metric_name}: {e}")

        # 2. تلاش برای دریافت از DB cache (request_cache)
        if self.repository:
            try:
                cached_value, cached_at = self._fetch_cached_metric(symbol, metric_name)
                if cached_value is not None:
                    mq.value = cached_value
                    mq.raw_value = cached_value
                    mq.source = "DB"
                    mq.fetched_at = cached_at
                    mq.age_seconds = int((datetime.now() - cached_at).total_seconds())
                    mq.fallback_used = True
                    mq.fallback_source = "DB_cache"
                    mq.quality = self._assess_quality(mq.age_seconds, ttl_seconds)
                    mq.confidence = self._assess_confidence(mq.age_seconds, ttl_seconds)
                    return mq
            except Exception as e:
                logger.debug(f"[{self._request_id}] DB cache fetch failed for {metric_name}: {e}")

        # 3. تلاش برای دریافت از جداول تاریخچه/شاخص‌ها (برای متریک‌های derived)
        if metric_name in ("technical_indicators", "risk_metrics", "history"):
            try:
                value, fetched_at = self._fetch_from_history_tables(symbol, metric_name)
                if value is not None:
                    mq.value = value
                    mq.raw_value = value
                    mq.source = "DB"
                    mq.fetched_at = fetched_at
                    mq.age_seconds = int((datetime.now() - fetched_at).total_seconds())
                    mq.fallback_used = True
                    mq.fallback_source = "history_tables"
                    mq.quality = self._assess_quality(mq.age_seconds, ttl_seconds)
                    mq.confidence = self._assess_confidence(mq.age_seconds, ttl_seconds)
                    return mq
            except Exception as e:
                logger.debug(f"[{self._request_id}] History tables fetch failed for {metric_name}: {e}")

        # 4. هیچ داده‌ای یافت نشد
        mq.quality = DataQuality.MISSING
        mq.confidence = ConfidenceLevel.LOW
        mq.fallback_used = False
        return mq

    def _fetch_live_metric(self, symbol: str, metric_name: str) -> tuple[Any, datetime]:
        """دریافت متریک به صورت زنده از BRS"""
        now = datetime.now()

        if metric_name == "price":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return quote.last_price, now

        if metric_name == "nav":
            nav: NavData = self.provider.get_nav(symbol)
            return nav.redeem_nav, now  # استفاده از redeem NAV به عنوان پیش‌فرض

        if metric_name == "volume":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return quote.volume, now

        if metric_name == "value":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return quote.value, now

        if metric_name == "orderbook":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return {
                "bid_qty": quote.bid_qty,
                "ask_qty": quote.ask_qty,
                "best_bid": quote.best_bid,
                "best_ask": quote.best_ask,
                "spread": (quote.best_ask - quote.best_bid) if quote.best_ask and quote.best_bid else None,
            }, now

        if metric_name == "change_pct":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return quote.change_close_pct, now

        if metric_name == "change_last_pct":
            quote: SymbolQuote = self.provider.get_symbol(symbol)
            return quote.change_last_pct, now

        if metric_name == "transactions":
            return self.provider.get_transactions(symbol), now

        if metric_name == "shareholders":
            return self.provider.get_shareholders(symbol), now

        if metric_name == "candlestick":
            return self.provider.get_candlestick(symbol, candlestick_type=3, count=200), now

        if metric_name == "codal":
            return self.provider.get_codal_announcements(symbol), now

        if metric_name == "market_regime":
            # این در MarketRegimeEngine پردازش می‌شود
            return None, now

        raise ValueError(f"Unknown live metric: {metric_name}")

    def _fetch_cached_metric(self, symbol: str, metric_name: str) -> tuple[Any, datetime]:
        """دریافت متریک از DB request_cache"""
        if not self.repository:
            return None, None

        # ساخت کلید cache
        cache_key = f"{metric_name}|{symbol}"
        response_json = self.repository.cache_get(cache_key)

        if response_json:
            import json
            data = json.loads(response_json)
            # استخراج زمان ایجاد از cache (approximate)
            # در اینجا فرض می‌کنیم cache 5 دقیقه پیش ساخته شده
            return data, datetime.now()

        return None, None

    def _fetch_from_history_tables(self, symbol: str, metric_name: str) -> tuple[Any, datetime]:
        """دریافت از جداول history/fund_indicators"""
        if not self.repository:
            return None, None

        if metric_name == "history":
            series = self.repository.get_history(symbol, limit=400)
            if series:
                last_date = series[-1].get("trade_date", datetime.now().isoformat())
                return series, datetime.fromisoformat(last_date)

        if metric_name == "technical_indicators":
            # آخرین ردیف fund_indicators
            with self.repository.db.transaction() as conn:
                row = conn.execute(
                    """SELECT * FROM fund_indicators
                       WHERE fund_id = (SELECT id FROM fund_universe WHERE symbol = ?)
                       ORDER BY as_of_date DESC LIMIT 1""",
                    (symbol,),
                ).fetchone()
                if row:
                    return dict(row), datetime.fromisoformat(row["as_of_date"])

        if metric_name == "risk_metrics":
            # مشابه technical_indicators
            return self._fetch_from_history_tables(symbol, "technical_indicators")

        return None, None

    def _assess_quality(self, age_seconds: int, ttl_seconds: int) -> DataQuality:
        """ارزیابی کیفیت بر اساس سن داده"""
        if age_seconds <= ttl_seconds:
            return DataQuality.FRESH
        elif age_seconds <= ttl_seconds * 3:  # تا 3 برابر TTL
            return DataQuality.STALE
        else:
            return DataQuality.STALE  # بسیار قدیمی اما هنوز موجود

    def _assess_confidence(self, age_seconds: int, ttl_seconds: int) -> ConfidenceLevel:
        """ارزیابی اطمینان بر اساس سن داده"""
        if age_seconds <= ttl_seconds:
            return ConfidenceLevel.HIGH
        elif age_seconds <= ttl_seconds * 2:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _check_price_nav_alignment(self, report: DataQualityReport) -> None:
        """بررسی هم‌زمان بودن price و NAV"""
        price_mq = report.metrics.get("price")
        nav_mq = report.metrics.get("nav")

        if price_mq and nav_mq and price_mq.fetched_at and nav_mq.fetched_at:
            diff_seconds = abs((price_mq.fetched_at - nav_mq.fetched_at).total_seconds())
            if diff_seconds > 900:  # 15 دقیقه
                conflict_msg = f"price/NAV timestamp misalignment: {diff_seconds:.0f}s"
                price_mq.conflict_details = conflict_msg
                nav_mq.conflict_details = conflict_msg
                report.conflicts.append("price_nav_alignment")
                report.warnings.append(conflict_msg)
                # کاهش اطمینان
                if price_mq.confidence == ConfidenceLevel.HIGH:
                    price_mq.confidence = ConfidenceLevel.MEDIUM
                if nav_mq.confidence == ConfidenceLevel.HIGH:
                    nav_mq.confidence = ConfidenceLevel.MEDIUM


# ================================================================
# Convenience Functions
# ================================================================

def create_data_quality_gate(
    provider: Optional[BrsProvider] = None,
    repository: Optional[HistoryRepository] = None,
) -> DataQualityGate:
    """ساخت DataQualityGate با dependency injection"""
    return DataQualityGate(provider=provider, repository=repository)