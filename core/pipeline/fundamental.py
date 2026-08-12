"""
Fundamental Analysis Engine — تحلیل بنیادی ماژولار بر اساس FundType.

اصل: FACT → ANALYSIS → CONFIDENCE

هر FundType متدولوژی خودش را دارد:
- EQUITY: valuation, earnings, exposure
- FIXED_INCOME: yield, duration, credit, rate sensitivity
- GOLD: gold exposure, FX exposure
- INDEX: tracking error, underlying
- LEVERAGED: leverage-aware interpretation
- UNKNOWN: only universally valid metrics
""" 

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.pipeline.fund_identity import FundIdentity, FundType
from core.pipeline.data_quality import DataQualityGate
from core.history.repository import HistoryRepository
from services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class FundamentalMetricType(str, Enum):
    """انواع متریک‌های بنیادی"""
    VALUATION = "valuation"
    YIELD = "yield"
    CREDIT = "credit"
    EXPOSURE = "exposure"
    TRACKING = "tracking"
    LEVERAGE = "leverage"
    LIQUIDITY = "liquidity"


@dataclass
class FundamentalFact:
    """مشاهده مستقیم (FACT) بنیادی"""
    name: str
    value: Any
    metric_type: FundamentalMetricType
    method: str
    formula: str
    inputs: dict
    timestamp: datetime
    freshness: str
    source: str
    confidence: float
    methodology_version: str = "v1"
    fund_type_applicable: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "method": self.method,
            "formula": self.formula,
            "inputs": self.inputs,
            "timestamp": self.timestamp.isoformat(),
            "freshness": self.freshness,
            "source": self.source,
            "confidence": self.confidence,
            "methodology_version": self.methodology_version,
            "fund_type_applicable": self.fund_type_applicable,
        }


@dataclass
class FundamentalAnalysis:
    """تحلیل/تفسیر (ANALYSIS) بنیادی"""
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
class FundamentalModuleResult:
    """نتیجه یک ماژول بنیادی"""
    module_name: str
    facts: list[FundamentalFact] = field(default_factory=list)
    analyses: list[FundamentalAnalysis] = field(default_factory=list)
    overall_confidence: float = 0.0

    def add_fact(self, fact: FundamentalFact) -> None:
        self.facts.append(fact)

    def add_analysis(self, analysis: FundamentalAnalysis) -> None:
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


