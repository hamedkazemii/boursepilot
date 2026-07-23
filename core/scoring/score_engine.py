"""موتور امتیاز ترکیبی چندعاملی."""

from __future__ import annotations

import logging
from typing import Any, Optional

from core.classification.fund_type import classify_fund_type
from core.factors.liquidity import score_liquidity
from core.factors.money_flow import score_money_flow
from core.factors.momentum import score_momentum
from core.factors.nav_premium import compute_premium_pct, score_nav_premium
from core.factors.orderbook_pressure import score_orderbook_pressure
from core.factors.volume_value import score_volume_value
from core.scoring.models import FactorScore, FundAssessment
from core.scoring.weights import load_scoring_config
from services.providers.models import NavData, SymbolQuote

logger = logging.getLogger(__name__)


class ScoreEngine:
    """محاسبه امتیاز نهایی + توصیه + دلایل فارسی."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or load_scoring_config()
        self.weights: dict[str, float] = dict(self.config.get("weights") or {})
        self.thresholds: dict[str, float] = dict(self.config.get("recommendation_thresholds") or {})
        self.labels: dict[str, str] = dict(self.config.get("labels") or {})
        self.redistribute_missing = bool(self.config.get("redistribute_missing", True))

    def assess(self, quote: SymbolQuote, nav: Optional[NavData] = None) -> FundAssessment:
        factors = [
            score_liquidity(quote, self.config),
            score_orderbook_pressure(quote, self.config),
            score_money_flow(quote, self.config),
            score_momentum(quote, self.config),
            score_volume_value(quote, self.config),
            score_nav_premium(quote, nav, self.config),
        ]

        # اگر NAV نبود و redistribute فعال است، وزن nav حذف و بین بقیه پخش می‌شود
        usable = list(factors)
        weights = dict(self.weights)
        nav_factor = next((f for f in factors if f.key == "nav_premium"), None)
        nav_missing = (
            nav_factor is not None
            and nav_factor.metrics.get("premium_pct") is None
        )
        if nav_missing and self.redistribute_missing and "nav_premium" in weights:
            dropped = float(weights.pop("nav_premium"))
            others = [k for k in weights if k != "nav_premium"]
            if others and dropped:
                add = dropped / len(others)
                for k in others:
                    weights[k] = float(weights[k]) + add
            # keep factor for display but weight 0
            weights["nav_premium"] = 0.0

        final = self._weighted_score(usable, weights)
        rec, rec_label = self._recommend(final)
        summary = self._summary_reasons(usable, final, rec_label)

        price = quote.close_price if quote.close_price is not None else quote.last_price
        premium = compute_premium_pct(price, nav.redeem_nav if nav else None)

        return FundAssessment(
            symbol=quote.symbol,
            name=quote.name,
            fund_type=classify_fund_type(quote),
            ins_code=quote.ins_code,
            sector=quote.sector,
            final_score=final,
            recommendation=rec,
            recommendation_label=rec_label,
            factors=tuple(usable),
            summary_reasons=tuple(summary),
            close_price=quote.close_price,
            last_price=quote.last_price,
            change_pct=quote.change_close_pct if quote.change_close_pct is not None else quote.change_last_pct,
            volume=quote.volume,
            value=quote.value,
            issue_nav=nav.issue_nav if nav else None,
            redeem_nav=nav.redeem_nav if nav else None,
            premium_pct=premium,
            extras={
                "time": quote.time,
                "bid_qty": quote.orderbook.total_bid_quantity,
                "ask_qty": quote.orderbook.total_ask_quantity,
            },
        )

    def _weighted_score(self, factors: list[FactorScore], weights: dict[str, float]) -> float:
        total_w = 0.0
        acc = 0.0
        by_key = {f.key: f for f in factors}
        for key, w in weights.items():
            if key not in by_key:
                continue
            ww = float(w)
            if ww <= 0:
                continue
            acc += by_key[key].score * ww
            total_w += ww
        if total_w <= 0:
            return 50.0
        return round(acc / total_w, 2)

    def _recommend(self, score: float) -> tuple[str, str]:
        sb = float(self.thresholds.get("strong_buy", 80))
        b = float(self.thresholds.get("buy", 65))
        n = float(self.thresholds.get("neutral", 45))
        w = float(self.thresholds.get("weak", 30))
        if score >= sb:
            key = "strong_buy"
        elif score >= b:
            key = "buy"
        elif score >= n:
            key = "neutral"
        elif score >= w:
            key = "weak"
        else:
            key = "sell"
        label = self.labels.get(key, key)
        return key, label

    def _summary_reasons(self, factors: list[FactorScore], final: float, rec_label: str) -> list[str]:
        """دلایل متوازن: برای امتیاز پایین اول ضعف‌ها، برای بالا اول قوت‌ها."""
        ordered_desc = sorted(factors, key=lambda f: f.score, reverse=True)
        ordered_asc = sorted(factors, key=lambda f: f.score)
        strong = [f for f in ordered_desc if f.score >= 65]
        weak = [f for f in ordered_asc if f.score <= 45]

        reasons: list[str] = [f"امتیاز نهایی {final:.1f} → توصیه: {rec_label}"]

        # آستانه نقش: زیر 50 بیشتر ضعف‌محور
        weakness_first = final < 55 or rec_label in {
            self.labels.get("weak", "ضعیف"),
            self.labels.get("sell", "فروش"),
        }

        def line(f: FactorScore, tone: str) -> str:
            detail = f.reasons[0] if f.reasons else f.label or f"{f.score:.0f}"
            if tone == "strong":
                return f"نقطه قوت — {f.title}: {detail}"
            if tone == "weak":
                return f"نقطه ضعف — {f.title}: {detail}"
            return f"{f.title}: {detail}"

        if weakness_first:
            for f in weak[:3]:
                reasons.append(line(f, "weak"))
            for f in strong[:1]:
                reasons.append(line(f, "strong"))
            if len(reasons) < 3:
                for f in ordered_asc[:2]:
                    reasons.append(line(f, "weak" if f.score <= 55 else "neutral"))
        else:
            for f in strong[:3]:
                reasons.append(line(f, "strong"))
            for f in weak[:1]:
                reasons.append(line(f, "weak"))
            if len(reasons) < 3 and ordered_desc:
                reasons.append(line(ordered_desc[0], "strong"))

        # unique preserve order
        out: list[str] = []
        seen: set[str] = set()
        for r in reasons:
            if r not in seen:
                seen.add(r)
                out.append(r)
        return out[:5]
