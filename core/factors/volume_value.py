"""فاکتور حجم و ارزش معاملات."""

from __future__ import annotations

from typing import Any

from core.factors.common import clamp, label_from_score, log_scale, safe_div
from core.scoring.models import FactorScore
from services.providers.models import SymbolQuote


def score_volume_value(quote: SymbolQuote, cfg: dict[str, Any]) -> FactorScore:
    liq = cfg.get("liquidity", {})
    value_ref = float(liq.get("value_ref", 50_000_000_000))
    volume_ref = float(liq.get("volume_ref", 5_000_000))

    value_s = log_scale(quote.value, value_ref)
    volume_s = log_scale(quote.volume, volume_ref)

    # relative to 1m average if present
    rel = None
    if quote.avg_volume_1m and quote.avg_volume_1m > 0 and quote.volume is not None:
        rel = safe_div(float(quote.volume), float(quote.avg_volume_1m), default=1.0)
        if rel >= 1.5:
            boost = 12
            rel_reason = "حجم امروز بالاتر از میانگین ماهانه است"
        elif rel >= 1.1:
            boost = 6
            rel_reason = "حجم امروز کمی بالاتر از میانگین ماهانه است"
        elif rel <= 0.5:
            boost = -12
            rel_reason = "حجم امروز کمتر از نصف میانگین ماهانه است"
        elif rel < 0.9:
            boost = -5
            rel_reason = "حجم امروز کمتر از میانگین ماهانه است"
        else:
            boost = 0
            rel_reason = "حجم نزدیک میانگین ماهانه است"
    else:
        boost = 0
        rel_reason = "میانگین حجم ماهانه در دسترس نیست"

    score = clamp(0.55 * value_s + 0.45 * volume_s + boost)
    reasons = [rel_reason]
    if value_s >= 70:
        reasons.append("ارزش معاملات بالاست")
    elif value_s <= 30:
        reasons.append("ارزش معاملات پایین است")

    return FactorScore(
        key="volume_value",
        title="حجم و ارزش",
        score=score,
        label=label_from_score(score),
        reasons=tuple(reasons),
        metrics={
            "volume": quote.volume,
            "value": quote.value,
            "avg_volume_1m": quote.avg_volume_1m,
            "volume_vs_avg": round(rel, 4) if rel is not None else None,
        },
    )
