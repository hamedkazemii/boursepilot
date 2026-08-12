"""
Technical Analysis Engine — تحلیل تکنیکال ماژولار.

اصل: FACT → ANALYSIS → CONFIDENCE

هیچ سیگنال BUY/SELL تولید نمی‌کند.
FundIdentity.is_applicable() باید برای هر متریک چک شود.
داده ناموجود → unavailable / نامشخص
""" 

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.pipeline.fund_identity import FundIdentity, FundType
from core.pipeline.data_quality import DataQualityGate
from core.history.repository import HistoryRepository
from services.providers.brs_provider import BrsProvider
from services.providers.models import SymbolQuote

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """جهت روند"""
    STRONG_UP = "strong_up"
    UP = "up"
    NEUTRAL = "neutral"
    DOWN = "down"
    STRONG_DOWN = "strong_down"
    UNKNOWN = "unknown"


class MomentumState(str, Enum):
    """وضعیت مومنتوم"""
    OVERBOUGHT = "overbought"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    OVERSOLD = "oversold"
    UNKNOWN = "unknown"


class VolatilityRegime(str, Enum):
    """رژیم نوسان"""
    VERY_LOW = "very_low"
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    VERY_HIGH = "very_high"
    UNKNOWN = "unknown"


@dataclass
class TechnicalFact:
    """یک مشاهده مستقیم (FACT) از داده‌های تکنیکال"""
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
    fund_type_applicable: bool = True

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
            "fund_type_applicable": self.fund_type_applicable,
        }


@dataclass
class TechnicalAnalysis:
    """یک تحلیل/تفسیر (ANALYSIS) بر اساس FACTها"""
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
class TechnicalModuleResult:
    """نتیجه یک ماژول تکنیکال"""
    module_name: str
    facts: list[TechnicalFact] = field(default_factory=list)
    analyses: list[TechnicalAnalysis] = field(default_factory=list)
    overall_confidence: float = 0.0

    def add_fact(self, fact: TechnicalFact) -> None:
        self.facts.append(fact)

    def add_analysis(self, analysis: TechnicalAnalysis) -> None:
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


class TrendModule:
    """ماژول تحلیل روند"""

    def __init__(self, history_repo: Optional[HistoryRepository] = None):
        self.history_repo = history_repo

    def analyze(
        self,
        symbol: str,
        prices: list[float],
        fund_type: FundType,
        identity: FundIdentity,
        request_id: str,
    ) -> TechnicalModuleResult:
        result = TechnicalModuleResult(module_name="trend")
        
        # Applicability check is done by orchestrator (TechnicalEngine)
        # Module just processes the data

        if len(prices) < 20:
            result.add_fact(TechnicalFact(
                name="sma_20",
                value=None,
                method="sma",
                formula="SMA(20) = sum(close[-20:]) / 20",
                inputs={"period": 20, "available_points": len(prices)},
                timestamp=datetime.now(),
                freshness="insufficient",
                source="HistoryRepository",
                confidence=0.0,
            ))
            result.add_analysis(TechnicalAnalysis(
                name="trend_direction",
                value=TrendDirection.UNKNOWN.value,
                reasoning="تاریخچه قیمتی ناکافی برای محاسبه SMA(20)",
                fact_refs=["sma_20"],
                confidence=0.0,
            ))
            return result

        # SMA 20
        sma_20 = statistics.mean(prices[-20:])
        # SMA 50 (if available)
        sma_50 = statistics.mean(prices[-50:]) if len(prices) >= 50 else None
        # Current price
        current_price = prices[-1]

        result.add_fact(TechnicalFact(
            name="sma_20",
            value=round(sma_20, 2),
            method="sma",
            formula="SMA(20) = sum(close[-20:]) / 20",
            inputs={"period": 20, "prices_used": 20},
            timestamp=datetime.now(),
            freshness="fresh" if len(prices) >= 20 else "stale",
            source="HistoryRepository",
            confidence=0.9,
        ))

        if sma_50 is not None:
            result.add_fact(TechnicalFact(
                name="sma_50",
                value=round(sma_50, 2),
                method="sma",
                formula="SMA(50) = sum(close[-50:]) / 50",
                inputs={"period": 50, "prices_used": 50},
                timestamp=datetime.now(),
                freshness="fresh",
                source="HistoryRepository",
                confidence=0.9,
            ))

        result.add_fact(TechnicalFact(
            name="current_price",
            value=current_price,
            method="last_price",
            formula="close[-1]",
            inputs={},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.95,
        ))

        # Trend determination
        if current_price > sma_20 * 1.02:
            if sma_50 and current_price > sma_50 * 1.02:
                direction = TrendDirection.STRONG_UP
                reasoning = "قیمت > SMA20 و > SMA50 (روند قوی صعودی)"
            else:
                direction = TrendDirection.UP
                reasoning = "قیمت > SMA20 (روند صعودی)"
        elif current_price < sma_20 * 0.98:
            if sma_50 and current_price < sma_50 * 0.98:
                direction = TrendDirection.STRONG_DOWN
                reasoning = "قیمت < SMA20 و < SMA50 (روند قوی نزولی)"
            else:
                direction = TrendDirection.DOWN
                reasoning = "قیمت < SMA20 (روند نزولی)"
        else:
            direction = TrendDirection.NEUTRAL
            reasoning = "قیمت در نزدیکی SMA20 (روند خنثی)"

        result.add_analysis(TechnicalAnalysis(
            name="trend_direction",
            value=direction.value,
            reasoning=reasoning,
            fact_refs=["current_price", "sma_20"] + (["sma_50"] if sma_50 else []),
            confidence=0.85,
        ))

        # Price vs SMA distance
        distance_pct = ((current_price - sma_20) / sma_20) * 100
        result.add_analysis(TechnicalAnalysis(
            name="price_sma_distance",
            value=round(distance_pct, 2),
            reasoning=f"فاصله قیمت از SMA20: {distance_pct:.2f}%",
            fact_refs=["current_price", "sma_20"],
            confidence=0.8,
        ))

        result.finalize()
        return result


