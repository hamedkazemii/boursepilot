"""فاکتور مومنتوم / تغییر قیمت."""

from __future__ import annotations

from typing import Any

from core.factors.common import clamp, label_from_score
from core.scoring.models import FactorScore
from services.providers.models import SymbolQuote


def score_momentum(quote: SymbolQuote, cfg: dict[str, Any]) -> FactorScore:
    m = cfg.get("momentum", {})
    strong_up = float(m.get("strong_up", 2.0))
    mild_up = float(m.get("mild_up", 0.5))
    mild_down = float(m.get("mild_down", -0.5))
    strong_down = float(m.get("strong_down", -2.0))

    chg = quote.change_close_pct
    if chg is None:
        chg = quote.change_last_pct
    if chg is None:
        return FactorScore(
            key="momentum",
            title="مومنتوم",
            score=50.0,
            label="نامشخص",
            reasons=("داده تغییر قیمت در دسترس نیست",),
            metrics={},
        )

    if chg >= strong_up:
        score = 88.0
        reason = "روند روزانه صعودی قوی"
    elif chg >= mild_up:
        score = 70.0
        reason = "روند روزانه مثبت"
    elif chg <= strong_down:
        score = 18.0
        reason = "روند روزانه نزولی قوی"
    elif chg <= mild_down:
        score = 35.0
        reason = "روند روزانه منفی"
    else:
        score = 52.0
        reason = "نوسان محدود حول صفر"

    # last vs close alignment
    if quote.change_last_pct is not None and quote.change_close_pct is not None:
        if quote.change_last_pct > quote.change_close_pct:
            score = clamp(score + 3)
        elif quote.change_last_pct < quote.change_close_pct - 0.3:
            score = clamp(score - 3)

    return FactorScore(
        key="momentum",
        title="مومنتوم",
        score=clamp(score),
        label=label_from_score(score),
        reasons=(reason, f"بازده/تغییر پایانی: {chg:.2f}%"),
        metrics={
            "change_close_pct": quote.change_close_pct,
            "change_last_pct": quote.change_last_pct,
        },
    )
