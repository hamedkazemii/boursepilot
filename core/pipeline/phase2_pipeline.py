"""
Phase 2 Pipeline Orchestrator — Extension of Phase 1 with Technical, NAV, Fundamental.

مسیر کامل:

USER REQUEST
→ REQUEST CLASSIFICATION
→ REQUEST_ID
→ DATA QUALITY / FRESHNESS (DataQualityGate)
→ MARKET REGIME (MarketRegimeEngine)
→ FUND IDENTITY (FundIdentityManager)
→ TABLO KHANI (TabloKhaniEngine)
→ TECHNICAL (TechnicalEngine)
→ NAV / VALUATION (NAVEngine)
→ FUNDAMENTAL (FundamentalEngine)
→ EVIDENCE PACK
→ CONFIDENCE AGGREGATION
→ ANALYSIS TRACE
→ OUTPUT

فاز ۱: ۴ موتور موجود
فاز ۲: ۳ موتور جدید (Technical, NAV, Fundamental)

این فایل Phase1Pipeline را wrap می‌کند و فاز ۲ را اضافه می‌کند.
""" 

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

# Phase 1 imports
from core.pipeline.data_quality import DataQualityGate, DataQualityReport
from core.pipeline.market_regime import MarketRegimeEngine, MarketRegimeResult, MarketRegime
from core.pipeline.fund_identity import FundIdentityManager, FundIdentity
from core.snapshot.resolver import LatestSnapshotResolver
from core.snapshot.resolver import LatestSnapshotResolver
from core.snapshot.resolver import LatestSnapshotResolver
from core.pipeline.microstructure import TabloKhaniEngine, TabloKhaniReport

# Phase 2 imports
from core.pipeline.technical import TechnicalEngine
from core.pipeline.nav import NAVEngine
from core.pipeline.fundamental import FundamentalEngine

# Infrastructure
from core.history.repository import HistoryRepository
from services.providers.brs_provider import BrsProvider

# Re-export Phase 1 types
from core.pipeline.phase1_pipeline import (
    AnalysisType,
    AnalysisStatus,
    EvidenceItem,
    AnalysisTrace,
    EvidencePack,
    Phase1AnalysisResult,
    format_phase1_telegram,
)

logger = logging.getLogger(__name__)


@dataclass
class Phase2AnalysisResult:
    """نتیجه کامل تحلیل Phase 1 + 2"""
    # Phase 1 results
    phase1: Phase1AnalysisResult
    
    # Phase 2 results
    technical: Optional[dict[str, Any]] = None
    nav: Optional[dict[str, Any]] = None
    fundamental: Optional[dict[str, Any]] = None
    
    # Aggregated
    overall_confidence: float = 0.0
    data_completeness_pct: float = 0.0  # 0-100: fraction of expected Phase2 stages that succeeded
    available_phase2_stages: list[str] = field(default_factory=list)
    missing_phase2_stages: list[str] = field(default_factory=list)
    methodology_version: str = "v1"


