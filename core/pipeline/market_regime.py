"""
Market Regime Engine — تشخیص رژیم بازار بر اساس شواهد (Evidence-based).

این موتور رژیم بازار را بر اساس داده‌های واقعی BRS AllSymbols
و متریک‌های ترکیبی تعیین می‌کند.

خروجی بر اساس شواهد است، نه if/else ساده.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from core.history.repository import HistoryRepository
from services.providers.base import MarketDataProvider
from services.providers.models import SymbolQuote

logger = logging.getLogger(__name__)


class MarketRegime(str, Enum):
    """رژیم‌های بازار"""
    RISK_ON = "RISK_ON"
    RISK_OFF = "RISK_OFF"
    NEUTRAL = "NEUTRAL"
    TRANSITION = "TRANSITION"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    """سطح اطمینان"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FreshnessClass(str, Enum):
    """کلاس تازگی"""
    REALTIME = "realtime"
    LIVE = "live"
    INTRADAY = "intraday"
    END_OF_DAY = "end_of_day"
    EVENT = "event"
    PERIODIC = "periodic"
    HISTORICAL = "historical"


@dataclass
class Evidence:
    """یک شاهد برای تصمیم‌گیری رژیم"""
    metric: str
    value: float
    threshold: float
    comparison: str  # "above", "below", "within", "above_abs", "below_abs"
    source: str
    timestamp: datetime
    weight: float = 1.0
    description: str = ""


@dataclass
class MarketRegimeResult:
    """نتیجه تحلیل رژیم بازار"""
    regime: MarketRegime = MarketRegime.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    evidence: list[Evidence] = field(default_factory=list)
    metrics_used: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    freshness: FreshnessClass = FreshnessClass.INTRADAY
    methodology_version: str = "v1.0"
    reasoning: str = ""
    contradictory_evidence: list[Evidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "regime": self.regime.value,
            "confidence": self.confidence.value,
            "evidence": [
                {
                    "metric": e.metric,
                    "value": e.value,
                    "threshold": e.threshold,
                    "comparison": e.comparison,
                    "source": e.source,
                    "timestamp": e.timestamp.isoformat(),
                    "weight": e.weight,
                    "description": e.description,
                }
                for e in self.evidence
            ],
            "metrics_used": self.metrics_used,
            "timestamp": self.timestamp.isoformat(),
            "freshness": self.freshness.value,
            "methodology_version": self.methodology_version,
            "reasoning": self.reasoning,
            "contradictory_evidence": [
                {
                    "metric": e.metric,
                    "value": e.value,
                    "threshold": e.threshold,
                    "comparison": e.comparison,
                    "source": e.source,
                    "timestamp": e.timestamp.isoformat(),
                    "weight": e.weight,
                    "description": e.description,
                }
                for e in self.contradictory_evidence
            ],
        }


# ================================================================
# Regime Detection Thresholds
# ================================================================

REGIME_THRESHOLDS = {
    # Broad market metrics
    "avg_change_pct": {
        "risk_on_min": 0.3,
        "risk_off_max": -0.3,
        "transition_range": (-0.3, 0.3),
    },
    "total_volume": {
        "high_threshold": 1_000_000,  # 1M units
        "low_threshold": 500_000,     # 500K units
    },
    "total_value": {
        "high_threshold": 5_000_000_000_000,  # 5T IRR
        "low_threshold": 1_000_000_000_000,   # 1T IRR
    },
    "breadth": {
        "advance_decline_ratio_risk_on": 1.5,
        "advance_decline_ratio_risk_off": 0.67,
    },
    "market_drawdown": {
        "high_drawdown": -5.0,  # >5% drawdown
    },
    "dispersion": {
        "high_dispersion": 3.0,  # std of returns > 3%
    },
}

METHODOLOGY_VERSION = "v1.0"


# ================================================================
# Market Regime Engine
# ================================================================

