"""تست پروفایل/پرتفو و AI advisor."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.ai.advisor import AIAdvisor
from core.database.connection import Database
from core.scoring.models import FactorScore, FundAssessment
from services.portfolio.service import PortfolioService


def _ranked() -> list[FundAssessment]:
    out = []
    for i, (sym, ft, sc) in enumerate([
        ("عیار", "طلا", 88), ("زر", "طلا", 80), ("دارا", "سهامی", 75),
        ("یاقوت", "درآمد ثابت", 70), ("موج", "اهرم", 40), ("آریا", "اهرم", 25),
    ], 1):
        out.append(FundAssessment(
            symbol=sym, name=sym, fund_type=ft, ins_code=str(i), sector=ft,
            final_score=sc, recommendation="buy" if sc > 60 else "sell",
            recommendation_label="خرید" if sc > 60 else "فروش", rank=i,
            factors=(FactorScore("liquidity", "نقدشوندگی", sc, "x", ("r",)),),
            summary_reasons=(f"امتیاز نسبی {sc}", f"نقطه {'قوت' if sc>60 else 'ضعف'} — تست"),
            change_pct=1 if sc > 60 else -2,
        ))
    return out


class TestPortfolioAI(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "t.db")
        self.pf = PortfolioService(self.db)
        self.ai = AIAdvisor(self.db)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_user_portfolio_flow(self) -> None:
        u = self.pf.ensure_user("12345", username="ham", first_name="H")
        self.assertEqual(u["telegram_id"], "12345")
        self.pf.update_profile("12345", risk_profile="low", capital=50_000_000, horizon_months=12)
        self.pf.upsert_holding("12345", "عیار", quantity=100, avg_cost=25000)
        data = self.pf.get_portfolio("12345")
        self.assertEqual(len(data["items"]), 1)
        text = self.pf.portfolio_summary_text("12345", prices={"عیار": 26000})
        self.assertIn("عیار", text)
        self.assertIn("PnL", text)

    def test_ai_learn_and_answer(self) -> None:
        ranked = _ranked()
        lessons = self.ai.learn_from_ranking(ranked, market={"market_status": "مثبت", "market_power": 70})
        self.assertTrue(lessons)
        ans = self.ai.answer("۵۰ میلیون ریسک کم یک‌ساله", user={"risk_profile": "low", "capital": 5e7}, ranked=ranked)
        self.assertIn("پیشنهاد", ans)
        ans2 = self.ai.answer("برترین‌ها", ranked=ranked)
        self.assertIn("عیار", ans2)
        ans3 = self.ai.answer("ضعیف‌ها", ranked=ranked)
        self.assertIn("آریا", ans3)


if __name__ == "__main__":
    unittest.main()
