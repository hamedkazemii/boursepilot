"""Smart Ranking — امتیاز نسبی روی کل جهان صندوق‌ها + روند تاریخی."""

from __future__ import annotations

from dataclasses import replace
from statistics import mean
from typing import Any, Optional, Sequence

from core.indicators.engine import IndicatorSnapshot
from core.scoring.models import FactorScore, FundAssessment


class SmartRanker:
    """
    رتبه‌بندی نسبی:
    - فاکتورهای لحظه‌ای (از ScoreEngine)
    - فاکتورهای روندی از IndicatorSnapshot
    - نرمال‌سازی صدکی بین همه صندوق‌های همان اجرا
    - top = بهترین‌ها، worst = بدترین‌های واقعی (نه فقط «کمی ضعیف‌تر»)
    """

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.weights = {
            "trend": 0.22,
            "momentum_hist": 0.14,
            "liquidity": 0.14,
            "money_flow": 0.12,
            "risk": 0.12,
            "technical": 0.10,
            "volume": 0.08,
            "nav": 0.08,
        }
        self.weights.update((self.config.get("smart_weights") or {}))

    def rank(
        self,
        assessments: Sequence[FundAssessment],
        indicators: Optional[dict[str, IndicatorSnapshot]] = None,
    ) -> list[FundAssessment]:
        indicators = indicators or {}
        if not assessments:
            return []

        # raw component maps symbol -> value (higher better except risk inputs handled)
        comps: dict[str, dict[str, float]] = {}
        for a in assessments:
            ind = indicators.get(a.symbol) or IndicatorSnapshot()
            fmap = {f.key: f.score for f in a.factors}
            trend = self._trend_component(ind, a)
            mom_h = self._hist_momentum(ind, a)
            risk = self._risk_component(ind, a)  # higher = safer
            technical = self._technical_component(ind)
            comps[a.symbol] = {
                "trend": trend,
                "momentum_hist": mom_h,
                "liquidity": float(fmap.get("liquidity", 50.0)),
                "money_flow": float(fmap.get("money_flow", 50.0)),
                "risk": risk,
                "technical": technical,
                "volume": float(fmap.get("volume_value", 50.0)),
                "nav": float(fmap.get("nav_premium", 50.0)),
            }

        # percentile normalize each component across universe
        keys = list(self.weights.keys())
        pct: dict[str, dict[str, float]] = {s: {} for s in comps}
        for k in keys:
            series = [(s, comps[s][k]) for s in comps]
            ranked_vals = _percentile_map(series)
            for s, v in ranked_vals.items():
                pct[s][k] = v

        out: list[FundAssessment] = []
        for a in assessments:
            p = pct[a.symbol]
            final = 0.0
            tw = 0.0
            factor_rows: list[FactorScore] = []
            # keep original factors + add smart ones
            factor_rows.extend(list(a.factors))
            labels = {
                "trend": "روند",
                "momentum_hist": "بازده تاریخی",
                "risk": "ریسک (ایمنی)",
                "technical": "تکنیکال",
            }
            for k, w in self.weights.items():
                score = p[k]
                final += score * w
                tw += w
                if k in labels:
                    factor_rows.append(
                        FactorScore(
                            key=f"smart_{k}",
                            title=labels[k],
                            score=round(score, 2),
                            label=_label(score),
                            reasons=(self._reason(k, comps[a.symbol][k], score, indicators.get(a.symbol)),),
                            metrics={"raw": comps[a.symbol][k], "percentile": score},
                        )
                    )
            final = round(final / tw * 100.0 / 100.0, 2) if tw else 50.0
            # p already 0..100
            final = round(sum(p[k] * self.weights[k] for k in keys) / sum(self.weights.values()), 2)
            rec, rec_label = self._recommend(final, indicators.get(a.symbol), a)
            reasons = self._build_reasons(a, p, comps[a.symbol], indicators.get(a.symbol), rec_label)
            out.append(
                replace(
                    a,
                    final_score=final,
                    recommendation=rec,
                    recommendation_label=rec_label,
                    factors=tuple(factor_rows),
                    summary_reasons=tuple(reasons),
                    extras={
                        **(a.extras or {}),
                        "smart_components": p,
                        "smart_raw": comps[a.symbol],
                        "indicator": (indicators.get(a.symbol).to_dict() if indicators.get(a.symbol) else {}),
                    },
                )
            )

        out = sorted(out, key=lambda x: x.final_score, reverse=True)
        return [replace(a, rank=i) for i, a in enumerate(out, 1)]

    def top(self, ranked: list[FundAssessment], n: int = 5) -> list[FundAssessment]:
        return ranked[: max(0, n)]

    def worst(self, ranked: list[FundAssessment], n: int = 5) -> list[FundAssessment]:
        if n <= 0 or not ranked:
            return []
        # انتهای لیست = ضعیف‌ترین‌های واقعی
        return list(reversed(ranked[-n:]))

    # ---- components ----
    def _trend_component(self, ind: IndicatorSnapshot, a: FundAssessment) -> float:
        score = 50.0
        if ind.ret_20d is not None:
            score += max(-25, min(25, ind.ret_20d * 2.0))
        if ind.ret_60d is not None:
            score += max(-15, min(15, ind.ret_60d * 0.6))
        if ind.extras.get("above_ema50"):
            score += 8
        if ind.extras.get("above_ema20"):
            score += 5
        if ind.extras.get("above_ema200"):
            score += 5
        # fallback to day change if no history
        if ind.bars < 5 and a.change_pct is not None:
            score = 50 + max(-30, min(30, a.change_pct * 8))
        return max(0.0, min(100.0, score))

    def _hist_momentum(self, ind: IndicatorSnapshot, a: FundAssessment) -> float:
        vals = [x for x in [ind.ret_1d, ind.ret_5d, ind.ret_20d] if x is not None]
        if not vals:
            return 50.0 + (a.change_pct or 0) * 5
        # weighted recent
        w = []
        if ind.ret_1d is not None:
            w.append(ind.ret_1d * 0.5)
        if ind.ret_5d is not None:
            w.append(ind.ret_5d * 0.3)
        if ind.ret_20d is not None:
            w.append(ind.ret_20d * 0.2)
        s = sum(w)
        return max(0.0, min(100.0, 50.0 + s * 3.0))

    def _risk_component(self, ind: IndicatorSnapshot, a: FundAssessment) -> float:
        # higher better (safer)
        score = 60.0
        if ind.volatility_20 is not None:
            # 10% vol -> good, 40% -> bad
            score -= max(-20, min(40, (ind.volatility_20 - 15) * 1.2))
        if ind.max_drawdown_90 is not None:
            # dd is negative
            score += max(-30, min(10, ind.max_drawdown_90))  # -20 dd => -20
        if ind.sharpe_60 is not None:
            score += max(-10, min(20, ind.sharpe_60 * 8))
        # leveraged funds inherently riskier if named
        if "اهرم" in (a.fund_type or "") or "اهرم" in (a.name or ""):
            score -= 8
        return max(0.0, min(100.0, score))

    def _technical_component(self, ind: IndicatorSnapshot) -> float:
        score = 50.0
        if ind.rsi14 is not None:
            # sweet spot 45-65
            if 45 <= ind.rsi14 <= 65:
                score += 15
            elif ind.rsi14 < 30:
                score += 5  # oversold bounce potential but risky
            elif ind.rsi14 > 75:
                score -= 10
            else:
                score += (ind.rsi14 - 50) * 0.3
        hist = ind.extras.get("macd_hist")
        if isinstance(hist, (int, float)):
            score += 8 if hist > 0 else -8
        if ind.ema20 and ind.ema50:
            score += 8 if ind.ema20 >= ind.ema50 else -8
        return max(0.0, min(100.0, score))

    def _recommend(
        self,
        final: float,
        ind: Optional[IndicatorSnapshot],
        a: FundAssessment,
    ) -> tuple[str, str]:
        # trend-aware recommendation
        trend_up = False
        trend_down = False
        if ind:
            if (ind.ret_20d or 0) > 2 and ind.extras.get("above_ema50"):
                trend_up = True
            if (ind.ret_20d or 0) < -2 and not ind.extras.get("above_ema50"):
                trend_down = True
        if final >= 80 and trend_up:
            return "strong_buy", "خرید قوی"
        if final >= 70 and not trend_down:
            return "buy", "خرید"
        if final >= 55:
            return "hold", "نگهداری"
        if final >= 40:
            return "reduce", "کاهش"
        if trend_down or final < 30:
            return "sell", "فروش"
        return "reduce", "کاهش"

    def _build_reasons(
        self,
        a: FundAssessment,
        pct: dict[str, float],
        raw: dict[str, float],
        ind: Optional[IndicatorSnapshot],
        rec_label: str,
    ) -> list[str]:
        reasons = [f"امتیاز نسبی {a.final_score if False else round(sum(pct[k]*self.weights[k] for k in self.weights)/sum(self.weights.values()),1)} → {rec_label}"]
        # fix: use computed later; rebuild simple
        final = round(sum(pct[k] * self.weights[k] for k in self.weights) / sum(self.weights.values()), 1)
        reasons = [f"امتیاز نسبی میان صندوق‌ها: {final} → توصیه: {rec_label}"]

        # ordered components
        ordered = sorted(pct.items(), key=lambda kv: kv[1], reverse=True)
        weak_ordered = sorted(pct.items(), key=lambda kv: kv[1])
        names = {
            "trend": "روند",
            "momentum_hist": "بازده تاریخی",
            "liquidity": "نقدشوندگی",
            "money_flow": "جریان پول",
            "risk": "ایمنی/ریسک",
            "technical": "تکنیکال",
            "volume": "حجم",
            "nav": "NAV",
        }
        if final >= 55:
            for k, v in ordered[:3]:
                reasons.append(f"نقطه قوت نسبی — {names.get(k,k)}: صدک {v:.0f}")
            if ind and ind.ret_20d is not None:
                reasons.append(f"بازده ۲۰روزه: {ind.ret_20d:+.2f}%")
            if ind and ind.volume_ratio is not None and ind.volume_ratio >= 1.5:
                reasons.append(f"حجم امروز {ind.volume_ratio:.1f}× میانگین ۲۰روزه")
        else:
            for k, v in weak_ordered[:3]:
                reasons.append(f"نقطه ضعف نسبی — {names.get(k,k)}: صدک {v:.0f}")
            if ind and ind.ret_20d is not None:
                reasons.append(f"بازده ۲۰روزه: {ind.ret_20d:+.2f}%")
            if ind and ind.max_drawdown_90 is not None:
                reasons.append(f"حداکثر افت ۹۰روزه: {ind.max_drawdown_90:.1f}%")
            if ind and ind.rsi14 is not None and ind.rsi14 < 40:
                reasons.append(f"RSI پایین ({ind.rsi14:.0f}) — مومنتوم ضعیف")
        return reasons[:6]

    def _reason(self, key: str, raw: float, pct: float, ind: Optional[IndicatorSnapshot]) -> str:
        if key == "trend" and ind and ind.ret_20d is not None:
            return f"بازده ۲۰روزه {ind.ret_20d:+.2f}% / صدک {pct:.0f}"
        if key == "risk" and ind and ind.volatility_20 is not None:
            return f"نوسان ۲۰روزه {ind.volatility_20:.1f}% / صدک ایمنی {pct:.0f}"
        if key == "technical" and ind and ind.rsi14 is not None:
            return f"RSI={ind.rsi14:.0f} / صدک {pct:.0f}"
        return f"مقدار خام {raw:.1f} → صدک {pct:.0f}"


def _percentile_map(series: list[tuple[str, float]]) -> dict[str, float]:
    """Return 0..100 percentile rank (average rank for ties). Higher raw => higher percentile."""
    if not series:
        return {}
    if len(series) == 1:
        return {series[0][0]: 50.0}
    sorted_s = sorted(series, key=lambda x: x[1])
    n = len(sorted_s)
    out: dict[str, float] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_s[j + 1][1] == sorted_s[i][1]:
            j += 1
        # average rank of ties
        avg_rank = (i + j) / 2.0
        pct = avg_rank / (n - 1) * 100.0
        for k in range(i, j + 1):
            out[sorted_s[k][0]] = pct
        i = j + 1
    return out


def _label(score: float) -> str:
    if score >= 75:
        return "عالی"
    if score >= 60:
        return "خوب"
    if score >= 45:
        return "متوسط"
    if score >= 30:
        return "ضعیف"
    return "خیلی ضعیف"
