"""تست توضیح‌های جدا برای برتر/ضعیف."""

from __future__ import annotations

import unittest

from core.analytics.explain import explain_fund
from core.scoring.models import FactorScore, FundAssessment
from services.telegram.smart_report import format_top_fund_messages, format_worst_fund_messages


def _fund(symbol: str, score: float, rank: int, *, weak_momentum: bool = False) -> FundAssessment:
    mom = 30.0 if weak_momentum or score < 50 else 80.0
    liq = 40.0 if score < 50 else 85.0
    flow = 35.0 if score < 50 else 70.0
    return FundAssessment(
        symbol=symbol,
        name=f"صندوق {symbol}",
        fund_type="طلا" if score >= 50 else "سهامی",
        ins_code=str(rank),
        sector="صندوق",
        final_score=score,
        recommendation="buy" if score >= 65 else "sell",
        recommendation_label="خرید" if score >= 65 else "فروش",
        rank=rank,
        factors=(
            FactorScore("liquidity", "نقدشوندگی", liq, "خوب" if liq >= 65 else "ضعیف", ("عمق بازار",)),
            FactorScore("momentum", "مومنتوم", mom, "قوی" if mom >= 65 else "منفی", ("روند روز",)),
            FactorScore("money_flow", "جریان پول", flow, "متوسط", ("خالص خرید",)),
        ),
        summary_reasons=(
            f"امتیاز نهایی {score:.1f} → توصیه: {'خرید' if score >= 65 else 'فروش'}",
            "نقطه قوت — نقدشوندگی: عمق بازار" if score >= 65 else "نقطه ضعف — مومنتوم: روند روز",
        ),
        change_pct=1.8 if score >= 65 else -1.7,
        volume=1_000_000,
        value=1e10,
        premium_pct=-0.4 if score >= 65 else 1.5,
    )


class TestExplain(unittest.TestCase):
    def test_worst_focuses_on_weakness(self) -> None:
        a = _fund("ضعیف", 35, 20, weak_momentum=True)
        reasons = explain_fund(a, kind="worst")
        blob = "\n".join(reasons)
        self.assertTrue(any("ضعف" in r or "پایین" in r or "منفی" in r for r in reasons), blob)
        # نباید فقط نقطه قوت باشد
        strength_only = all("قوت" in r for r in reasons if r)
        self.assertFalse(strength_only)

    def test_top_focuses_on_strength(self) -> None:
        a = _fund("عیار", 88, 1)
        reasons = explain_fund(a, kind="top")
        blob = "\n".join(reasons)
        self.assertIn("قوت", blob)

    def test_cards_differ_for_top_and_worst(self) -> None:
        ranked = [
            _fund("عیار", 88, 1),
            _fund("زر", 80, 2),
            _fund("موج", 40, 3, weak_momentum=True),
            _fund("کم‌ریسک", 30, 4, weak_momentum=True),
        ]
        tops = format_top_fund_messages(ranked, n=2)
        worst = format_worst_fund_messages(ranked, n=2)
        self.assertIn("چرا در برترین‌هاست", tops[0])
        self.assertIn("چرا در ضعیف‌هاست", worst[0])
        self.assertIn("نقطه ضعف", worst[0])
        # کارت ضعیف نباید تیتر قوت‌محور یکسان با برتر داشته باشد
        self.assertNotEqual(tops[0], worst[0])


if __name__ == "__main__":
    unittest.main()
