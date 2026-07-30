"""ساخت خلاصه وضعیت بازار از لیست FundAssessment."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Optional

from core.scoring.models import FundAssessment


@dataclass
class MarketSummary:
    funds_count: int
    market_status: str
    market_power: float
    best_group: str
    worst_group: str
    avg_change_pct: Optional[float]
    median_score: Optional[float]
    total_value: Optional[float]
    up_count: int
    down_count: int
    flat_count: int
    group_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "funds_count": self.funds_count,
            "market_status": self.market_status,
            "market_power": self.market_power,
            "best_group": self.best_group,
            "worst_group": self.worst_group,
            "avg_change_pct": self.avg_change_pct,
            "median_score": self.median_score,
            "total_value": self.total_value,
            "up_count": self.up_count,
            "down_count": self.down_count,
            "flat_count": self.flat_count,
            "group_stats": self.group_stats,
            "generated_at": self.generated_at,
        }


def build_market_summary(
    ranked: list[FundAssessment],
    *,
    generated_at: str = "",
) -> MarketSummary:
    if not ranked:
        return MarketSummary(
            funds_count=0,
            market_status="نامشخص",
            market_power=50.0,
            best_group="-",
            worst_group="-",
            avg_change_pct=None,
            median_score=None,
            total_value=None,
            up_count=0,
            down_count=0,
            flat_count=0,
            generated_at=generated_at,
        )

    changes = [a.change_pct for a in ranked if a.change_pct is not None]
    avg_chg = mean(changes) if changes else None
    up = sum(1 for c in changes if c > 0.05)
    down = sum(1 for c in changes if c < -0.05)
    flat = len(changes) - up - down

    scores = sorted(a.final_score for a in ranked)
    mid = len(scores) // 2
    median_score = (
        scores[mid]
        if len(scores) % 2 == 1
        else (scores[mid - 1] + scores[mid]) / 2.0
    ) if scores else None

    values = [float(a.value) for a in ranked if a.value is not None]
    total_value = sum(values) if values else None

    by_type: dict[str, list[FundAssessment]] = defaultdict(list)
    for a in ranked:
        by_type[a.fund_type or "سایر"].append(a)

    group_stats: dict[str, dict[str, Any]] = {}
    group_strength: dict[str, float] = {}
    for ftype, items in by_type.items():
        ch = [x.change_pct for x in items if x.change_pct is not None]
        sc = [x.final_score for x in items]
        avg_c = mean(ch) if ch else 0.0
        avg_s = mean(sc) if sc else 0.0
        # قدرت گروه: ترکیب بازده و امتیاز
        strength = 0.6 * _clamp01((avg_c + 3) / 6) * 100 + 0.4 * avg_s
        group_stats[ftype] = {
            "count": len(items),
            "avg_change_pct": round(avg_c, 3) if ch else None,
            "avg_score": round(avg_s, 2),
            "best_symbol": items[0].symbol if items else "",
            "strength": round(strength, 1),
        }
        group_strength[ftype] = strength

    best_group = max(group_strength, key=group_strength.get) if group_strength else "-"
    worst_group = min(group_strength, key=group_strength.get) if group_strength else "-"

    market_status = _status_label(avg_chg)
    market_power = _power(avg_chg, up, len(changes) or 1)

    return MarketSummary(
        funds_count=len(ranked),
        market_status=market_status,
        market_power=market_power,
        best_group=best_group,
        worst_group=worst_group,
        avg_change_pct=round(avg_chg, 3) if avg_chg is not None else None,
        median_score=round(median_score, 2) if median_score is not None else None,
        total_value=total_value,
        up_count=up,
        down_count=down,
        flat_count=max(0, flat),
        group_stats=group_stats,
        generated_at=generated_at,
    )


def _status_label(avg_change: Optional[float]) -> str:
    if avg_change is None:
        return "نامشخص"
    if avg_change >= 0.8:
        return "مثبت قوی"
    if avg_change >= 0.15:
        return "مثبت"
    if avg_change > -0.15:
        return "خنثی"
    if avg_change > -0.8:
        return "منفی"
    return "منفی قوی"


def _power(avg_change: Optional[float], up: int, n: int) -> float:
    breadth = up / max(1, n)
    avg = avg_change if avg_change is not None else 0.0
    mom = max(0.0, min(100.0, 50.0 + avg * 12.0))
    return round(max(0.0, min(100.0, 0.55 * mom + 0.45 * breadth * 100.0)), 1)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))
