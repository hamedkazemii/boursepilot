"""ابزار مشترک فاکتورها."""

from __future__ import annotations

import math
from typing import Optional


def clamp(score: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(score)))


def log_scale(value: Optional[float], ref: float) -> float:
    """نرمال‌سازی لگاریتمی 0..100 نسبت به ref."""
    if value is None or value <= 0 or ref <= 0:
        return 0.0
    return clamp(100.0 * math.log10(1.0 + float(value)) / math.log10(1.0 + float(ref)))


def safe_div(n: float, d: float, default: float = 0.0) -> float:
    if d == 0:
        return default
    return n / d


def label_from_score(score: float) -> str:
    if score >= 80:
        return "عالی"
    if score >= 65:
        return "خوب"
    if score >= 45:
        return "متوسط"
    if score >= 30:
        return "ضعیف"
    return "بسیار ضعیف"
