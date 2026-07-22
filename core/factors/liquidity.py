"""فاکتور نقدشوندگی."""

from __future__ import annotations

from typing import Any

from core.factors.common import clamp, label_from_score, log_scale
from core.scoring.models import FactorScore
from services.providers.models import SymbolQuote


def score_liquidity(quote: SymbolQuote, cfg: dict[str, Any]) -> FactorScore:
    liq = cfg.get("liquidity", {})
    value_ref = float(liq.get("value_ref", 50_000_000_000))
    volume_ref = float(liq.get("volume_ref", 5_000_000))
    depth_ref = float(liq.get("depth_ref", 200_000))

    value_s = log_scale(quote.value, value_ref)
    volume_s = log_scale(quote.volume, volume_ref)
    depth = quote.orderbook.total_bid_quantity + quote.orderbook.total_ask_quantity
    depth_s = log_scale(depth, depth_ref)

    score = clamp(0.45 * value_s + 0.35 * volume_s + 0.20 * depth_s)
    reasons = []
    if value_s >= 70:
        reasons.append("ارزش معاملات نسبت به معیار نقدشوندگی مناسب است")
    elif value_s <= 30:
        reasons.append("ارزش معاملات پایین است و خروج/ورود ممکن است سخت‌تر باشد")
    if depth_s >= 70:
        reasons.append("عمق سفارش‌ها قابل قبول است")
    elif depth_s <= 30:
        reasons.append("عمق بازار کم است")
    if not reasons:
        reasons.append("نقدشوندگی در سطح متوسط ارزیابی شد")

    return FactorScore(
        key="liquidity",
        title="نقدشوندگی",
        score=score,
        label=label_from_score(score),
        reasons=tuple(reasons),
        metrics={
            "value": quote.value,
            "volume": quote.volume,
            "depth_qty": depth,
            "value_score": round(value_s, 2),
            "volume_score": round(volume_s, 2),
            "depth_score": round(depth_s, 2),
        },
    )
