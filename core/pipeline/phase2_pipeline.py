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
from datetime import datetime
from enum import Enum
from typing import Any, Optional

# Phase 1 imports
from core.pipeline.data_quality import DataQualityGate, DataQualityReport
from core.pipeline.market_regime import MarketRegimeEngine, MarketRegimeResult, MarketRegime
from core.pipeline.fund_identity import FundIdentityManager, FundIdentity
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
        
        # Run Phase 2 engines
        technical_result = None
        nav_result = None
        fundamental_result = None
        
        available_stages = []
        missing_stages = []
        
        # Technical Engine
        try:
            technical_result = self.technical_engine.analyze(
                symbol, fund_identity, request_id=phase1_result.request_id
            )
            available_stages.append("Technical")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] TechnicalEngine failed: {e}")
            missing_stages.append("Technical")
        
        # NAV Engine
        try:
            nav_result = self.nav_engine.analyze(
                symbol, fund_identity, request_id=phase1_result.request_id
            )
            available_stages.append("NAV")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] NAVEngine failed: {e}")
            missing_stages.append("NAV")
        
        # Fundamental Engine
        try:
            fundamental_result = self.fundamental_engine.analyze(
                symbol, fund_identity, request_id=phase1_result.request_id
            )
            available_stages.append("Fundamental")
        except Exception as e:
            logger.warning(f"[{phase1_result.request_id}] FundamentalEngine failed: {e}")
            missing_stages.append("Fundamental")
        
        # Aggregate overall confidence
        confidences = [phase1_result.overall_confidence]
        if technical_result and technical_result.get("overall_confidence", 0) > 0:
            confidences.append(technical_result["overall_confidence"])
        if nav_result and nav_result.get("overall_confidence", 0) > 0:
            confidences.append(nav_result["overall_confidence"])
        if fundamental_result and fundamental_result.get("overall_confidence", 0) > 0:
            confidences.append(fundamental_result["overall_confidence"])
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return Phase2AnalysisResult(
            phase1=phase1_result,
            technical=technical_result,
            nav=nav_result,
            fundamental=fundamental_result,
            overall_confidence=overall_confidence,
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
    فرمت کردن خروجی Phase 1 + 2 برای Telegram.
    
    بر اساس brand principles:
    - No BUY/SELL
    - هر تصمیم، شایسته آگاهی است
    - نشان دادن evidence/confidence/trace
    - صادقانه در مورد missing data
    """
    # Start with Phase 1 output
    lines = format_phase1_telegram(result.phase1).split("\n")
    
    # Remove the footer line
    footer_idx = None
    for i, line in enumerate(lines):
        if "این تحلیل شامل فاز ۱ است" in line:
            footer_idx = i
            break
    
    if footer_idx:
        lines = lines[:footer_idx]
    
    lines.append("")
    lines.append("─── فاز ۲: تحلیل تکمیلی ───")
    lines.append("")
    
    # === Technical ===
    if result.technical:
        tech = result.technical
        lines.append("📈 تحلیل تکنیکال")
        lines.append(f"  • اطمینان: {tech.get('overall_confidence', 0):.0%}")
        lines.append(f"  • ماژول‌ها: {len(tech.get('modules', {}))}")
        
        for module_name, module_data in tech.get("modules", {}).items():
            if module_data.get("analyses"):
                analyses = module_data["analyses"]
                for analysis in analyses:
                    lines.append(f"  • {module_name}/{analysis['name']}: {analysis['value']} ({analysis['confidence']:.0%})")
        lines.append("")
    
    # === NAV ===
    if result.nav:
        nav = result.nav
        lines.append("💰 NAV / پرمیوم-دیسکانت")
        lines.append(f"  • اطمینان: {nav.get('overall_confidence', 0):.0%}")
        lines.append(f"  • Alignment: {nav.get('alignment_status', 'unknown')}")
        if nav.get("alignment_seconds") is not None:
            lines.append(f"  • تفاضل زمانی: {nav['alignment_seconds']}s")
        
        for analysis in nav.get("analyses", []):
            lines.append(f"  • {analysis['name']}: {analysis['value']} ({analysis['confidence']:.0%})")
        lines.append("")
    
    # === Fundamental ===
    if result.fundamental:
        fund = result.fundamental
        lines.append("📊 تحلیل بنیادی")
        lines.append(f"  • اطمینان: {fund.get('overall_confidence', 0):.0%}")
        lines.append(f"  • ماژول‌ها: {list(fund.get('modules', {}).keys())}")
        
        for module_name, module_data in fund.get("modules", {}).items():
            for analysis in module_data.get("analyses", []):
                lines.append(f"  • {module_name}/{analysis['name']}: {analysis['value']} ({analysis['confidence']:.0%})")
        lines.append("")
    
    # Phase 2 summary
    lines.append("─── جمع‌بندی فاز ۲ ───")
    lines.append(f"مراحل موجود: {', '.join(result.available_phase2_stages) if result.available_phase2_stages else 'هیچ‌کدام'}")
    if result.missing_phase2_stages:
        lines.append(f"مراحل ناموجود: {', '.join(result.missing_phase2_stages)}")
    lines.append(f"اطمینان کلی فاز ۱+۲: {result.overall_confidence:.0%}")
    lines.append("")
    lines.append("──────────────────────────────")
    lines.append("این تحلیل شامل فاز ۱ و ۲ است:")
    lines.append("Phase 1: DataQualityGate + MarketRegime + FundIdentity + TabloKhani")
    lines.append("Phase 2: Technical + NAV + Fundamental")
    lines.append("فازهای بعدی (KODAL / Risk / Relative / Decision Support) متعاقباً اضافه می‌شوند.")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Phase2Pipeline module loaded successfully")