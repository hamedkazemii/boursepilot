"""
Phase 1 Pipeline Orchestrator — مسیر canonical تحلیل صندوق.

مسیر:

USER REQUEST
→ REQUEST CLASSIFICATION
→ REQUEST_ID
→ DATA QUALITY / FRESHNESS
→ MARKET REGIME
→ FUND IDENTITY
→ TABLO KHANI
→ EVIDENCE PACK
→ CONFIDENCE
→ ANALYSIS TRACE
→ OUTPUT

فاز ۱ فقط شامل این چهار موتور است.
موتورهای بعدی (Technical / NAV / Fundamental / KODAL / Risk / Relative / Decision Support)
بدون rebuild اضافه خواهند شد.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.pipeline.data_quality import DataQualityGate, DataQualityReport
from core.pipeline.market_regime import MarketRegimeEngine, MarketRegimeResult, MarketRegime
from core.pipeline.fund_identity import FundIdentityManager, FundIdentity
from core.pipeline.microstructure import TabloKhaniEngine, TabloKhaniReport
from core.history.repository import HistoryRepository
from services.providers.base import MarketDataProvider

logger = logging.getLogger(__name__)


class AnalysisType(str, Enum):
    """نوع تحلیل"""
    FUND = "fund"
    PORTFOLIO = "portfolio"
    MARKET = "market"


class AnalysisStatus(str, Enum):
    """وضعیت کلی تحلیل"""
    SUCCESS = "success"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass
class EvidenceItem:
    """یک مورد شواهد"""
    stage: str
    description: str
    source: str
    timestamp: datetime
    confidence: float
    methodology_version: str = "v1"
    fact_refs: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "description": self.description,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "methodology_version": self.methodology_version,
            "fact_refs": self.fact_refs,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisTrace:
    """ردیابی کامل یک اجرا"""
    request_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    symbol: str = ""
    analysis_type: AnalysisType = AnalysisType.FUND
    stages_executed: list[str] = field(default_factory=list)
    metrics_used: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    fallback_used: list[str] = field(default_factory=list)
    freshness_status: dict[str, str] = field(default_factory=dict)
    missing_data: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def add_stage(self, stage: str) -> None:
        if stage not in self.stages_executed:
            self.stages_executed.append(stage)

    def add_metric(self, metric: str) -> None:
        if metric not in self.metrics_used:
            self.metrics_used.append(metric)

    def add_source(self, source: str) -> None:
        if source not in self.sources:
            self.sources.append(source)

    def add_fallback(self, fallback: str) -> None:
        if fallback not in self.fallback_used:
            self.fallback_used.append(fallback)

    def add_missing(self, msg: str) -> None:
        self.missing_data.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_conflict(self, msg: str) -> None:
        self.conflicts.append(msg)

    def set_freshness(self, metric: str, status: str) -> None:
        self.freshness_status[metric] = status

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "symbol": self.symbol,
            "analysis_type": self.analysis_type.value,
            "stages_executed": self.stages_executed,
            "metrics_used": self.metrics_used,
            "sources": self.sources,
            "fallback_used": self.fallback_used,
            "freshness_status": self.freshness_status,
            "missing_data": self.missing_data,
            "warnings": self.warnings,
            "conflicts": self.conflicts,
        }


@dataclass
class EvidencePack:
    """بسته شواهد نهایی"""
    items: list[EvidenceItem] = field(default_factory=list)
    overall_confidence: float = 0.0
    evidence_count: int = 0

    def add(self, item: EvidenceItem) -> None:
        self.items.append(item)
        self.evidence_count += 1

    def finalize(self) -> None:
        if not self.items:
            self.overall_confidence = 0.0
            return
        # Confidence only over items with confidence > 0
        confs = [i.confidence for i in self.items if i.confidence > 0]
        if not confs:
            self.overall_confidence = 0.0
            return
        self.overall_confidence = sum(confs) / len(confs)

    def to_dict(self) -> dict:
        return {
            "items": [i.to_dict() for i in self.items],
            "overall_confidence": self.overall_confidence,
            "evidence_count": self.evidence_count,
        }


@dataclass
class Phase1AnalysisResult:
    """خروجی نهایی pipeline فاز ۱"""
    request_id: str
    symbol: str
    generated_at: datetime = field(default_factory=datetime.now)
    status: AnalysisStatus = AnalysisStatus.SUCCESS

    data_quality: Optional[DataQualityReport] = None
    market_regime: Optional[MarketRegimeResult] = None
    fund_identity: Optional[FundIdentity] = None
    tablo_khani: Optional[TabloKhaniReport] = None

    evidence: EvidencePack = field(default_factory=EvidencePack)
    trace: Optional[AnalysisTrace] = None

    overall_confidence: float = 0.0
    overall_data_quality: str = ""
    available_stages: list[str] = field(default_factory=list)
    missing_stages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "symbol": self.symbol,
            "generated_at": self.generated_at.isoformat(),
            "status": self.status.value,
            "data_quality": self.data_quality.to_dict() if self.data_quality else None,
            "market_regime": self.market_regime.to_dict() if self.market_regime else None,
            "fund_identity": self.fund_identity.to_dict() if self.fund_identity else None,
            "tablo_khani": self.tablo_khani.to_dict() if self.tablo_khani else None,
            "evidence": self.evidence.to_dict(),
            "trace": self.trace.to_dict() if self.trace else None,
            "overall_confidence": self.overall_confidence,
            "overall_data_quality": self.overall_data_quality,
            "available_stages": self.available_stages,
            "missing_stages": self.missing_stages,
        }


class Phase1Pipeline:
    """Pipeline canonical فاز ۱ — تحلیل صندوق"""

    METHODOLOGY_VERSION = "v1"

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        repository: Optional[HistoryRepository] = None,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.data_quality_gate = DataQualityGate(provider=provider, repository=repository)
        self.market_regime_engine = MarketRegimeEngine(provider=provider, repository=repository)
        self.fund_identity_manager = FundIdentityManager(provider=provider, repository=repository)
        self.tablo_khani_engine = TabloKhaniEngine(provider=provider, repository=repository)

    def analyze_fund(
        self,
        symbol: str,
        *,
        request_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Phase1AnalysisResult:
        """
        اجرای pipeline فاز ۱ برای یک صندوق.

        Args:
            symbol: نماد صندوق
            request_id: شناسه اختیاری (در غیر این صورت تولید می‌شود)
            force_refresh: نادیده گرفتن cache و refresh از BRS

        Returns:
            Phase1AnalysisResult با evidence و trace
        """
        started_at = datetime.now()
        rid = request_id or f"p1_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}"
        trace = AnalysisTrace(
            request_id=rid,
            started_at=started_at,
            symbol=symbol,
            analysis_type=AnalysisType.FUND,
        )
        logger.info(f"[{rid}] Phase1Pipeline.analyze_fund start: {symbol}")

        result = Phase1AnalysisResult(request_id=rid, symbol=symbol)
        result.trace = trace
        result.evidence = EvidencePack()

        # ============ STAGE 1: DATA QUALITY GATE ============
        try:
            trace.add_stage("DataQualityGate")
            dq_report = self.data_quality_gate.check(
                symbol,
                required_metrics=[
                    "last_price", "nav", "volume", "change_close_pct",
                    "redeem_nav", "issue_nav", "avg_volume_1m",
                    "orderbook", "money_flow", "history",
                ],
                request_id=rid,
                force_refresh=force_refresh,
            )
            result.data_quality = dq_report
            trace.sources.append("DataQualityGate")

            # Track freshness per metric
            for metric, mq in dq_report.metrics.items():
                trace.add_metric(metric)
                trace.set_freshness(metric, mq.freshness_class.value if mq.freshness_class else "unknown")
                trace.add_source(mq.source or "unknown")
                if mq.freshness_class and mq.freshness_class.value == "stale":
                    trace.add_fallback(f"stale:{metric}")

            # Add evidence
            for metric, mq in dq_report.metrics.items():
                if mq.value is not None:
                    result.evidence.add(EvidenceItem(
                        stage="DataQualityGate",
                        description=f"{metric}={mq.value}",
                        source=mq.source or "unknown",
                        timestamp=mq.fetched_at or datetime.now(),
                        confidence=0.8,  # base confidence for data quality evidence
                        methodology_version=self.METHODOLOGY_VERSION,
                        metadata={
                            "freshness": mq.freshness_class.value if mq.freshness_class else "unknown",
                            "staleness_seconds": mq.age_seconds,
                        },
                    ))

            # Quality aggregate
            dq_report.finalize()
            result.overall_data_quality = dq_report.overall_quality.value if dq_report.overall_quality else "unknown"
            logger.info(
                f"[{rid}] DataQuality: quality={result.overall_data_quality}, "
                f"conf={dq_report.overall_confidence.value}"
            )
        except Exception as e:
            logger.exception(f"[{rid}] DataQualityGate failed: {e}")
            trace.add_warning(f"DataQualityGate: {e}")

        # ============ STAGE 2: MARKET REGIME ============
        try:
            trace.add_stage("MarketRegime")
            mr_report = self.market_regime_engine.analyze(
                request_id=rid,
                force_refresh=force_refresh,
            )
            result.market_regime = mr_report
            trace.sources.append("MarketRegimeEngine")

            if mr_report:
                # Evidence per regime metric - use the evidence list from MarketRegimeResult
                for e in mr_report.evidence:
                    result.evidence.add(EvidenceItem(
                        stage="MarketRegime",
                        description=f"{e.metric}={e.value:.2f}",
                        source=e.source,
                        timestamp=e.timestamp,
                        confidence=0.7,  # confidence per evidence item
                        methodology_version=mr_report.methodology_version,
                        fact_refs=[e.metric],
                    ))

                # Contradictions as warnings
                if mr_report.contradictory_evidence:
                    for c in mr_report.contradictory_evidence:
                        trace.add_conflict(f"{c.metric}: {c.description}")

                # Market regime UNKNOWN does NOT block pipeline
                logger.info(
                    f"[{rid}] MarketRegime: regime={mr_report.regime.value}, "
                    f"conf={mr_report.confidence.value}"
                )
        except Exception as e:
            logger.exception(f"[{rid}] MarketRegimeEngine failed: {e}")
            trace.add_warning(f"MarketRegimeEngine: {e}")

        # ============ STAGE 3: FUND IDENTITY ============
        try:
            trace.add_stage("FundIdentity")
            identity = self.fund_identity_manager.identify(symbol, request_id=rid)
            result.fund_identity = identity
            trace.sources.append("FundIdentityManager")
            trace.add_metric(f"fund_type:{identity.fund_type.value}")

            result.evidence.add(EvidenceItem(
                stage="FundIdentity",
                description=f"fund_type={identity.fund_type.value}",
                source=f"FundIdentityManager/{identity.source}",
                timestamp=identity.identified_at,
                confidence=0.9 if identity.fund_type != identity.fund_type.UNKNOWN else 0.4,
                methodology_version=self.METHODOLOGY_VERSION,
                metadata={
                    "history_availability": identity.history_availability.value,
                    "applicable_metrics_count": len(identity.applicable_metrics),
                    "methodology_restrictions_count": len(identity.methodology_restrictions),
                },
            ))

            if identity.fund_type == identity.fund_type.UNKNOWN:
                trace.add_missing("fund_type")
            logger.info(
                f"[{rid}] FundIdentity: type={identity.fund_type.value}, "
                f"history={identity.history_availability.value}"
            )
        except Exception as e:
            logger.exception(f"[{rid}] FundIdentityManager failed: {e}")
            trace.add_warning(f"FundIdentityManager: {e}")

        # ============ STAGE 4: TABLO KHANI ============
        try:
            trace.add_stage("TabloKhani")

            # Fetch orderbook, money_flow, quote from provider if available
            ob = None
            mf = None
            quote = None

            if self.provider:
                try:
                    symbol_quote = self.provider.get_symbol(symbol)
                    if symbol_quote:
                        quote = symbol_quote
                        ob = symbol_quote.orderbook
                        mf = symbol_quote.money_flow
                        trace.add_source("BRSProvider")
                except Exception as e:
                    logger.debug(f"[{rid}] provider fetch failed: {e}")
                    trace.add_fallback("BRS_provider_failed")

            tk_report = self.tablo_khani_engine.analyze(
                symbol,
                request_id=rid,
                orderbook=ob,
                money_flow=mf,
                quote=quote,
            )
            result.tablo_khani = tk_report
            trace.sources.append("TabloKhaniEngine")

            # Evidence from TABLO KHANI facts
            for fact in tk_report.facts[:20]:  # cap to avoid bloat
                result.evidence.add(EvidenceItem(
                    stage="TabloKhani",
                    description=f"{fact.name}={fact.value}",
                    source=f"TabloKhani/{fact.source}",
                    timestamp=fact.timestamp,
                    confidence=fact.confidence,
                    methodology_version=self.METHODOLOGY_VERSION,
                    fact_refs=[fact.name],
                ))

            # Missing fact tracking
            if not ob or not ob.bids or not ob.asks:
                trace.add_missing("orderbook")
            if not mf:
                trace.add_missing("money_flow")
            if not quote or quote.last_price is None:
                trace.add_missing("quote.price")

            logger.info(
                f"[{rid}] TabloKhani: pressure={tk_report.orderbook_pressure.value}, "
                f"conf={tk_report.overall_confidence:.2f}"
            )
        except Exception as e:
            logger.exception(f"[{rid}] TabloKhaniEngine failed: {e}")
            trace.add_warning(f"TabloKhaniEngine: {e}")

        # ============ AGGREGATE ============
        result.evidence.finalize()
        result.overall_confidence = result.evidence.overall_confidence

        result.available_stages = list(trace.stages_executed)
        all_stages = ["DataQualityGate", "MarketRegime", "FundIdentity", "TabloKhani"]
        result.missing_stages = [s for s in all_stages if s not in trace.stages_executed]

        # Status decision
        if not trace.stages_executed:
            result.status = AnalysisStatus.FAILED
        elif result.missing_stages or trace.missing_data or trace.conflicts:
            result.status = AnalysisStatus.PARTIAL
        else:
            result.status = AnalysisStatus.SUCCESS

        trace.finished_at = datetime.now()
        elapsed = (trace.finished_at - started_at).total_seconds()
        logger.info(
            f"[{rid}] Phase1 done: status={result.status.value}, "
            f"conf={result.overall_confidence:.2f}, "
            f"stages={len(result.available_stages)}, "
            f"elapsed={elapsed:.2f}s"
        )
        return result


# ================================================================
# Telegram Output Adapter
# ================================================================

def format_phase1_telegram(result: Phase1AnalysisResult) -> str:
    """
    فرمت کردن خروجی Phase1 برای Telegram.

    مطابق brand principles صندوقچی:
    - No BUY/SELL
    - هر تصمیم، شایسته آگاهی است
    - نشان دادن evidence/confidence/trace
    - صادقانه در مورد missing data
    """
    lines: list[str] = []

    # Header
    lines.append(f"🔎 تحلیل صندوق {result.symbol}")
    lines.append(f"📋 request_id: `{result.request_id}`")
    lines.append("")

    # Status badge
    status_label = {
        "success": "✅ کامل",
        "partial": "⚠️ با داده ناقص",
        "unavailable": "❌ داده موجود نیست",
        "failed": "❌ خطا",
    }.get(result.status.value, result.status.value)
    lines.append(f"وضعیت: {status_label}")
    lines.append(f"اطمینان کلی: {result.overall_confidence:.0%}")
    lines.append("")

    # === Market Regime ===
    if result.market_regime:
        mr = result.market_regime
        regime_label = {
            "RISK_ON": "🟢 ریسک‌پذیری (RISK_ON)",
            "RISK_OFF": "🔴 ریسک‌گریزی (RISK_OFF)",
            "NEUTRAL": "⚪ خنثی",
            "TRANSITION": "🟡 گذار",
            "UNKNOWN": "⚪ نامشخص",
        }.get(mr.regime.value, mr.regime.value)
        lines.append("📊 رژیم بازار")
        lines.append(f"  • وضعیت: {regime_label}")
        lines.append(f"  • اطمینان: {mr.confidence.value}")
        if mr.evidence:
            lines.append(f"  • شواهد: {len(mr.evidence)} مورد")
        if mr.contradictory_evidence:
            lines.append(f"  • تناقضات: {'، '.join([c.metric for c in mr.contradictory_evidence[:3]])}")
        lines.append("")
    else:
        lines.append("📊 رژیم بازار")
        lines.append("  • وضعیت: نامشخص (موتور اجرا نشد)")
        lines.append("")

    # === Fund Identity ===
    if result.fund_identity:
        fi = result.fund_identity
        lines.append("🪪 هویت صندوق")
        lines.append(f"  • نوع: {fi.fund_type.value}")
        if fi.strategy:
            lines.append(f"  • استراتژی: {fi.strategy}")
        lines.append(f"  • فعال: {'بله' if fi.is_active else 'خیر'}")
        lines.append(f"  • تاریخچه: {fi.history_availability.value}")
        lines.append(f"  • متریک‌های مجاز: {len(fi.applicable_metrics)}")
        if fi.methodology_restrictions:
            lines.append(f"  • محدودیت‌های methodology: {len(fi.methodology_restrictions)}")
        lines.append("")
    else:
        lines.append("🪪 هویت صندوق")
        lines.append("  • نامشخص (موتور اجرا نشد)")
        lines.append("")

    # === Data Quality ===
    if result.data_quality:
        dq = result.data_quality
        dq_label = {
            "fresh": "🟢 تازه",
            "stale": "🟡 قدیمی‌شده",
            "missing": "🔴 ناموجود",
            "partial": "🟡 ناقص",
        }.get(dq.overall_quality.value if dq.overall_quality else "unknown", "نامشخص")
        lines.append("🛡️ کیفیت داده")
        lines.append(f"  • کیفیت کلی: {dq_label}")
        lines.append(f"  • اطمینان: {dq.overall_confidence.value}")
        metrics_with_value = [m for m, v in dq.metrics.items() if v.value is not None]
        if metrics_with_value:
            lines.append(f"  • متریک‌های بررسی‌شده: {len(metrics_with_value)}")
        else:
            lines.append("  • داده کافی برای این تحلیل موجود نیست.")
        lines.append("")

    # === Tablo Khani ===
    if result.tablo_khani:
        tk = result.tablo_khani
        pressure_label = {
            "strong_buy": "🟢 تقاضای بسیار قوی",
            "buy": "🟢 تقاضای قوی",
            "neutral": "⚪ متعادل",
            "sell": "🔴 عرضه قوی",
            "strong_sell": "🔴 عرضه بسیار قوی",
            "queue_buy": "🟢 صف خرید",
            "queue_sell": "🔴 صف فروش",
            "unknown": "⚪ نامشخص",
        }.get(tk.orderbook_pressure.value, tk.orderbook_pressure.value)
        lines.append("📋 تابلوخوانی")
        lines.append(f"  • فشار مظنه: {pressure_label}")
        if tk.spread_quality and tk.spread_quality.value != "unknown":
            spread_label = {
                "tight": "تنگ",
                "normal": "معمولی",
                "wide": "پهن",
                "crossed": "تقاطع",
            }.get(tk.spread_quality.value, tk.spread_quality.value)
            lines.append(f"  • اسپرد: {spread_label}")
        if tk.depth_quality and tk.depth_quality.value != "unknown":
            depth_label = {
                "deep": "عمیق",
                "moderate": "متوسط",
                "shallow": "سطحی",
            }.get(tk.depth_quality.value, tk.depth_quality.value)
            lines.append(f"  • عمق: {depth_label}")
        if tk.money_flow_pressure and tk.money_flow_pressure.value != "unknown":
            mf_label = {
                "real_buy_dominant": "خریداران حقیقی",
                "legal_buy_dominant": "خریداران حقوقی",
                "real_sell_dominant": "فروشندگان حقیقی",
                "legal_sell_dominant": "فروشندگان حقوقی",
                "balanced": "متعادل",
            }.get(tk.money_flow_pressure.value, tk.money_flow_pressure.value)
            lines.append(f"  • جریان پول: {mf_label}")
        if tk.queue_status and tk.queue_status != "نامشخص":
            lines.append(f"  • صف: {tk.queue_status}")
        lines.append(f"  • اطمینان تابلو: {tk.overall_confidence:.0%}")
        lines.append("")

    # === Missing Data Notice ===
    if result.trace and result.trace.missing_data:
        lines.append("⚠️ داده‌های ناموجود:")
        for m in result.trace.missing_data[:5]:
            lines.append(f"  • {m}")
        lines.append("بخشی از داده‌ها قدیمی‌شده‌اند یا در دسترس نیستند.")
        lines.append("")

    # === Evidence Summary ===
    lines.append(f"📚 شواهد: {result.evidence.evidence_count} مورد")

    # === Phase Notice ===
    lines.append("")
    lines.append("─" * 30)
    lines.append("این تحلیل شامل فاز ۱ است:")
    lines.append("DataQualityGate + MarketRegime + FundIdentity + TabloKhani")
    lines.append("فازهای بعدی (تحلیل تکنیکال/NAV/بنیادی/KODAL/ریسک) متعاقباً اضافه می‌شوند.")

    return "\n".join(lines)