class Phase2Pipeline:
    """Pipeline کامل Phase 1 + 2"""

    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        repository: Optional[HistoryRepository] = None,
        data_quality_gate: Optional[DataQualityGate] = None,
        market_regime_engine: Optional[MarketRegimeEngine] = None,
        fund_identity_manager: Optional[FundIdentityManager] = None,
        tablo_khani_engine: Optional[TabloKhaniEngine] = None,
        technical_engine: Optional[TechnicalEngine] = None,
        nav_engine: Optional[NAVEngine] = None,
        fundamental_engine: Optional[FundamentalEngine] = None,
    ):
        # Phase 1 engines
        self.provider = provider
        self.repository = repository
        self.latest_snapshot_resolver = LatestSnapshotResolver(self.repository.db._connect()) if self.repository else None
        self.data_quality_gate = data_quality_gate or DataQualityGate(
            provider=provider, repository=repository
        )
        self.market_regime_engine = market_regime_engine or MarketRegimeEngine(
            provider=provider, repository=repository
        )
        self.fund_identity_manager = fund_identity_manager or FundIdentityManager(
            provider=provider, repository=repository
        )
        self.tablo_khani_engine = tablo_khani_engine or TabloKhaniEngine(
            provider=provider
        )
        
        # Phase 2 engines
        self.technical_engine = technical_engine or TechnicalEngine(
            provider=provider,
            repository=repository,
            data_quality_gate=self.data_quality_gate,
            fund_identity_manager=self.fund_identity_manager,
        )
        self.nav_engine = nav_engine or NAVEngine(
            provider=provider,
            repository=repository,
            data_quality_gate=self.data_quality_gate,
            fund_identity_manager=self.fund_identity_manager,
        )
        self.fundamental_engine = fundamental_engine or FundamentalEngine(
            provider=provider,
            repository=repository,
            data_quality_gate=self.data_quality_gate,
            fund_identity_manager=self.fund_identity_manager,
        )

    def analyze_fund(
        self,
        symbol: str,
        *,
        request_id: Optional[str] = None,
        analysis_type: AnalysisType = AnalysisType.FUND,
        force_refresh: bool = False,
    ) -> Phase2AnalysisResult:
        """
        اجرای تحلیل کامل Phase 1 + 2.
        """
        # First run Phase 1
        phase1_result = self._run_phase1(
            symbol, request_id=request_id, force_refresh=force_refresh
        )
        
        # If Phase 1 failed completely, return early
        if phase1_result.status == AnalysisStatus.FAILED:
            return Phase2AnalysisResult(
                phase1=phase1_result,
                overall_confidence=0.0,
            )
        
        # Get FundIdentity from Phase 1
        fund_identity = phase1_result.fund_identity
        if not fund_identity:
            fund_identity = self.fund_identity_manager.identify(symbol)
        
        # Get latest valid market snapshot
        fund_id = self.repository.get_fund_id(fund_identity.symbol) if self.repository and fund_identity else None
        latest_snapshot = self.latest_snapshot_resolver.get_latest_snapshot(fund_id) if fund_id else None

        # Compute freshness
        analysis_time = datetime.now(timezone.utc)
        if latest_snapshot:
            freshness_data = self.latest_snapshot_resolver.compute_freshness(latest_snapshot, analysis_time)
        else:
            freshness_data = {
                'freshness': 'MISSING',
                'age_minutes': None,
                'observation_time_semantics': 'unknown',
                'snapshot_time_semantics': 'unknown'
            }

        # Run Phase 2 engines
        nav_result = None
        fundamental_result = None
        technical_result = None

        available_stages = []
        missing_stages = []
        
        # Technical Engine
        try:
            technical_result = self.technical_engine.analyze(
                symbol, fund_identity, latest_snapshot=latest_snapshot,
                freshness_data=freshness_data, request_id=phase1_result.request_id
            )
            available_stages.append("Technical")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] TechnicalEngine failed: {e}")
            missing_stages.append("Technical")
        
        # NAV Engine
        try:
            nav_result = self.nav_engine.analyze(
                symbol, fund_identity,
                request_id=phase1_result.request_id
            )
            available_stages.append("NAV")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] NAVEngine failed: {e}")
            missing_stages.append("NAV")
        
        # Fundamental Engine
        try:
            fundamental_result = self.fundamental_engine.analyze(
                symbol, fund_identity,
                request_id=phase1_result.request_id
            )
            available_stages.append("Fundamental")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] FundamentalEngine failed: {e}")
            missing_stages.append("Fundamental")
        
        # Aggregate overall confidence
        # HONEST CONFIDENCE RULE (per product contract):
        # Confidence must reflect ACTUAL available evidence.
        # Expected Phase 2 stages: Technical, NAV, Fundamental.
        # Missing stage = 0 contribution (NOT silently ignored).
        # Overall = mean over [Phase1] + [Technical, NAV, Fundamental] (missing=0).
        expected_stage_conf = []
        # Phase 1 base
        expected_stage_conf.append(phase1_result.overall_confidence if phase1_result.overall_confidence > 0 else 0.0)
        # Phase 2 stages (0 if missing/unavailable)
        expected_stage_conf.append(technical_result["overall_confidence"] if (technical_result and technical_result.get("overall_confidence", 0) > 0) else 0.0)
        expected_stage_conf.append(nav_result["overall_confidence"] if (nav_result and nav_result.get("overall_confidence", 0) > 0) else 0.0)
        expected_stage_conf.append(fundamental_result["overall_confidence"] if (fundamental_result and fundamental_result.get("overall_confidence", 0) > 0) else 0.0)

        overall_confidence = sum(expected_stage_conf) / len(expected_stage_conf) if expected_stage_conf else 0.0

        # Data completeness flag for Telegram transparency
        completeness_pct = (len(available_stages) / 3.0) * 100 if available_stages else 0.0
        
        return Phase2AnalysisResult(
            phase1=phase1_result,
            technical=technical_result,
            nav=nav_result,
            fundamental=fundamental_result,
            overall_confidence=overall_confidence,
            data_completeness_pct=completeness_pct,
            available_phase2_stages=available_stages,
            missing_phase2_stages=missing_stages,
            methodology_version="v1",
        )

    def _run_phase1(
        self,
        symbol: str,
        *,
        request_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Phase1AnalysisResult:
        """Run Phase 1 pipeline"""
        # Use the existing Phase1Pipeline internally
        from core.pipeline.phase1_pipeline import Phase1Pipeline
        phase1_pipeline = Phase1Pipeline(
            provider=self.provider,
            repository=self.repository,
        )
        return phase1_pipeline.analyze_fund(
            symbol, request_id=request_id, force_refresh=force_refresh
        )


def format_phase2_telegram(result: Phase2AnalysisResult) -> str:
    """
    Final Canonical Formatter for Sandoghچی Single Fund Analysis.
    User-facing, Human-readable, No internal leakage.
    """
    symbol = result.phase1.symbol
    lines = []
    
    # 1. HEADER & BRANDING
    lines.append(f"🔎 تحلیل صندوق «{symbol}»")
    lines.append("")
    
    # 2. MARKET STATUS & LAST UPDATE
    gen_at = result.phase1.generated_at
    lines.append("🕐 آخرین بروزرسانی:")
    lines.append(f"{gen_at.strftime('%Y/%m/%d — %H:%M')}")
    lines.append("")
    
    lines.append("📡 وضعیت بازار:")
    if result.phase1.data_quality and result.phase1.data_quality.overall_quality.value == "fresh":
        lines.append("🟢 بازار زنده")
    else:
        lines.append("🟡 آخرین داده معتبر")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    # 3. GENERAL IMAGE
    lines.append("📌 تصویر کلی")
    fund_identity = result.phase1.fund_identity
    fund_type = fund_identity.fund_type.value if fund_identity else "نامشخص"
    type_map = {"gold": "طلا", "stock": "سهامی", "fixed_income": "درآمد ثابت"}
    fund_type_fa = type_map.get(fund_type, fund_type)
    
    summary_parts = [f"این صندوق از نوع {fund_type_fa} است."]
    
    if result.phase1.market_regime:
        regime = result.phase1.market_regime.regime.value
        if regime == "RISK_ON": summary_parts.append("وضعیت کلی بازار نشان‌دهنده ریسک‌پذیری است.")
        elif regime == "RISK_OFF": summary_parts.append("احتیاط در بازار دیده می‌شود.")
        
    lines.append(" ".join(summary_parts))
    lines.append("")
    
    # 4. PRICE & NAV
    lines.append("💰 قیمت و NAV")
    price = "نامشخص"
    nav = "نامشخص"
    if result.phase1.data_quality:
        metrics = result.phase1.data_quality.metrics
        if "last_price" in metrics and metrics["last_price"].value: price = f"{metrics['last_price'].value:,.0f}"
        if "nav" in metrics and metrics["nav"].value: nav = f"{metrics['nav'].value:,.0f}"
        
    lines.append(f"قیمت فعلی: {price}")
    lines.append(f"NAV: {nav}")
    
    if result.nav and result.nav.get("analyses"):
        pd_val = "نامشخص"
        for a in result.nav["analyses"]:
            if a["name"] == "premium_discount":
                pd_val = a["value"]
                break
        
        if pd_val == "unavailable":
            lines.append("فاصله از NAV: [داده هم‌زمان کافی نیست]")
        else:
            lines.append(f"فاصله از NAV: {pd_val}")
            
    lines.append("")
    
    # 5. RECENT BEHAVIOR
    if result.technical:
        lines.append("📈 رفتار اخیر")
        tech_mods = result.technical.get("modules", {})
        
        trend_val = "نامشخص"
        if "trend" in tech_mods:
            trend_val = tech_mods["trend"].get("analyses", [{}])[0].get("value", "نامشخص")
            
        if trend_val == "up": lines.append("• روند قیمت: صعودی")
        elif trend_val == "down": lines.append("• روند قیمت: نزولی")
        else: lines.append("• روند قیمت: نشانه قطعی دیده نمی‌شود")
        
        rsi_state = "نامشخص"
        if "momentum" in tech_mods:
            for a in tech_mods["momentum"].get("analyses", []):
                if a["name"] == "rsi_state":
                    rsi_state = a["value"]
                    break
        
        if rsi_state == "oversold": lines.append("• شتاب: در محدوده اشباع فروش")
        elif rsi_state == "overbought": lines.append("• شتاب: در محدوده اشباع خرید")
        else: lines.append("• شتاب: متعادل")
        
        lines.append("")
        
    # 6. STRENGTHS & RISKS
    lines.append("🟢 نقاط قوت")
    s_count = 0
    if result.phase1.tablo_khani:
        tk = result.phase1.tablo_khani
        if tk.orderbook_pressure.value in ["strong_buy", "buy"]:
            lines.append("• تقاضای مناسب در تابلوی معاملات")
            s_count += 1
        if tk.money_flow_pressure.value == "real_buy_dominant":
            lines.append("• ورود پول حقیقی")
            s_count += 1
    
    if s_count == 0:
        lines.append("• مورد خاصی در داده‌های فعلی مشاهده نشد.")
    lines.append("")
    
    lines.append("🔴 ریسک‌ها")
    r_count = 0
    if result.nav and result.nav.get("alignment_status") == "misaligned":
        lines.append("• فاصله زمانی بین قیمت و NAV")
        r_count += 1
    if result.phase1.status.value == "partial":
        lines.append("• برخی داده‌های تحلیل ناقص است.")
        r_count += 1
        
    if r_count == 0:
        lines.append("• ریسک فوری در داده‌های تابلو دیده نمی‌شود.")
    lines.append("")
    
    # 7. SUMMARY
    lines.append("🧭 جمع‌بندی صندوقچی")
    if result.overall_confidence < 0.6:
        lines.append("با توجه به محدودیت داده‌ها، ارزیابی قطعی میسر نیست و احتیاط پیشنهاد می‌شود.")
    else:
        lines.append("وضعیت کلی صندوق متعادل ارزیابی می‌شود.")
    lines.append("")
    
    lines.append("⚠️ این تحلیل توصیه خرید یا فروش نیست.")
    lines.append("هدف، کمک به تصمیم آگاهانه است.")
    lines.append("")
    lines.append("«هر تصمیم، شایسته آگاهی است.»")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Phase2Pipeline module loaded successfully")