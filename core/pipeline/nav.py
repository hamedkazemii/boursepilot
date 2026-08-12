"""
NAV / Premium-Discount Engine — تحلیل NAV و پرمیوم/دیسکانت.

اصل: price/NAV timestamp alignment mandatory
محاسبه فقط زمانی انجام شود که timestampها aligned باشند.
""" 

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from core.pipeline.fund_identity import FundIdentity, FundType
from core.pipeline.data_quality import DataQualityGate
from core.history.repository import HistoryRepository
from services.providers.base import MarketDataProvider
from services.providers.models import NavData, SymbolQuote

logger = logging.getLogger(__name__)


class AlignmentStatus(str, Enum):
    """وضعیت alignment price و NAV"""
    ALIGNED = "aligned"           # تفاضل زمانی در حد مجاز
    MISALIGNED = "misaligned"     # تفاضل زمانی زیاد
    PRICE_MISSING = "price_missing"
    NAV_MISSING = "nav_missing"
    BOTH_MISSING = "both_missing"
    UNKNOWN = "unknown"


class PremiumDiscountCategory(str, Enum):
    """دسته‌بندی پرمیوم/دیسکانت"""
    DEEP_DISCOUNT = "deep_discount"     # < -5%
    DISCOUNT = "discount"               # -5% to -1%
    NEAR_PAR = "near_par"               # -1% to +1%
    PREMIUM = "premium"                 # +1% to +5%
    HIGH_PREMIUM = "high_premium"       # +5% to +15%
    EXTREME_PREMIUM = "extreme_premium" # > +15%
    UNAVAILABLE = "unavailable"


@dataclass
class NAVFact:
    """مشاهده مستقیم NAV"""
    name: str
    value: Any
    method: str
    formula: str
    inputs: dict
    timestamp: datetime
    freshness: str
    source: str
    confidence: float
    methodology_version: str = "v1"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "method": self.method,
            "formula": self.formula,
            "inputs": self.inputs,
            "timestamp": self.timestamp.isoformat(),
            "freshness": self.freshness,
            "source": self.source,
            "confidence": self.confidence,
            "methodology_version": self.methodology_version,
        }


@dataclass
class NAVAnalysis:
    """تحلیل NAV/پرمیوم"""
    name: str
    value: Any
    reasoning: str
    fact_refs: list[str]
    confidence: float
    methodology_version: str = "v1"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "reasoning": self.reasoning,
            "fact_refs": self.fact_refs,
            "confidence": self.confidence,
            "methodology_version": self.methodology_version,
        }


@dataclass
class NAVModuleResult:
    """نتیجه ماژول NAV"""
    module_name: str = "nav"
    facts: list[NAVFact] = field(default_factory=list)
    analyses: list[NAVAnalysis] = field(default_factory=list)
    overall_confidence: float = 0.0
    price_timestamp: Optional[datetime] = None
    nav_timestamp: Optional[datetime] = None
    alignment_seconds: Optional[int] = None
    alignment_status: AlignmentStatus = AlignmentStatus.UNKNOWN

    def add_fact(self, fact: NAVFact) -> None:
        self.facts.append(fact)

    def add_analysis(self, analysis: NAVAnalysis) -> None:
        self.analyses.append(analysis)

    def finalize(self) -> None:
        if not self.analyses:
            self.overall_confidence = 0.0
            return
        confs = [a.confidence for a in self.analyses if a.confidence > 0]
        if not confs:
            self.overall_confidence = 0.0
            return
        self.overall_confidence = sum(confs) / len(confs)