class EquityFundamentalModule:
    """ماژول تحلیل بنیادی برای صندوق‌های سهامی"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="equity_fundamental")
        
        # Since we don't have direct access to earnings/financials from BRS,
        # we focus on what we CAN derive: NAV-based valuation proxies
        # and underlying holdings if available via KODAL (future)
        
        result.add_fact(FundamentalFact(
            name="equity_metrics_available",
            value=False,
            metric_type=FundamentalMetricType.VALUATION,
            method="availability_check",
            formula="Check if earnings/financial data available",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="valuation_assessment",
            value="data_unavailable",
            reasoning="داده‌های بنیادی سهامی (P/E, P/B, EPS) در دسترس نیست - نیاز بهנת‌پیدا کردن از KODAL یا پایگاه داده مالی",
            fact_refs=["equity_metrics_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class FixedIncomeFundamentalModule:
    """ماژول تحلیل بنیادی برای صندوق‌های درآمد ثابت"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="fixed_income_fundamental")
        
        # For fixed income, we can derive yield info from NAV changes
        # and duration if we have historical NAV data
        
        result.add_fact(FundamentalFact(
            name="fixed_income_metrics_available",
            value=False,
            metric_type=FundamentalMetricType.YIELD,
            method="availability_check",
            formula="Check if yield/duration/credit data available",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="yield_assessment",
            value="data_unavailable",
            reasoning="داده‌های درآمد (yield), دوره (duration), و ریسک اعتباری (credit) در دسترس نیست",
            fact_refs=["fixed_income_metrics_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class GoldFundamentalModule:
    """ماژول تحلیل بنیادی برای صندوق‌های طلایی"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="gold_fundamental")
        
        result.add_fact(FundamentalFact(
            name="gold_exposure_available",
            value=False,
            metric_type=FundamentalMetricType.EXPOSURE,
            method="availability_check",
            formula="Check if gold/FX exposure data available",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="exposure_assessment",
            value="data_unavailable",
            reasoning="داده‌های exposición به طلا و ارز در دسترس نیست - نیاز به گزارش‌های 보유ات",
            fact_refs=["gold_exposure_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class IndexFundamentalModule:
    """ماژول تحلیل بنیادی برای صندوق‌های نمادین/شاخصی"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="index_fundamental")
        
        result.add_fact(FundamentalFact(
            name="tracking_metrics_available",
            value=False,
            metric_type=FundamentalMetricType.TRACKING,
            method="availability_check",
            formula="Check if tracking error/underlying index data available",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="tracking_assessment",
            value="data_unavailable",
            reasoning="داده‌های خطای ردیابی (tracking error) و شاخص پایه در دسترس نیست",
            fact_refs=["tracking_metrics_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class LeveragedFundamentalModule:
    """ماژول تحلیل بنیادی برای صندوق‌های با اهرم"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="leveraged_fundamental")
        
        result.add_fact(FundamentalFact(
            name="leverage_metrics_available",
            value=False,
            metric_type=FundamentalMetricType.LEVERAGE,
            method="availability_check",
            formula="Check if leverage ratio/cost data available",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="leverage_assessment",
            value="data_unavailable",
            reasoning="داده‌های اهرم (leverage ratio، هزینه قرض) در دسترس نیست",
            fact_refs=["leverage_metrics_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class UniversalFundamentalModule:
    """ماژول‌های بنیادی که برای همه انواع صندوق معتبرند"""

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        provider: Optional[BrsProvider] = None,
        request_id: str = "",
    ) -> FundamentalModuleResult:
        result = FundamentalModuleResult(module_name="universal_fundamental")
        
        # Liquidity is universally applicable
        result.add_fact(FundamentalFact(
            name="liquidity_proxy_available",
            value=True,
            metric_type=FundamentalMetricType.LIQUIDITY,
            method="proxy_from_volume",
            formula="Daily turnover / AUM (when AUM available)",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="HistoryRepository/Calculated",
            confidence=0.5,  # Low confidence as proxy
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="liquidity_assessment",
            value="proxy_only",
            reasoning="تقییم نقدینگی از روی حجم معاملات (proxy) - نیاز به AUM برای محاسبه دقیق",
            fact_refs=["liquidity_proxy_available"],
            confidence=0.4,
        ))
        
        # Fund size proxy (from NAV * shares if available)
        result.add_fact(FundamentalFact(
            name="fund_size_proxy_available",
            value=False,
            metric_type=FundamentalMetricType.VALUATION,
            method="availability_check",
            formula="NAV * shares_outstanding",
            inputs={},
            timestamp=datetime.now(),
            freshness="realtime",
            source="Provider",
            confidence=1.0,
            fund_type_applicable=True,
        ))
        
        result.add_analysis(FundamentalAnalysis(
            name="size_assessment",
            value="data_unavailable",
            reasoning="اندازه صندوق (AUM) برای محاسبه دقیق نقدینگی و اثر بازار در دسترس نیست",
            fact_refs=["fund_size_proxy_available"],
            confidence=0.0,
        ))
        
        result.finalize()
        return result


class FundamentalEngine:
    """موتور تحلیل بنیادی ترکیبی"""

    METHODOLOGY_VERSION = "v1"

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
        
        self.equity_module = EquityFundamentalModule()
        self.fixed_income_module = FixedIncomeFundamentalModule()
        self.gold_module = GoldFundamentalModule()
        self.index_module = IndexFundamentalModule()
        self.leveraged_module = LeveragedFundamentalModule()
        self.universal_module = UniversalFundamentalModule()

    def _is_applicable(self, metric: str, fund_type: FundType) -> bool:
        """Check if metric is applicable for fund type"""
        if self.fund_identity_manager:
            return self.fund_identity_manager.is_applicable(metric, fund_type)
        return True

    def _get_fund_type_module(self, fund_type: FundType):
        """Get the appropriate fundamental module for fund type"""
        modules = {
            FundType.EQUITY: self.equity_module,
            FundType.FIXED_INCOME: self.fixed_income_module,
            FundType.GOLD: self.gold_module,
            FundType.INDEX: self.index_module,
            FundType.LEVERAGED: self.leveraged_module,
        }
        return modules.get(fund_type, None)

    def analyze(
        self,
        symbol: str,
        fund_identity: FundIdentity,
        *,
        request_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        اجرای تحلیل بنیادی کامل بر اساس FundType.
        """
        rid = request_id or f"fund_{symbol}_{datetime.now().timestamp()}"
        logger.info(f"[{rid}] FundamentalEngine analyze: {symbol} ({fund_identity.fund_type.value})")

        all_facts = []
        all_analyses = []
        confidences = []
        module_results = {}

        # Always run universal module - check applicability
        if self._is_applicable("liquidity", fund_identity.fund_type):
            universal_result = self.universal_module.analyze(
                symbol, fund_identity, self.provider, rid
            )
            module_results["universal"] = universal_result
            all_facts.extend(universal_result.facts)
            all_analyses.extend(universal_result.analyses)
            if universal_result.overall_confidence > 0:
                confidences.append(universal_result.overall_confidence)
        else:
            logger.info(f"[{rid}] Universal module not applicable for {fund_identity.fund_type.value}")

        # Run fund-type-specific module if applicable
        fund_type_module = self._get_fund_type_module(fund_identity.fund_type)
        if fund_type_module:
            # Check specific metrics for each fund type
            metric_map = {
                FundType.EQUITY: "valuation",
                FundType.FIXED_INCOME: "yield",
                FundType.GOLD: "exposure",
                FundType.INDEX: "tracking",
                FundType.LEVERAGED: "leverage",
            }
            specific_metric = metric_map.get(fund_identity.fund_type, "unknown")
            
            if self._is_applicable(specific_metric, fund_identity.fund_type):
                specific_result = fund_type_module.analyze(
                    symbol, fund_identity, self.provider, rid
                )
                module_results[fund_identity.fund_type.value] = specific_result
                all_facts.extend(specific_result.facts)
                all_analyses.extend(specific_result.analyses)
                if specific_result.overall_confidence > 0:
                    confidences.append(specific_result.overall_confidence)
            else:
                logger.info(f"[{rid}] {specific_metric} not applicable for {fund_identity.fund_type.value}")
        else:
            # UNKNOWN or OTHER - only universal
            logger.info(f"[{rid}] No specific module for {fund_identity.fund_type.value}, using universal only")

        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "symbol": symbol,
            "request_id": rid,
            "generated_at": datetime.now().isoformat(),
            "fund_type": fund_identity.fund_type.value,
            "modules": {
                name: {
                    "facts": [f.to_dict() for f in res.facts],
                    "analyses": [a.to_dict() for a in res.analyses],
                    "overall_confidence": res.overall_confidence,
                }
                for name, res in module_results.items()
            },
            "total_facts": len(all_facts),
            "total_analyses": len(all_analyses),
            "overall_confidence": overall_confidence,
            "methodology_version": self.METHODOLOGY_VERSION,
        }


if __name__ == "__main__":
    print("FundamentalEngine module loaded successfully")