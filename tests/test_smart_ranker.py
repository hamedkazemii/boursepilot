"""تست رتبه‌بندی نسبی و اندیکاتور."""

from __future__ import annotations

import unittest

from core.indicators.engine import IndicatorEngine
from core.ranking.smart_ranker import SmartRanker
from core.scoring.models import FactorScore, FundAssessment


def _a(sym: str, score: float, chg: float, ftype: str = "سهامی") -> FundAssessment:
    return FundAssessment(
        symbol=sym,
        name=sym,
        fund_type=ftype,
        ins_code=sym,
        sector=ftype,
        final_score=score,
        recommendation="buy",
        recommendation_label="خرید",
        factors=(
            FactorScore("liquidity", "نقدشوندگی", score, "x", ("r",)),
            FactorScore("money_flow", "جریان پول", score - 5, "x", ("r",)),
            FactorScore("momentum", "مومنتوم", 50 + chg * 5, "x", ("r",)),
            FactorScore("volume_value", "حجم", score, "x", ("r",)),
            FactorScore("nav_premium", "NAV", 50, "x", ("r",)),
            FactorScore("orderbook_pressure", "سفارش", 50 + chg, "x", ("r",)),
        ),
        summary_reasons=(),
        change_pct=chg,
    )


class TestIndicators(unittest.TestCase):
    def test_compute_from_series(self) -> None:
        rows = []
        px = 100.0
        for i in range(80):
            px *= 1.01 if i % 3 else 0.995
            rows.append({
                "trade_date": f"2026-01-{(i%28)+1:02d}",
                "close_price": px,
                "high_price": px * 1.01,
                "low_price": px * 0.99,
                "volume": 1000 + i * 10,
            })
        ind = IndicatorEngine().compute(rows)
        self.assertGreater(ind.bars, 50)
        self.assertIsNotNone(ind.ema20)
        self.assertIsNotNone(ind.rsi14)
        self.assertIsNotNone(ind.ret_20d)


class TestSmartRanker(unittest.TestCase):
    def test_top_not_equal_worst_and_order(self) -> None:
        assessments = [
            _a("A", 90, 2.0, "طلا"),
            _a("B", 80, 1.0, "طلا"),
            _a("C", 70, 0.2, "سهامی"),
            _a("D", 60, -0.5, "سهامی"),
            _a("E", 40, -1.5, "اهرم"),
            _a("F", 30, -2.5, "اهرم"),
            _a("G", 20, -3.0, "درآمد ثابت"),
            _a("H", 10, -3.5, "درآمد ثابت"),
        ]
        # build simple indicators favoring A/B
        from core.indicators.engine import IndicatorSnapshot
        inds = {}
        for i, a in enumerate(assessments):
            inds[a.symbol] = IndicatorSnapshot(
                as_of_date="2026-07-23",
                ret_1d=a.change_pct,
                ret_5d=a.change_pct * 2,
                ret_20d=a.change_pct * 4,
                ema20=100,
                ema50=100 - i,
                rsi14=60 - i * 5,
                volatility_20=10 + i * 3,
                max_drawdown_90=-5 - i * 2,
                sharpe_60=1.2 - i * 0.2,
                bars=60,
                extras={"above_ema20": i < 3, "above_ema50": i < 2, "above_ema200": i < 1, "macd_hist": 1 - i * 0.3},
            )
        ranked = SmartRanker().rank(assessments, indicators=inds)
        self.assertEqual(len(ranked), 8)
        self.assertEqual(ranked[0].rank, 1)
        self.assertEqual(ranked[-1].rank, 8)
        self.assertGreater(ranked[0].final_score, ranked[-1].final_score + 10)
        top = SmartRanker().top(ranked, 3)
        worst = SmartRanker().worst(ranked, 3)
        top_syms = {a.symbol for a in top}
        worst_syms = {a.symbol for a in worst}
        self.assertTrue(top_syms.isdisjoint(worst_syms))
        # worst scores must be the lowest
        self.assertTrue(max(a.final_score for a in worst) < min(a.final_score for a in top))


if __name__ == "__main__":
    unittest.main()