class NAVEngine:
    """موتور محاسبه NAV و پرمیوم/دیسکانت"""

    METHODOLOGY_VERSION = "v1"
    MAX_ALIGNMENT_SECONDS = 300  # 5 minutes max difference
    IDEAL_ALIGNMENT_SECONDS = 60  # ideal: within 1 minute

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        repository: Optional[HistoryRepository] = None,
        data_quality_gate: Optional[DataQualityGate] = None,
        fund_identity_manager: Optional[Any] = None,
    ):
        self.provider = provider
        self.repository = repository
        self.data_quality_gate = data_quality_gate
        self.fund_identity_manager = fund_identity_manager

    def _is_applicable(self, fund_type: FundType) -> bool:
        """بررسی applicability"""
        if self.fund_identity_manager:
            return self.fund_identity_manager.is_applicable("nav", fund_type)
        return True

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        *,
        request_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        اجرای تحلیل NAV/Premium-Discount.
        
        Returns:
            dict با فکت‌ها، تحلیل‌ها و metadata alignment
        """
        rid = request_id or f"nav_{symbol}_{datetime.now().timestamp()}"
        logger.info(f"[{rid}] NAVEngine analyze: {symbol}")

        result = NAVModuleResult()

        if not self._is_applicable(fund_identity.fund_type):
            result.add_analysis(NAVAnalysis(
                name="premium_discount",
                value="not_applicable",
                reasoning=f"محاسبه NAV برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return self._format_result(result, rid, symbol, fund_identity.fund_type.value)

        # Fetch price and NAV
        price_data = None
        nav_data = None

        if self.provider:
            try:
                price_data = self.provider.get_symbol(symbol)
                if hasattr(price_data, 'last_price') and price_data.last_price:
                    # SymbolQuote has date and time fields
                    if price_data.date and price_data.time:
                        result.price_timestamp = datetime.strptime(
                            f"{price_data.date} {price_data.time}", "%Y-%m-%d %H:%M:%S"
                        )
                    else:
                        result.price_timestamp = datetime.now()
            except Exception as e:
                logger.warning(f"[{rid}] Failed to fetch price: {e}")

            try:
                nav_data = self.provider.get_nav(symbol)
                # Check for ANY nav value to set timestamp
                has_nav = (hasattr(nav_data, 'redeem_nav') and nav_data.redeem_nav is not None) or \
                          (hasattr(nav_data, 'issue_nav') and nav_data.issue_nav is not None)
                if has_nav:
                    # NavData has date and time fields
                    if nav_data.date and nav_data.time:
                        result.nav_timestamp = datetime.strptime(
                            f"{nav_data.date} {nav_data.time}", "%Y-%m-%d %H:%M:%S"
                        )
                    else:
                        result.nav_timestamp = datetime.now()
            except Exception as e:
                logger.warning(f"[{rid}] Failed to fetch NAV: {e}")

        # Check alignment
        self._check_alignment(result)

        # If aligned, calculate premium/discount
        if result.alignment_status == AlignmentStatus.ALIGNED:
            self._calculate_premium_discount(result, price_data, nav_data, rid)
        else:
            self._handle_misalignment(result, price_data, nav_data, rid)

        result.finalize()
        return self._format_result(result, rid, symbol, fund_identity.fund_type.value)

    def _check_alignment(self, result: NAVModuleResult) -> None:
        """بررسی alignment بین price و NAV timestamps"""
        if result.price_timestamp is None and result.nav_timestamp is None:
            result.alignment_status = AlignmentStatus.BOTH_MISSING
            result.alignment_seconds = None
            return

        if result.price_timestamp is None:
            result.alignment_status = AlignmentStatus.PRICE_MISSING
            result.alignment_seconds = None
            return

        if result.nav_timestamp is None:
            result.alignment_status = AlignmentStatus.NAV_MISSING
            result.alignment_seconds = None
            return

        # Both exist - check difference
        diff = abs((result.price_timestamp - result.nav_timestamp).total_seconds())
        result.alignment_seconds = int(diff)

        if diff <= self.MAX_ALIGNMENT_SECONDS:
            result.alignment_status = AlignmentStatus.ALIGNED
        else:
            result.alignment_status = AlignmentStatus.MISALIGNED

    def _calculate_premium_discount(
        self,
        result: NAVModuleResult,
        price_data: Optional[SymbolQuote],
        nav_data: Optional[NavData],
        rid: str,
    ) -> None:
        """محاسبه پرمیوم/دیسکانت"""
        
        # Use redeem_nav (back/ redemption price) as primary NAV
        nav_value = None
        if nav_data and hasattr(nav_data, 'redeem_nav') and nav_data.redeem_nav:
            nav_value = nav_data.redeem_nav
        elif nav_data and hasattr(nav_data, 'issue_nav') and nav_data.issue_nav:
            nav_value = nav_data.issue_nav

        price_value = None
        if price_data and hasattr(price_data, 'last_price') and price_data.last_price:
            price_value = price_data.last_price

        if nav_value is None or price_value is None:
            result.add_analysis(NAVAnalysis(
                name="premium_discount",
                value=PremiumDiscountCategory.UNAVAILABLE.value,
                reasoning="قیمت یا NAV در دسترس نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        # Calculate premium/discount
        premium_discount_pct = ((price_value - nav_value) / nav_value) * 100

        # Add facts
        result.add_fact(NAVFact(
            name="last_price",
            value=round(price_value, 2),
            method="direct",
            formula="BRS last_price",
            inputs={"symbol": "from_provider"},
            timestamp=result.price_timestamp or datetime.now(),
            freshness="fresh",
            source="BRS",
            confidence=0.95,
        ))

        result.add_fact(NAVFact(
            name="redeem_nav",
            value=round(nav_value, 2),
            method="direct",
            formula="BRS redeem_nav",
            inputs={"symbol": "from_provider"},
            timestamp=result.nav_timestamp or datetime.now(),
            freshness="fresh",
            source="BRS",
            confidence=0.95,
        ))

        result.add_fact(NAVFact(
            name="premium_discount_pct",
            value=round(premium_discount_pct, 2),
            method="calculation",
            formula="(price - NAV) / NAV * 100",
            inputs={"price": price_value, "nav": nav_value},
            timestamp=datetime.now(),
            freshness="fresh",
            source="Calculated",
            confidence=0.9,
        ))

        result.add_fact(NAVFact(
            name="alignment_seconds",
            value=result.alignment_seconds,
            method="timestamp_diff",
            formula="abs(price_timestamp - nav_timestamp)",
            inputs={
                "price_ts": result.price_timestamp.isoformat() if result.price_timestamp else None,
                "nav_ts": result.nav_timestamp.isoformat() if result.nav_timestamp else None,
            },
            timestamp=datetime.now(),
            freshness="realtime",
            source="Calculated",
            confidence=1.0,
        ))

        # Categorize
        category = self._categorize_premium_discount(premium_discount_pct)

        # Determine reasoning
        if premium_discount_pct < 0:
            reasoning = f"دیسکانت {abs(premium_discount_pct):.2f}%: قیمت بازار کمتر از NAV است"
        else:
            reasoning = f"پرمیوم {premium_discount_pct:.2f}%: قیمت بازار بیشتر از NAV است"

        result.add_analysis(NAVAnalysis(
            name="premium_discount",
            value=category.value,
            reasoning=reasoning,
            fact_refs=["last_price", "redeem_nav", "premium_discount_pct", "alignment_seconds"],
            confidence=0.85,
        ))

        # Add category interpretation
        result.add_analysis(NAVAnalysis(
            name="category_interpretation",
            value=self._interpret_category(category, premium_discount_pct),
            reasoning=f"دسته: {category.value}",
            fact_refs=["premium_discount_pct"],
            confidence=0.8,
        ))

        # Add alignment quality
        if result.alignment_seconds <= self.IDEAL_ALIGNMENT_SECONDS:
            align_quality = "excellent"
            align_reason = f"زمان‌بندی عالی: تفاضل {result.alignment_seconds}s"
        elif result.alignment_seconds <= self.MAX_ALIGNMENT_SECONDS:
            align_quality = "acceptable"
            align_reason = f"زمان‌بندی قابل قبول: تفاضل {result.alignment_seconds}s"
        else:
            align_quality = "poor"
            align_reason = f"زمان‌بندی ضعیف: تفاضل {result.alignment_seconds}s"

        result.add_analysis(NAVAnalysis(
            name="alignment_quality",
            value=align_quality,
            reasoning=align_reason,
            fact_refs=["alignment_seconds"],
            confidence=1.0,
        ))

    def _handle_misalignment(
        self,
        result: NAVModuleResult,
        price_data: Optional[SymbolQuote],
        nav_data: Optional[NavData],
        rid: str,
    ) -> None:
        """مدیریت misalignment"""
        
        if result.alignment_status == AlignmentStatus.MISALIGNED:
            reason = f"تفاضل زمانی price/NAV ({result.alignment_seconds}s) بیش از حد مجاز ({self.MAX_ALIGNMENT_SECONDS}s)"
        elif result.alignment_status == AlignmentStatus.PRICE_MISSING:
            reason = "قیمت بازار در دسترس نیست"
        elif result.alignment_status == AlignmentStatus.NAV_MISSING:
            reason = "NAV در دسترس نیست"
        elif result.alignment_status == AlignmentStatus.BOTH_MISSING:
            reason = "هم قیمت و هم NAV در دسترس نیستند"
        else:
            reason = "وضعیت alignment ناشناخته"

        result.add_fact(NAVFact(
            name="alignment_status",
            value=result.alignment_status.value,
            method="check",
            formula="alignment check",
            inputs={
                "price_ts": result.price_timestamp.isoformat() if result.price_timestamp else None,
                "nav_ts": result.nav_timestamp.isoformat() if result.nav_timestamp else None,
                "alignment_seconds": result.alignment_seconds,
            },
            timestamp=datetime.now(),
            freshness="realtime",
            source="Calculated",
            confidence=1.0,
        ))

        result.add_analysis(NAVAnalysis(
            name="premium_discount",
            value=PremiumDiscountCategory.UNAVAILABLE.value,
            reasoning=reason,
            fact_refs=["alignment_status"],
            confidence=0.0,
        ))

    def _categorize_premium_discount(self, pct: float) -> PremiumDiscountCategory:
        """دسته‌بندی پرمیوم/دیسکانت"""
        if pct < -5:
            return PremiumDiscountCategory.DEEP_DISCOUNT
        elif pct < -1:
            return PremiumDiscountCategory.DISCOUNT
        elif pct <= 1:
            return PremiumDiscountCategory.NEAR_PAR
        elif pct <= 5:
            return PremiumDiscountCategory.PREMIUM
        elif pct <= 15:
            return PremiumDiscountCategory.HIGH_PREMIUM
        else:
            return PremiumDiscountCategory.EXTREME_PREMIUM

    def _interpret_category(self, category: PremiumDiscountCategory, pct: float) -> str:
        """تفسیر دسته‌بندی"""
        interpretations = {
            PremiumDiscountCategory.DEEP_DISCOUNT: "دیسکانت عمیق - احتمال ارزشیابی ناکافی یا ریسک بالا",
            PremiumDiscountCategory.DISCOUNT: "دیسکانت متوسط - قیمت زیر NAV",
            PremiumDiscountCategory.NEAR_PAR: "نزدیک برابر - قیمت بازار ~= NAV",
            PremiumDiscountCategory.PREMIUM: "پرمیوم متوسط - تقاضای بالا",
            PremiumDiscountCategory.HIGH_PREMIUM: "پرمیوم بالا - احتمال حباب قیمتی",
            PremiumDiscountCategory.EXTREME_PREMIUM: "پرمیوم فوق‌العاده - ریسک تصحیح بالا",
            PremiumDiscountCategory.UNAVAILABLE: "قابل محاسبه نیست",
        }
        return interpretations.get(category, "نامشخص")

    def _format_result(
        self,
        result: NAVModuleResult,
        rid: str,
        symbol: str,
        fund_type: str,
    ) -> dict[str, Any]:
        return {
            "symbol": symbol,
            "request_id": rid,
            "generated_at": datetime.now().isoformat(),
            "fund_type": fund_type,
            "module": result.module_name,
            "facts": [f.to_dict() for f in result.facts],
            "analyses": [a.to_dict() for a in result.analyses],
            "overall_confidence": result.overall_confidence,
            "alignment_status": result.alignment_status.value,
            "alignment_seconds": result.alignment_seconds,
            "price_timestamp": result.price_timestamp.isoformat() if result.price_timestamp else None,
            "nav_timestamp": result.nav_timestamp.isoformat() if result.nav_timestamp else None,
            "methodology_version": self.METHODOLOGY_VERSION,
        }


if __name__ == "__main__":
    print("NAVEngine module loaded successfully")