class MarketRegimeEngine:
    """
    موتور تشخیص رژیم بازار بر اساس شواهد.

    از داده‌های BRS AllSymbols و market_snapshot استفاده می‌کند.
    خروجی: regime + confidence + evidence[] + reasoning
    """

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        repository: Optional[HistoryRepository] = None,
    ):
        self.provider = provider
        self.repository = repository
        self._request_id: Optional[str] = None

    def analyze(
        self,
        *,
        request_id: Optional[str] = None,
        force_refresh: bool = False,
    ) -> MarketRegimeResult:
        """
        تحلیل رژیم بازار.

        Args:
            request_id: شناسه درخواست برای Trace
            force_refresh: اجبار به refresh از BRS

        Returns:
            MarketRegimeResult
        """
        self._request_id = request_id or f"mr_{datetime.now().timestamp()}"
        result = MarketRegimeResult(
            timestamp=datetime.now(),
            methodology_version=METHODOLOGY_VERSION,
        )

        logger.info(f"[{self._request_id}] MarketRegimeEngine analyze started")

        # 1. دریافت داده‌های بازار
        market_data = self._fetch_market_data(force_refresh=force_refresh)
        result.metrics_used = list(market_data.keys())

        if not market_data:
            result.regime = MarketRegime.UNKNOWN
            result.confidence = ConfidenceLevel.LOW
            result.reasoning = "هیچ داده بازار قابل‌دستیابی نبود"
            result.freshness = FreshnessClass.INTRADAY
            return result

        # 2. استخراج شواهد
        evidence_list = self._extract_evidence(market_data)
        result.evidence = evidence_list

        # 3. تشخیص شواهد متناقض
        result.contradictory_evidence = self._detect_contradictions(evidence_list)

        # 4. محاسبه امتیاز رژیم
        regime_scores = self._score_regimes(evidence_list)

        # 5. تعیین رژیم نهایی
        result.regime, result.confidence = self._determine_regime(regime_scores, evidence_list)

        # 6. تولید استدلال
        result.reasoning = self._generate_reasoning(result.regime, evidence_list, regime_scores)

        # 7. تعیین تازگی
        result.freshness = self._determine_freshness(market_data)

        logger.info(
            f"[{self._request_id}] MarketRegimeEngine result: "
            f"regime={result.regime.value}, confidence={result.confidence.value}, "
            f"evidence_count={len(evidence_list)}"
        )
        return result

    def _fetch_market_data(self, force_refresh: bool = False) -> dict[str, Any]:
        """دریافت داده‌های بازار از BRS و DB"""
        data = {}

        # اولویت 1: BRS AllSymbols (زنده)
        if self.provider and not force_refresh:
            try:
                all_symbols = self.provider.get_all_symbols(symbol_type=1)  # همه نمادها
                if all_symbols:
                    data = self._compute_market_metrics(all_symbols)
                    data["_source"] = "BRS_API"
                    data["_fetched_at"] = datetime.now()
                    logger.debug(f"[{self._request_id}] Fetched market data from BRS AllSymbols")
                    return data
            except Exception as e:
                logger.warning(f"[{self._request_id}] BRS AllSymbols failed: {e}")

        # اولویت 2: DB market_snapshot (فول‌بک روزانه)
        if self.repository:
            try:
                snapshot = self.repository.get_latest_market_snapshot()
                if snapshot:
                    data = {
                        "avg_change_pct": snapshot.get("avg_change_pct"),
                        "total_volume": snapshot.get("total_volume"),
                        "total_value": snapshot.get("total_value"),
                        "funds_count": snapshot.get("funds_count"),
                        "best_group": snapshot.get("best_group"),
                        "worst_group": snapshot.get("worst_group"),
                        "market_status": snapshot.get("market_status"),
                        "market_power": snapshot.get("market_power"),
                    }
                    data["_source"] = "DB"
                    data["_fetched_at"] = datetime.now()  # approximate
                    logger.debug(f"[{self._request_id}] Fetched market data from DB snapshot")
                    return data
            except Exception as e:
                logger.warning(f"[{self._request_id}] DB market_snapshot failed: {e}")

        # اولویت 3: HistoryEngine daily scores (اگر موجود باشد)
        if self.repository:
            try:
                latest_scores = self.repository.get_latest_daily_scores(limit=100)
                if latest_scores:
                    changes = [s.get("change_pct") for s in latest_scores if s.get("change_pct") is not None]
                    if changes:
                        data = {
                            "avg_change_pct": sum(changes) / len(changes),
                            "funds_count": len(changes),
                            "up_count": sum(1 for c in changes if c > 0.05),
                            "down_count": sum(1 for c in changes if c < -0.05),
                            "flat_count": len(changes) - sum(1 for c in changes if c > 0.05) - sum(1 for c in changes if c < -0.05),
                        }
                        data["_source"] = "DB"
                        data["_fetched_at"] = datetime.now()
                        logger.debug(f"[{self._request_id}] Computed market data from daily_scores")
                        return data
            except Exception as e:
                logger.warning(f"[{self._request_id}] DB daily_scores failed: {e}")

        return {}

    def _compute_market_metrics(self, quotes: list[SymbolQuote]) -> dict[str, Any]:
        """محاسبه متریک‌های بازار از لیست نمادها"""
        if not quotes:
            return {}

        # فیلتر صندوق‌های معتبر
        fund_quotes = [q for q in quotes if q.is_fund_like and q.symbol]
        if not fund_quotes:
            fund_quotes = quotes

        changes = [q.change_close_pct for q in fund_quotes if q.change_close_pct is not None]
        volumes = [q.volume for q in fund_quotes if q.volume is not None]
        values = [q.value for q in fund_quotes if q.value is not None]

        # Breadth: advance/decline
        up = sum(1 for c in changes if c > 0.05)
        down = sum(1 for c in changes if c < -0.05)
        flat = len(changes) - up - down
        adv_dec_ratio = up / max(down, 1)

        # Dispersion: std of returns
        import statistics
        dispersion = statistics.stdev(changes) if len(changes) > 1 else 0.0

        # Best/worst groups
        by_type: dict[str, list[float]] = {}
        for q in fund_quotes:
            ft = q.fund_type or "سایر"
            if q.change_close_pct is not None:
                by_type.setdefault(ft, []).append(float(q.change_close_pct))

        group_avg = {k: sum(v) / len(v) for k, v in by_type.items() if v}
        best_group = ""
        worst_group = ""
        if group_avg:
            best_group = max(group_avg.keys(), key=lambda k: group_avg[k])
            worst_group = min(group_avg.keys(), key=lambda k: group_avg[k])

        return {
            "avg_change_pct": sum(changes) / len(changes) if changes else None,
            "total_volume": sum(volumes) if volumes else None,
            "total_value": sum(values) if values else None,
            "funds_count": len(fund_quotes),
            "up_count": up,
            "down_count": down,
            "flat_count": flat,
            "adv_dec_ratio": adv_dec_ratio,
            "dispersion": dispersion,
            "best_group": best_group,
            "worst_group": worst_group,
            "group_avg_change": group_avg,
        }

    def _extract_evidence(self, market_data: dict[str, Any]) -> list[Evidence]:
        """استخراج شواهد از داده‌های بازار"""
        evidence = []
        now = datetime.now()
        source = market_data.get("_source", "UNKNOWN")

        # 1. Average market change
        avg_chg = market_data.get("avg_change_pct")
        if avg_chg is not None:
            thresholds = REGIME_THRESHOLDS["avg_change_pct"]
            if avg_chg >= thresholds["risk_on_min"]:
                evidence.append(Evidence(
                    metric="avg_change_pct",
                    value=avg_chg,
                    threshold=thresholds["risk_on_min"],
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=2.0,
                    description=f"Market average change {avg_chg:.2f}% >= {thresholds['risk_on_min']}% (RISK_ON threshold)",
                ))
            elif avg_chg <= thresholds["risk_off_max"]:
                evidence.append(Evidence(
                    metric="avg_change_pct",
                    value=avg_chg,
                    threshold=thresholds["risk_off_max"],
                    comparison="below",
                    source=source,
                    timestamp=now,
                    weight=2.0,
                    description=f"Market average change {avg_chg:.2f}% <= {thresholds['risk_off_max']}% (RISK_OFF threshold)",
                ))
            else:
                evidence.append(Evidence(
                    metric="avg_change_pct",
                    value=avg_chg,
                    threshold=thresholds["transition_range"][1],
                    comparison="within",
                    source=source,
                    timestamp=now,
                    weight=1.0,
                    description=f"Market average change {avg_chg:.2f}% in transition range ({thresholds['transition_range'][0]}% to {thresholds['transition_range'][1]}%)",
                ))

        # 2. Total volume
        total_vol = market_data.get("total_volume")
        if total_vol is not None:
            thresholds = REGIME_THRESHOLDS["total_volume"]
            if total_vol >= thresholds["high_threshold"]:
                evidence.append(Evidence(
                    metric="total_volume",
                    value=total_vol,
                    threshold=thresholds["high_threshold"],
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=1.5,
                    description=f"Total volume {total_vol:,.0f} >= {thresholds['high_threshold']:,.0f} (high liquidity)",
                ))
            elif total_vol <= thresholds["low_threshold"]:
                evidence.append(Evidence(
                    metric="total_volume",
                    value=total_vol,
                    threshold=thresholds["low_threshold"],
                    comparison="below",
                    source=source,
                    timestamp=now,
                    weight=1.5,
                    description=f"Total volume {total_vol:,.0f} <= {thresholds['low_threshold']:,.0f} (low liquidity)",
                ))

        # 3. Total value
        total_val = market_data.get("total_value")
        if total_val is not None:
            thresholds = REGIME_THRESHOLDS["total_value"]
            if total_val >= thresholds["high_threshold"]:
                evidence.append(Evidence(
                    metric="total_value",
                    value=total_val,
                    threshold=thresholds["high_threshold"],
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=1.0,
                    description=f"Total value {total_val:,.0f} >= {thresholds['high_threshold']:,.0f} (high activity)",
                ))
            elif total_val <= thresholds["low_threshold"]:
                evidence.append(Evidence(
                    metric="total_value",
                    value=total_val,
                    threshold=thresholds["low_threshold"],
                    comparison="below",
                    source=source,
                    timestamp=now,
                    weight=1.0,
                    description=f"Total value {total_val:,.0f} <= {thresholds['low_threshold']:,.0f} (low activity)",
                ))

        # 4. Breadth (advance/decline ratio)
        adv_dec = market_data.get("adv_dec_ratio")
        if adv_dec is not None:
            thresholds = REGIME_THRESHOLDS["breadth"]
            if adv_dec >= thresholds["advance_decline_ratio_risk_on"]:
                evidence.append(Evidence(
                    metric="advance_decline_ratio",
                    value=adv_dec,
                    threshold=thresholds["advance_decline_ratio_risk_on"],
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=1.5,
                    description=f"Advance/Decline ratio {adv_dec:.2f} >= {thresholds['advance_decline_ratio_risk_on']} (broad participation)",
                ))
            elif adv_dec <= thresholds["advance_decline_ratio_risk_off"]:
                evidence.append(Evidence(
                    metric="advance_decline_ratio",
                    value=adv_dec,
                    threshold=thresholds["advance_decline_ratio_risk_off"],
                    comparison="below",
                    source=source,
                    timestamp=now,
                    weight=1.5,
                    description=f"Advance/Decline ratio {adv_dec:.2f} <= {thresholds['advance_decline_ratio_risk_off']} (broad decline)",
                ))

        # 5. Dispersion
        dispersion = market_data.get("dispersion")
        if dispersion is not None:
            thresholds = REGIME_THRESHOLDS["dispersion"]
            if dispersion >= thresholds["high_dispersion"]:
                evidence.append(Evidence(
                    metric="return_dispersion",
                    value=dispersion,
                    threshold=thresholds["high_dispersion"],
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=1.0,
                    description=f"Return dispersion {dispersion:.2f}% >= {thresholds['high_dispersion']}% (high uncertainty)",
                ))

        # 6. Best/Worst group momentum
        group_avg = market_data.get("group_avg_change", {})
        if group_avg:
            best_val = max(group_avg.values())
            worst_val = min(group_avg.values())
            if best_val > 1.0:
                evidence.append(Evidence(
                    metric="best_group_momentum",
                    value=best_val,
                    threshold=1.0,
                    comparison="above",
                    source=source,
                    timestamp=now,
                    weight=0.5,
                    description=f"Best group ({market_data.get('best_group', '')}) momentum {best_val:.2f}% > 1% (sector leadership)",
                ))
            if worst_val < -1.0:
                evidence.append(Evidence(
                    metric="worst_group_momentum",
                    value=worst_val,
                    threshold=-1.0,
                    comparison="below",
                    source=source,
                    timestamp=now,
                    weight=0.5,
                    description=f"Worst group ({market_data.get('worst_group', '')}) momentum {worst_val:.2f}% < -1% (sector weakness)",
                ))

        return evidence

    def _detect_contradictions(self, evidence: list[Evidence]) -> list[Evidence]:
        """تشخیص شواهد متناقض"""
        contradictions = []

        # بررسی تضادها: همزمان RISK_ON و RISK_OFF شواهد
        risk_on_evidence = [e for e in evidence if e.comparison in ("above", "above_abs") and e.value > 0]
        risk_off_evidence = [e for e in evidence if e.comparison in ("below", "below_abs") and e.value < 0]

        # اگر هم volume بالا و هم avg_change منفی باشد
        high_vol = any(e.metric == "total_volume" and e.comparison == "above" for e in evidence)
        neg_change = any(e.metric == "avg_change_pct" and e.comparison == "below" for e in evidence)

        if high_vol and neg_change:
            contradictions.append(Evidence(
                metric="volume_change_contradiction",
                value=0,
                threshold=0,
                comparison="contradiction",
                source="internal",
                timestamp=datetime.now(),
                weight=1.0,
                description="High volume with negative market change (possible distribution or panic selling)",
            ))

        # اگر breadth مثبت اما dispersion بالا باشد
        pos_breadth = any(e.metric == "advance_decline_ratio" and e.comparison == "above" for e in evidence)
        high_disp = any(e.metric == "return_dispersion" and e.comparison == "above" for e in evidence)

        if pos_breadth and high_disp:
            contradictions.append(Evidence(
                metric="breadth_dispersion_contradiction",
                value=0,
                threshold=0,
                comparison="contradiction",
                source="internal",
                timestamp=datetime.now(),
                weight=1.0,
                description="Positive breadth but high dispersion (selective rally, not broad-based)",
            ))

        return contradictions

    def _score_regimes(self, evidence: list[Evidence]) -> dict[MarketRegime, float]:
        """محاسبه امتیاز برای هر رژیم"""
        scores = {
            MarketRegime.RISK_ON: 0.0,
            MarketRegime.RISK_OFF: 0.0,
            MarketRegime.NEUTRAL: 0.0,
            MarketRegime.TRANSITION: 0.0,
        }

        for e in evidence:
            weight = e.weight

            # RISK_ON شواهد
            if e.comparison == "above" and e.value > 0:
                if e.metric in ("avg_change_pct", "total_volume", "total_value", "advance_decline_ratio", "best_group_momentum"):
                    scores[MarketRegime.RISK_ON] += weight
                elif e.metric in ("worst_group_momentum"):  # worst group positive would be risk_on
                    if e.value > 0:
                        scores[MarketRegime.RISK_ON] += weight * 0.5

            # RISK_OFF شواهد
            if e.comparison == "below" and e.value < 0:
                if e.metric in ("avg_change_pct", "total_volume", "total_value", "advance_decline_ratio", "worst_group_momentum"):
                    scores[MarketRegime.RISK_OFF] += weight
                elif e.metric in ("best_group_momentum"):  # best group negative would be risk_off
                    if e.value < 0:
                        scores[MarketRegime.RISK_OFF] += weight * 0.5

            # NEUTRAL / TRANSITION شواهد
            if e.comparison == "within":
                if e.metric == "avg_change_pct":
                    scores[MarketRegime.TRANSITION] += weight
                    scores[MarketRegime.NEUTRAL] += weight * 0.5

            # High dispersion = uncertainty = TRANSITION
            if e.metric == "return_dispersion" and e.comparison == "above":
                scores[MarketRegime.TRANSITION] += weight

        return scores

    def _determine_regime(
        self,
        scores: dict[MarketRegime, float],
        evidence: list[Evidence],
    ) -> tuple[MarketRegime, ConfidenceLevel]:
        """تعیین رژیم نهایی بر اساس امتیازات"""
        if not evidence:
            return MarketRegime.UNKNOWN, ConfidenceLevel.LOW

        # یافتن رژیم با بالاترین امتیاز
        max_score = max(scores.values())
        top_regimes = [r for r, s in scores.items() if s == max_score]

        # اگر هم‌پیچیده باشد
        if len(top_regimes) > 1:
            # ترجیح به TRANSITION در صورت تعادل
            if MarketRegime.TRANSITION in top_regimes:
                regime = MarketRegime.TRANSITION
            elif MarketRegime.RISK_ON in top_regimes and MarketRegime.RISK_OFF in top_regimes:
                regime = MarketRegime.TRANSITION
            else:
                regime = top_regimes[0]
        else:
            regime = top_regimes[0]

        # محاسبه اطمینان
        total_weight = sum(e.weight for e in evidence)
        regime_weight = scores.get(regime, 0.0)

        if total_weight == 0:
            confidence = ConfidenceLevel.LOW
        else:
            ratio = regime_weight / total_weight
            if ratio >= 0.6:
                confidence = ConfidenceLevel.HIGH
            elif ratio >= 0.35:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW

        # اگر شواهد متناقض زیاد باشد، اطمینان را کاهش بده
        if len(self._detect_contradictions(evidence)) >= 2:
            if confidence == ConfidenceLevel.HIGH:
                confidence = ConfidenceLevel.MEDIUM
            elif confidence == ConfidenceLevel.MEDIUM:
                confidence = ConfidenceLevel.LOW

        return regime, confidence

    def _generate_reasoning(
        self,
        regime: MarketRegime,
        evidence: list[Evidence],
        scores: dict[MarketRegime, float],
    ) -> str:
        """تولید استدلال متنی"""
        if regime == MarketRegime.UNKNOWN:
            return "داده‌های کافی برای تشخیص رژیم بازار وجود ندارد"

        supporting = [e for e in evidence if self._evidence_supports_regime(e, regime)]
        if not supporting:
            return f"رژیم {regime.value} تشخیص داده شد اما شاهد قوی مستقیمی یافت نشد"

        parts = [f"رژیم بازار: {regime.value}"]
        for e in supporting[:3]:  # حداکثر 3 شاهد اصلی
            parts.append(f"- {e.description}")

        if scores:
            score_str = ", ".join(f"{r.value}={s:.1f}" for r, s in scores.items() if s > 0)
            parts.append(f"امتیازات: {score_str}")

        return "\n".join(parts)

    def _evidence_supports_regime(self, evidence: Evidence, regime: MarketRegime) -> bool:
        """بررسی اینکه آیا شاهد از رژیم خاصی پشتیبانی می‌کند"""
        if regime == MarketRegime.RISK_ON:
            return (evidence.comparison == "above" and evidence.value > 0) or \
                   (evidence.metric == "avg_change_pct" and evidence.comparison == "within" and evidence.value > 0)
        elif regime == MarketRegime.RISK_OFF:
            return (evidence.comparison == "below" and evidence.value < 0) or \
                   (evidence.metric == "avg_change_pct" and evidence.comparison == "within" and evidence.value < 0)
        elif regime == MarketRegime.TRANSITION:
            return evidence.comparison == "within" or \
                   (evidence.metric == "return_dispersion" and evidence.comparison == "above")
        elif regime == MarketRegime.NEUTRAL:
            return evidence.comparison == "within"
        return False

    def _determine_freshness(self, market_data: dict[str, Any]) -> FreshnessClass:
        """تعیین کلاس تازگی داده"""
        source = market_data.get("_source", "")
        if source == "BRS_API":
            return FreshnessClass.INTRADAY
        elif source == "DB":
            return FreshnessClass.END_OF_DAY
        return FreshnessClass.HISTORICAL


# ================================================================
# Convenience Functions
# ================================================================

def create_market_regime_engine(
    provider: Optional[BrsProvider] = None,
    repository: Optional[HistoryRepository] = None,
) -> MarketRegimeEngine:
    """ساخت MarketRegimeEngine با dependency injection"""
    return MarketRegimeEngine(provider=provider, repository=repository)