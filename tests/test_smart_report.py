"""تست فرمت گزارش هوشمند چندپیامی."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from core.scoring.models import FactorScore, FundAssessment
from services.telegram.publisher import TelegramPublisher
from services.telegram.smart_report import (
    build_smart_morning_messages,
    format_market_summary_telegram,
    format_top_fund_messages,
    format_worst_fund_messages,
)


def _a(symbol: str, score: float, rank: int, ftype: str = "طلا", chg: float = 1.0) -> FundAssessment:
    return FundAssessment(
        symbol=symbol,
        name=f"صندوق {symbol}",
        fund_type=ftype,
        ins_code=str(rank),
        sector="صندوق",
        final_score=score,
        recommendation="buy" if score >= 65 else "sell",
        recommendation_label="خرید" if score >= 65 else "فروش",
        rank=rank,
        factors=(
            FactorScore("liquidity", "نقدشوندگی", 70, "خوب", ("عمق مناسب است",)),
            FactorScore("momentum", "مومنتوم", 75, "قوی", ("روند مثبت",)),
        ),
        summary_reasons=(
            f"امتیاز نهایی {score:.1f} → توصیه: خرید",
            "نقطه قوت — نقدشوندگی: عمق مناسب است",
        ),
        change_pct=chg,
        volume=1_000_000,
        value=2e10,
        premium_pct=-0.3,
    )


class TestSmartReport(unittest.TestCase):
    def setUp(self) -> None:
        self.ranked = [
            _a("عیار", 88, 1, "طلا", 2.1),
            _a("زر", 80, 2, "طلا", 1.4),
            _a("اهرم", 72, 3, "سهامی", 0.8),
            _a("موج", 60, 4, "سهامی", -0.2),
            _a("یاقوت", 55, 5, "درآمد ثابت", 0.1),
            _a("آرام", 40, 6, "درآمد ثابت", -1.2),
            _a("کم‌ریسک", 30, 7, "درآمد ثابت", -2.0),
        ]

    def test_summary_contains_market_block(self) -> None:
        text = format_market_summary_telegram(
            self.ranked,
            meta={"generated_at": "2026-07-23T08:50:00"},
        )
        self.assertIn("صندوق بررسی شد", text)
        self.assertIn("وضعیت بازار", text)
        self.assertIn("قدرت بازار", text)
        self.assertIn("بهترین گروه", text)
        self.assertIn("ضعیف‌ترین گروه", text)
        self.assertIn("7", text)

    def test_top_and_worst_separate_messages(self) -> None:
        tops = format_top_fund_messages(self.ranked, n=5)
        worst = format_worst_fund_messages(self.ranked, n=5)
        self.assertEqual(len(tops), 5)
        self.assertEqual(len(worst), 5)
        self.assertIn("عیار", tops[0])
        self.assertIn("چرا این رتبه", tops[0])
        self.assertIn("صندوق برتر", tops[0])
        self.assertIn("صندوق ضعیف", worst[0])

    def test_build_smart_morning_message_count(self) -> None:
        msgs = build_smart_morning_messages(self.ranked, top_n=5, worst_n=5)
        # 1 summary + 5 top + 5 worst
        self.assertEqual(len(msgs), 11)
        self.assertIn("گزارش هوشمند", msgs[0])

    def test_publisher_smart_sends_many(self) -> None:
        tg = MagicMock()
        tg.send_messages.return_value = True
        pub = TelegramPublisher(telegram=tg)
        ok = pub.publish_smart_morning(self.ranked, top_n=5, worst_n=5)
        self.assertTrue(ok)
        self.assertTrue(tg.send_messages.called)
        args, _kwargs = tg.send_messages.call_args
        messages = list(args[0])
        self.assertEqual(len(messages), 11)

    def test_publisher_compact_single(self) -> None:
        tg = MagicMock()
        tg.send_message.return_value = True
        pub = TelegramPublisher(telegram=tg)
        ok = pub.publish_ranking(self.ranked, smart=False)
        self.assertTrue(ok)
        self.assertTrue(tg.send_message.called)


if __name__ == "__main__":
    unittest.main()
