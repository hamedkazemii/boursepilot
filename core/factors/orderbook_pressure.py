"""فاکتور فشار پیش‌سفارش / عمق خرید و فروش."""

from __future__ import annotations

from typing import Any

from core.factors.common import clamp, label_from_score, safe_div
from core.scoring.models import FactorScore
from services.providers.models import SymbolQuote


def score_orderbook_pressure(quote: SymbolQuote, cfg: dict[str, Any]) -> FactorScore:
    ob = cfg.get("orderbook", {})
    strong_bid = float(ob.get("strong_bid_ratio", 3.0))
    mild_bid = float(ob.get("mild_bid_ratio", 1.5))
    strong_ask = float(ob.get("strong_ask_ratio", 0.33))

    bid = quote.orderbook.total_bid_quantity
    ask = quote.orderbook.total_ask_quantity
    ratio = safe_div(bid, max(ask, 1.0), default=1.0)

    # map ratio -> score
    if ask <= 0 and bid > 0:
        score = 95.0
        label_extra = "صف/فشار خرید غالب"
    elif bid <= 0 and ask > 0:
        score = 10.0
        label_extra = "فشار فروش غالب"
    elif ratio >= strong_bid:
        score = 90.0
        label_extra = "تقاضای بسیار قوی در عمق"
    elif ratio >= mild_bid:
        score = 72.0
        label_extra = "تقاضا قوی‌تر از عرضه"
    elif ratio <= strong_ask:
        score = 20.0
        label_extra = "عرضه بسیار سنگین"
    elif ratio < 1.0:
        score = 38.0
        label_extra = "عرضه بیشتر از تقاضا"
    else:
        score = 55.0
        label_extra = "تعادل نسبی عمق"

    # best level imbalance bonus/malus
    bb = quote.orderbook.best_bid
    ba = quote.orderbook.best_ask
    if bb and ba and bb.price > 0 and ba.price > 0:
        spread_pct = (ba.price - bb.price) / bb.price * 100
        if spread_pct < 0.05:
            score = clamp(score + 3)
        elif spread_pct > 0.5:
            score = clamp(score - 5)

    reasons = [
        label_extra,
        f"نسبت حجم تقاضا به عرضه در ۵ سطح: {ratio:.2f}",
    ]
    if bb and ba:
        reasons.append(f"بهترین خرید {bb.price:,.0f} / بهترین فروش {ba.price:,.0f}")

    return FactorScore(
        key="orderbook_pressure",
        title="فشار پیش‌سفارش",
        score=clamp(score),
        label=label_from_score(score),
        reasons=tuple(reasons),
        metrics={
            "bid_qty": bid,
            "ask_qty": ask,
            "bid_ask_ratio": round(ratio, 4),
            "best_bid": bb.price if bb else None,
            "best_ask": ba.price if ba else None,
        },
    )
