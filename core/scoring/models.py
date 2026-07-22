"""مدل‌های ارزیابی و امتیاز صندوق."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class FactorScore:
    key: str
    title: str
    score: float  # 0..100
    label: str
    reasons: tuple[str, ...] = ()
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "title": self.title,
            "score": round(float(self.score), 2),
            "label": self.label,
            "reasons": list(self.reasons),
            "metrics": self.metrics,
        }


@dataclass(frozen=True)
class FundAssessment:
    symbol: str
    name: str
    fund_type: str
    ins_code: str
    sector: Optional[str]
    final_score: float
    recommendation: str  # strong_buy|buy|neutral|weak|sell
    recommendation_label: str
    rank: Optional[int] = None
    factors: tuple[FactorScore, ...] = ()
    summary_reasons: tuple[str, ...] = ()
    close_price: Optional[float] = None
    last_price: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[float] = None
    value: Optional[float] = None
    issue_nav: Optional[float] = None
    redeem_nav: Optional[float] = None
    premium_pct: Optional[float] = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "fund_type": self.fund_type,
            "ins_code": self.ins_code,
            "sector": self.sector,
            "final_score": round(float(self.final_score), 2),
            "recommendation": self.recommendation,
            "recommendation_label": self.recommendation_label,
            "rank": self.rank,
            "factors": [f.to_dict() for f in self.factors],
            "summary_reasons": list(self.summary_reasons),
            "close_price": self.close_price,
            "last_price": self.last_price,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "value": self.value,
            "issue_nav": self.issue_nav,
            "redeem_nav": self.redeem_nav,
            "premium_pct": self.premium_pct,
            "extras": self.extras,
        }
