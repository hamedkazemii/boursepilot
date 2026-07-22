"""تست تلگرام بدون شبکه واقعی."""

from __future__ import annotations

import unittest
from typing import Any, Optional
from unittest.mock import MagicMock

from core.scoring.models import FactorScore, FundAssessment
from core.preopen.analyzer import PreopenSignal
from services.telegram import TelegramService, chunk_text
from services.telegram_publisher import (
    TelegramPublisher,
    format_fund_telegram,
    format_preopen_telegram,
    format_ranking_telegram,
)


def _sample_assessment(symbol: str = "عیار", score: float = 77.0, rank: int = 1) -> FundAssessment:
    return FundAssessment(
        symbol=symbol,
        name=f"صندوق {symbol}",
        fund_type="طلا",
        ins_code="1",
        sector="صندوق",
        final_score=score,
        recommendation="buy",
        recommendation_label="خرید",
        rank=rank,
        factors=(
            FactorScore(
                key="liquidity",
                title="نقدشوندگی",
                score=80,
                label="خوب",
                reasons=("عمق مناسب است",),
            ),
        ),
        summary_reasons=(
            f"امتیاز نهایی {score:.1f} → توصیه: خرید",
            "نقطه قوت — نقدشوندگی: عمق مناسب است",
        ),
        change_pct=1.5,
        volume=1000,
        value=1e9,
        premium_pct=-0.4,
    )


class TestTelegramChunk(unittest.TestCase):
    def test_short(self) -> None:
        self.assertEqual(chunk_text("سلام", 10), ["سلام"])

    def test_chunk_lines(self) -> None:
        text = "\n".join([f"line-{i}" for i in range(50)])
        parts = chunk_text(text, 40)
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 40 for p in parts))
        self.assertEqual("\n".join(parts), text)


class TestTelegramService(unittest.TestCase):
    def test_not_configured_prints(self) -> None:
        svc = TelegramService(bot_token="", chat_id="")
        self.assertFalse(svc.configured)
        self.assertFalse(svc.send_message("test"))

    def test_send_ok(self) -> None:
        session = MagicMock()
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.text = "{}"
        session.post.return_value = resp
        svc = TelegramService(bot_token="TOKEN", chat_id="-100123", session=session)
        self.assertTrue(svc.send_message("hello\nworld"))
        self.assertTrue(session.post.called)
        args, kwargs = session.post.call_args
        self.assertIn("sendMessage", args[0])
        self.assertEqual(kwargs["json"]["chat_id"], "-100123")


class TestPublisherFormat(unittest.TestCase):
    def test_ranking_format(self) -> None:
        ranked = [_sample_assessment("عیار", 80, 1), _sample_assessment("اهرم", 40, 2)]
        text = format_ranking_telegram(ranked, meta={"generated_at": "t"})
        self.assertIn("رنکینگ", text)
        self.assertIn("عیار", text)
        self.assertIn("برترین", text)

    def test_preopen_format(self) -> None:
        sig = PreopenSignal(
            symbol="عیار",
            name="x",
            fund_type="طلا",
            bid_qty=100,
            ask_qty=10,
            ratio=10,
            bias="buy_pressure",
            bias_label="فشار خرید قوی",
            score=88,
            reasons=("a", "b", "c"),
            best_bid=1,
            best_ask=2,
            change_pct=1.0,
        )
        text = format_preopen_telegram([sig])
        self.assertIn("پیش‌سفارش", text)
        self.assertIn("عیار", text)

    def test_fund_format(self) -> None:
        text = format_fund_telegram(_sample_assessment())
        self.assertIn("عیار", text)
        self.assertIn("نقدشوندگی", text)

    def test_publisher_uses_service(self) -> None:
        tg = MagicMock()
        tg.send_message.return_value = True
        pub = TelegramPublisher(telegram=tg)
        ok = pub.publish_ranking([_sample_assessment()])
        self.assertTrue(ok)
        self.assertTrue(tg.send_message.called)


if __name__ == "__main__":
    unittest.main()