class MomentumModule:
    """ماژول تحلیل مومنتوم (RSI, MACD, etc.)"""

    def analyze(
        self,
        symbol: str,
        prices: list[float],
        fund_type: FundType,
        identity: FundIdentity,
        request_id: str,
    ) -> TechnicalModuleResult:
        result = TechnicalModuleResult(module_name="momentum")

        # Applicability check is done by orchestrator (TechnicalEngine)
        # Module just processes the data

        if len(prices) < 14:
            result.add_fact(TechnicalFact(
                name="rsi_14",
                value=None,
                method="rsi",
                formula="RSI(14) = 100 - 100/(1+RS) حيث RS = avg_gain/avg_loss",
                inputs={"period": 14, "available_points": len(prices)},
                timestamp=datetime.now(),
                freshness="insufficient",
                source="HistoryRepository",
                confidence=0.0,
            ))
            result.add_analysis(TechnicalAnalysis(
                name="rsi_state",
                value=MomentumState.UNKNOWN.value,
                reasoning="تاریخقه ناکافی برای RSI(14)",
                fact_refs=["rsi_14"],
                confidence=0.0,
            ))
            return result

        # Calculate RSI(14)
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c for c in changes if c > 0]
        losses = [-c for c in changes if c < 0]

        avg_gain = statistics.mean(gains[-14:]) if gains else 0
        avg_loss = statistics.mean(losses[-14:]) if losses else 0

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        result.add_fact(TechnicalFact(
            name="rsi_14",
            value=round(rsi, 1),
            method="rsi",
            formula="RSI(14) = 100 - 100/(1 + avg_gain/avg_loss)",
            inputs={"period": 14, "avg_gain": avg_gain, "avg_loss": avg_loss},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        # RSI interpretation
        if rsi >= 70:
            state = MomentumState.OVERBOUGHT
            reasoning = "RSI >= 70 (اشباع خرید)"
        elif rsi >= 55:
            state = MomentumState.BULLISH
            reasoning = "RSI 55-70 (مومنتوم صعودی)"
        elif rsi >= 45:
            state = MomentumState.NEUTRAL
            reasoning = "RSI 45-55 (خنثی)"
        elif rsi >= 30:
            state = MomentumState.BEARISH
            reasoning = "RSI 30-45 (مومنتوم نزولی)"
        else:
            state = MomentumState.OVERSOLD
            reasoning = "RSI <= 30 (اشباع فروش)"

        result.add_analysis(TechnicalAnalysis(
            name="rsi_state",
            value=state.value,
            reasoning=reasoning,
            fact_refs=["rsi_14"],
            confidence=0.8,
        ))

        # MACD (12, 26, 9) - simplified
        if len(prices) >= 26:
            ema_12 = self._ema(prices, 12)
            ema_26 = self._ema(prices, 26)
            macd_line = ema_12 - ema_26
            
            # Signal line (9-period EMA of MACD)
            # Simplified: just store MACD line
            result.add_fact(TechnicalFact(
                name="macd_line",
                value=round(macd_line, 4),
                method="macd",
                formula="MACD = EMA(12) - EMA(26)",
                inputs={"ema_12": ema_12, "ema_26": ema_26},
                timestamp=datetime.now(),
                freshness="fresh",
                source="HistoryRepository",
                confidence=0.8,
            ))

            # MACD interpretation
            if macd_line > 0:
                macd_reasoning = "MACD > 0 (مومنتوم صعودی)"
            else:
                macd_reasoning = "MACD < 0 (مومنتوم نزولی)"

            result.add_analysis(TechnicalAnalysis(
                name="macd_signal",
                value="bullish" if macd_line > 0 else "bearish",
                reasoning=macd_reasoning,
                fact_refs=["macd_line"],
                confidence=0.75,
            ))

        result.finalize()
        return result

    def _ema(self, prices: list[float], period: int) -> float:
        """محاسبه EMA ساده"""
        if len(prices) < period:
            return statistics.mean(prices)
        multiplier = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = (price - ema) * multiplier + ema
        return ema


class VolatilityModule:
    """ماژول تحلیل نوسان"""

    def analyze(
        self,
        symbol: str,
        prices: list[float],
        fund_type: FundType,
        identity: FundIdentity,
        request_id: str,
    ) -> TechnicalModuleResult:
        result = TechnicalModuleResult(module_name="volatility")

        # Applicability check is done by orchestrator (TechnicalEngine)
        # Module just processes the data

        if len(prices) < 20:
            result.add_fact(TechnicalFact(
                name="volatility_20",
                value=None,
                method="std_dev",
                formula="σ = sqrt(sum((r_i - mean_r)^2) / (n-1)) برای بازده‌های ۲۰ روزه",
                inputs={"period": 20, "available_points": len(prices)},
                timestamp=datetime.now(),
                freshness="insufficient",
                source="HistoryRepository",
                confidence=0.0,
            ))
            result.add_analysis(TechnicalAnalysis(
                name="volatility_regime",
                value=VolatilityRegime.UNKNOWN.value,
                reasoning="تاریخچه ناکافی برای محاسبه نوسان",
                fact_refs=["volatility_20"],
                confidence=0.0,
            ))
            return result

        # Calculate 20-day volatility (std dev of returns)
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        recent_returns = returns[-20:]
        mean_return = statistics.mean(recent_returns)
        std_dev = statistics.stdev(recent_returns) if len(recent_returns) > 1 else 0
        annualized_vol = std_dev * (252 ** 0.5) * 100  # annualized percentage

        result.add_fact(TechnicalFact(
            name="volatility_20",
            value=round(std_dev * 100, 4),
            method="std_dev",
            formula="σ_20 = std_dev(daily_returns[-20:])",
            inputs={"period": 20, "mean_return": mean_return, "std_dev": std_dev},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        result.add_fact(TechnicalFact(
            name="annualized_volatility",
            value=round(annualized_vol, 2),
            method="std_dev_annualized",
            formula="Annualized Vol = σ_20 * sqrt(252) * 100",
            inputs={"daily_vol_pct": std_dev * 100},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.8,
        ))

        # Volatility regime
        if annualized_vol < 10:
            regime = VolatilityRegime.VERY_LOW
            reasoning = "نوسان سالانه < 10% (بسیار پایین)"
        elif annualized_vol < 20:
            regime = VolatilityRegime.LOW
            reasoning = "نوسان سالانه 10-20% (پایین)"
        elif annualized_vol < 35:
            regime = VolatilityRegime.NORMAL
            reasoning = "نوسان سالانه 20-35% (معمولی)"
        elif annualized_vol < 50:
            regime = VolatilityRegime.HIGH
            reasoning = "نوسان سالانه 35-50% (بالا)"
        else:
            regime = VolatilityRegime.VERY_HIGH
            reasoning = "نوسان سالانه > 50% (بسیار بالا)"

        result.add_analysis(TechnicalAnalysis(
            name="volatility_regime",
            value=regime.value,
            reasoning=reasoning,
            fact_refs=["volatility_20", "annualized_volatility"],
            confidence=0.8,
        ))

        # Max drawdown (90-day)
        if len(prices) >= 90:
            recent = prices[-90:]
            peak = recent[0]
            max_dd = 0.0
            for p in recent:
                if p > peak:
                    peak = p
                dd = (peak - p) / peak * 100
                if dd > max_dd:
                    max_dd = dd

            result.add_fact(TechnicalFact(
                name="max_drawdown_90",
                value=round(max_dd, 2),
                method="max_drawdown",
                formula="MDD = max((peak - trough) / peak) * 100 over 90 days",
                inputs={"period": 90},
                timestamp=datetime.now(),
                freshness="fresh",
                source="HistoryRepository",
                confidence=0.8,
            ))

            result.add_analysis(TechnicalAnalysis(
                name="max_drawdown_assessment",
                value="low" if max_dd < 10 else "moderate" if max_dd < 20 else "high",
                reasoning=f"حداکثر افت ۹۰ روزه: {max_dd:.1f}%",
                fact_refs=["max_drawdown_90"],
                confidence=0.8,
            ))

        result.finalize()
        return result


class VolumeModule:
    """ماژول تحلیل حجم"""

    def analyze(
        self,
        symbol: str,
        volumes: list[float],
        prices: list[float],
        fund_type: FundType,
        identity: FundIdentity,
        request_id: str,
    ) -> TechnicalModuleResult:
        result = TechnicalModuleResult(module_name="volume")

        # Applicability check is done by orchestrator (TechnicalEngine)
        # Module just processes the data

        if len(volumes) < 20 or len(prices) < 20:
            result.add_analysis(TechnicalAnalysis(
                name="volume_trend",
                value=MomentumState.UNKNOWN.value,
                reasoning="تاریخچه حجم/قیمت ناکافی",
                fact_refs=[],
                confidence=0.0,
            ))
            return result

        recent_vol = volumes[-20:]
        avg_vol_20 = statistics.mean(recent_vol)
        current_vol = volumes[-1]
        vol_ratio = current_vol / avg_vol_20 if avg_vol_20 > 0 else 0

        # Price-volume relationship
        price_change = (prices[-1] - prices[-2]) / prices[-2] if len(prices) >= 2 else 0

        result.add_fact(TechnicalFact(
            name="avg_volume_20",
            value=round(avg_vol_20, 0),
            method="mean",
            formula="AVG_VOL_20 = mean(volume[-20:])",
            inputs={"period": 20},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        result.add_fact(TechnicalFact(
            name="volume_ratio",
            value=round(vol_ratio, 2),
            method="ratio",
            formula="volume_ratio = current_volume / avg_volume_20",
            inputs={"current": current_vol, "avg_20": avg_vol_20},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        # Volume interpretation
        if vol_ratio > 2.0 and price_change > 0:
            interpretation = "حجم بالا + قیمت بالا (تأیید روند صعودی)"
        elif vol_ratio > 2.0 and price_change < 0:
            interpretation = "حجم بالا + قیمت پایین (تأیید روند نزولی)"
        elif vol_ratio > 1.5:
            interpretation = "حجم بالاتر از میانگین"
        elif vol_ratio < 0.5:
            interpretation = "حجم پایین (افزایش کاذب احتمالی)"
        else:
            interpretation = "حجم معمولی"

        result.add_analysis(TechnicalAnalysis(
            name="volume_trend",
            value="high" if vol_ratio > 1.5 else "normal" if vol_ratio > 0.5 else "low",
            reasoning=interpretation,
            fact_refs=["avg_volume_20", "volume_ratio"],
            confidence=0.8,
        ))

        result.finalize()
        return result


class PriceStructureModule:
    """ماژول تحلیل ساختار قیمتی (Support/Resistance, Patterns)"""

    def analyze(
        self,
        symbol: str,
        prices: list[float],
        highs: Optional[list[float]] = None,
        lows: Optional[list[float]] = None,
        fund_type: FundType = FundType.UNKNOWN,
        identity: Optional[FundIdentity] = None,
        request_id: str = "",
    ) -> TechnicalModuleResult:
        result = TechnicalModuleResult(module_name="price_structure")

        # Applicability check is done by orchestrator (TechnicalEngine)
        # Module just processes the data

        if len(prices) < 50:
            result.add_analysis(TechnicalAnalysis(
                name="position_in_range",
                value="insufficient_data",
                reasoning="تاریخچه ناکافی برای تشخیص سطوح",
                fact_refs=[],
                confidence=0.0,
            ))
            return result

        # Simple support/resistance detection using recent highs/lows
        recent = prices[-50:]
        high_50 = max(recent)
        low_50 = min(recent)
        current = prices[-1]

        # Distance from 52-week high/low (approximate with 50-period)
        dist_from_high = ((high_50 - current) / high_50) * 100
        dist_from_low = ((current - low_50) / low_50) * 100

        result.add_fact(TechnicalFact(
            name="high_50",
            value=high_50,
            method="max",
            formula="HIGH_50 = max(close[-50:])",
            inputs={"period": 50},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        result.add_fact(TechnicalFact(
            name="low_50",
            value=low_50,
            method="min",
            formula="LOW_50 = min(close[-50:])",
            inputs={"period": 50},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.85,
        ))

        result.add_fact(TechnicalFact(
            name="dist_from_high_pct",
            value=round(dist_from_high, 2),
            method="pct_distance",
            formula="(HIGH_50 - current) / HIGH_50 * 100",
            inputs={"high_50": high_50, "current": current},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.8,
        ))

        result.add_fact(TechnicalFact(
            name="dist_from_low_pct",
            value=round(dist_from_low, 2),
            method="pct_distance",
            formula="(current - LOW_50) / LOW_50 * 100",
            inputs={"low_50": low_50, "current": current},
            timestamp=datetime.now(),
            freshness="fresh",
            source="HistoryRepository",
            confidence=0.8,
        ))

        # Position in range
        if dist_from_high < 3:
            position = "near_high"
            reasoning = "قیمت نزدیک سقف ۵۰ روزه"
        elif dist_from_low < 3:
            position = "near_low"
            reasoning = "قیمت نزدیک کف ۵۰ روزه"
        elif dist_from_high < dist_from_low:
            position = "upper_half"
            reasoning = "قیمت در نیمه بالای رنج ۵۰ روزه"
        else:
            position = "lower_half"
            reasoning = "قیمت در نیمه پایین رنج ۵۰ روزه"

        result.add_analysis(TechnicalAnalysis(
            name="position_in_range",
            value=position,
            reasoning=reasoning,
            fact_refs=["high_50", "low_50", "dist_from_high_pct", "dist_from_low_pct"],
            confidence=0.8,
        ))

        result.finalize()
        return result


class TechnicalEngine:
    """موتور تحلیل تکنیکال ترکیبی"""

    METHODOLOGY_VERSION = "v1"

    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        repository: Optional[HistoryRepository] = None,
        data_quality_gate: Optional[DataQualityGate] = None,
        fund_identity_manager: Optional[Any] = None,
    ):
        self.provider = provider
        self.repository = repository
        self.data_quality_gate = data_quality_gate
        self.fund_identity_manager = fund_identity_manager
        self.trend_module = TrendModule(repository)
        self.momentum_module = MomentumModule()
        self.volatility_module = VolatilityModule()
        self.volume_module = VolumeModule()
        self.price_structure_module = PriceStructureModule()

    def _is_applicable(self, metric: str, fund_type: FundType) -> bool:
        """Check if metric is applicable for fund type"""
        if self.fund_identity_manager:
            return self.fund_identity_manager.is_applicable(metric, fund_type)
        # Default: allow if no manager
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
        اجرای تحلیل تکنیکال کامل.
        
        Returns:
            dict با ماژول‌های مختلف
        """
        rid = request_id or f"tech_{symbol}_{datetime.now().timestamp()}"
        logger.info(f"[{rid}] TechnicalEngine analyze: {symbol}")

        # Fetch price history
        prices = []
        volumes = []
        highs = []
        lows = []

        if self.repository:
            try:
                fund_id = self.repository.get_fund_id(symbol)
                if fund_id:
                    with self.repository.db.transaction() as conn:
                        rows = conn.execute(
                            """SELECT close_price, volume, high_price, low_price 
                               FROM history 
                               WHERE fund_id = ? 
                               ORDER BY trade_date ASC""",
                            (fund_id,),
                        ).fetchall()
                    
                    for row in rows:
                        if row["close_price"] is not None:
                            prices.append(float(row["close_price"]))
                        if row["volume"] is not None:
                            volumes.append(float(row["volume"]))
                        if row["high_price"] is not None:
                            highs.append(float(row["high_price"]))
                        if row["low_price"] is not None:
                            lows.append(float(row["low_price"]))
            except Exception as e:
                logger.warning(f"[{rid}] Failed to fetch history: {e}")

        if not prices:
            logger.warning(f"[{rid}] No price history available for {symbol}")

        # Run modules
        results = {}

        # Trend
        if self._is_applicable("trend", fund_identity.fund_type):
            results["trend"] = self.trend_module.analyze(
                symbol, prices, fund_identity.fund_type, fund_identity, rid
            )
        else:
            results["trend"] = TechnicalModuleResult(module_name="trend")
            results["trend"].add_analysis(TechnicalAnalysis(
                name="trend_direction",
                value="not_applicable",
                reasoning=f"تحلیل روند برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))

        # Momentum
        if self._is_applicable("rsi", fund_identity.fund_type):
            results["momentum"] = self.momentum_module.analyze(
                symbol, prices, fund_identity.fund_type, fund_identity, rid
            )
        else:
            results["momentum"] = TechnicalModuleResult(module_name="momentum")
            results["momentum"].add_analysis(TechnicalAnalysis(
                name="rsi_state",
                value="not_applicable",
                reasoning=f"تحلیل مومنتوم برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))

        # Volatility
        if self._is_applicable("volatility", fund_identity.fund_type):
            results["volatility"] = self.volatility_module.analyze(
                symbol, prices, fund_identity.fund_type, fund_identity, rid
            )
        else:
            results["volatility"] = TechnicalModuleResult(module_name="volatility")
            results["volatility"].add_analysis(TechnicalAnalysis(
                name="volatility_regime",
                value="not_applicable",
                reasoning=f"تحلیل نوسان برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))

        # Volume
        if self._is_applicable("volume", fund_identity.fund_type):
            results["volume"] = self.volume_module.analyze(
                symbol, volumes, prices, fund_identity.fund_type, fund_identity, rid
            )
        else:
            results["volume"] = TechnicalModuleResult(module_name="volume")
            results["volume"].add_analysis(TechnicalAnalysis(
                name="volume_trend",
                value="not_applicable",
                reasoning=f"تحلیل حجم برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))

        # Price Structure
        if self._is_applicable("price_structure", fund_identity.fund_type):
            results["price_structure"] = self.price_structure_module.analyze(
                symbol, prices, highs, lows, fund_identity.fund_type, fund_identity, rid
            )
        else:
            results["price_structure"] = TechnicalModuleResult(module_name="price_structure")
            results["price_structure"].add_analysis(TechnicalAnalysis(
                name="position_in_range",
                value="not_applicable",
                reasoning=f"تحلیل ساختار قیمتی برای نوع صندوق {fund_identity.fund_type.value} قابل اجرا نیست",
                fact_refs=[],
                confidence=0.0,
            ))

        # Aggregate
        all_facts = []
        all_analyses = []
        confidences = []

        for module_name, module_result in results.items():
            all_facts.extend(module_result.facts)
            all_analyses.extend(module_result.analyses)
            if module_result.overall_confidence > 0:
                confidences.append(module_result.overall_confidence)

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
                for name, res in results.items()
            },
            "total_facts": len(all_facts),
            "total_analyses": len(all_analyses),
            "overall_confidence": overall_confidence,
            "methodology_version": self.METHODOLOGY_VERSION,
        }


if __name__ == "__main__":
    # Quick test
    print("TechnicalEngine module loaded successfully")