"""فاکتور جریان پول حقیقی/حقوقی."""

from __future__ import annotations

from typing import Any

from core.factors.common import clamp, label_from_score, safe_div
from core.scoring.models import FactorScore
from services.providers.models import SymbolQuote


def score_money_flow(quote: SymbolQuote, cfg: dict[str, Any]) -> FactorScore:
    mf_cfg = cfg.get("money_flow", {})
    strong = float(mf_cfg.get("strong_real_buy", 0.70))
    mild = float(mf_cfg.get("mild_real_buy", 0.55))

    mf = quote.money_flow
    buy_total = mf.buy_real_volume + mf.buy_legal_volume
    sell_total = mf.sell_real_volume + mf.sell_legal_volume
    real_buy_share = safe_div(mf.buy_real_volume, max(buy_total, 1.0))
    real_net = mf.buy_real_volume - mf.sell_real_volume

    # base from net real
    if sell_total + buy_total <= 0:
        score = 50.0
        reasons = ["داده جریان پول معنادار نیست"]
    else:
        # normalize net real vs total activity
        activity = max(buy_total + sell_total, 1.0)
        net_ratio = real_net / activity  # -1..1 approx
        score = clamp(50 + net_ratio * 80)
        reasons = []
        if real_net > 0:
            reasons.append("خالص خرید حقیقی مثبت است")
        elif real_net < 0:
            reasons.append("خالص خرید حقیقی منفی است")
        else:
            reasons.append("خالص خرید حقیقی نزدیک صفر است")

        if real_buy_share >= strong:
            score = clamp(score + 8)
            reasons.append("سهم حقیقی از خرید بالاست")
        elif real_buy_share >= mild:
            score = clamp(score + 3)
            reasons.append("سهم حقیقی از خرید متوسط رو به بالاست")

    return FactorScore(
        key="money_flow",
        title="جریان پول",
        score=score,
        label=label_from_score(score),
        reasons=tuple(reasons),
        metrics={
            "buy_real_volume": mf.buy_real_volume,
            "sell_real_volume": mf.sell_real_volume,
            "buy_legal_volume": mf.buy_legal_volume,
            "sell_legal_volume": mf.sell_legal_volume,
            "real_net": real_net,
            "real_buy_share": round(real_buy_share, 4),
        },
    )
