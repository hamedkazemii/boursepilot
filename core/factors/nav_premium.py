"""فاکتور حباب/تخفیف نسبت به NAV."""

from __future__ import annotations

from typing import Any, Optional

from core.factors.common import clamp, label_from_score
from core.scoring.models import FactorScore
from services.providers.models import NavData, SymbolQuote


def compute_premium_pct(price: Optional[float], redeem_nav: Optional[float]) -> Optional[float]:
    if price is None or redeem_nav is None or redeem_nav == 0:
        return None
    return (float(price) - float(redeem_nav)) / float(redeem_nav) * 100.0


def score_nav_premium(
    quote: SymbolQuote,
    nav: Optional[NavData],
    cfg: dict[str, Any],
) -> FactorScore:
    np_cfg = cfg.get("nav_premium", {})
    deep_disc = float(np_cfg.get("deep_discount", -2.0))
    mild_disc = float(np_cfg.get("mild_discount", -0.5))
    mild_prem = float(np_cfg.get("mild_premium", 0.5))
    high_prem = float(np_cfg.get("high_premium", 2.0))

    price = quote.close_price if quote.close_price is not None else quote.last_price
    redeem = nav.redeem_nav if nav else None
    issue = nav.issue_nav if nav else None
    premium = compute_premium_pct(price, redeem)

    if premium is None:
        return FactorScore(
            key="nav_premium",
            title="حباب/تخفیف NAV",
            score=50.0,
            label="نامشخص",
            reasons=("NAV در دسترس نیست؛ این فاکتور خنثی در نظر گرفته شد",),
            metrics={"premium_pct": None, "issue_nav": issue, "redeem_nav": redeem, "price": price},
            # caller may drop weight
        )

    # higher score for discount (cheaper than NAV), lower for premium bubble
    if premium <= deep_disc:
        score = 90.0
        reason = "صندوق نسبت به NAV ابطال تخفیف عمیق دارد"
    elif premium <= mild_disc:
        score = 75.0
        reason = "صندوق نسبت به NAV در تخفیف است"
    elif premium >= high_prem:
        score = 20.0
        reason = "حباب/پریمیوم بالا نسبت به NAV"
    elif premium >= mild_prem:
        score = 38.0
        reason = "قیمت کمی بالاتر از NAV است"
    else:
        score = 58.0
        reason = "قیمت نزدیک به NAV است"

    return FactorScore(
        key="nav_premium",
        title="حباب/تخفیف NAV",
        score=clamp(score),
        label=label_from_score(score),
        reasons=(reason, f"اختلاف قیمت با NAV ابطال: {premium:.2f}%"),
        metrics={
            "premium_pct": round(premium, 4),
            "issue_nav": issue,
            "redeem_nav": redeem,
            "price": price,
        },
    )
