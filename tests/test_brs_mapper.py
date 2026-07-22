"""تست نگاشت پاسخ BRS به DTO — بدون شبکه."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from services.providers.brs_mapper import (
    is_fund_like,
    map_nav,
    map_orderbook,
    map_shareholders,
    map_symbol_quote,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "brs"


class TestBrsMapper(unittest.TestCase):
    def test_map_symbol_quote_ayar(self) -> None:
        rows = json.loads((FIXTURES / "all_symbols_sample.json").read_text(encoding="utf-8"))
        ayar = next(x for x in rows if x.get("l18") == "عیار")
        quote = map_symbol_quote(ayar)

        self.assertEqual(quote.symbol, "عیار")
        self.assertIn("عیار", quote.name)
        self.assertTrue(quote.is_fund_like)
        self.assertEqual(quote.ins_code, str(ayar["id"]))
        self.assertIsNotNone(quote.close_price)
        self.assertIsNotNone(quote.volume)
        self.assertGreater(quote.orderbook.total_bid_quantity + quote.orderbook.total_ask_quantity, 0)
        self.assertGreater(quote.money_flow.buy_real_volume, 0)

    def test_map_symbol_fixture(self) -> None:
        payload = json.loads((FIXTURES / "symbol_ayar.json").read_text(encoding="utf-8"))
        quote = map_symbol_quote(payload)
        self.assertEqual(quote.symbol, "عیار")
        self.assertEqual(quote.state, "مجاز")
        self.assertIsNotNone(quote.avg_volume_1m)
        self.assertTrue(quote.orderbook.bids)
        self.assertTrue(quote.orderbook.asks)

    def test_map_nav(self) -> None:
        payload = json.loads((FIXTURES / "nav_ayar.json").read_text(encoding="utf-8"))
        nav = map_nav("عیار", payload)
        self.assertEqual(nav.symbol, "عیار")
        self.assertEqual(nav.issue_nav, 515049)
        self.assertEqual(nav.redeem_nav, 512730)
        self.assertEqual(nav.date, "1405-04-31")

    def test_map_shareholders(self) -> None:
        payload = json.loads((FIXTURES / "shareholders_ayar.json").read_text(encoding="utf-8"))
        rows = map_shareholders(payload)
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(rows[0].name)
        self.assertGreater(rows[0].percent, 0)

    def test_orderbook_levels(self) -> None:
        payload = {
            "pd1": 100,
            "qd1": 10,
            "zd1": 2,
            "po1": 101,
            "qo1": 5,
            "zo1": 1,
            "pd2": 0,
            "qd2": 0,
            "zd2": 0,
            "po2": 0,
            "qo2": 0,
            "zo2": 0,
        }
        book = map_orderbook(payload)
        self.assertEqual(len(book.bids), 1)
        self.assertEqual(len(book.asks), 1)
        self.assertEqual(book.best_bid.price, 100)
        self.assertEqual(book.best_ask.price, 101)

    def test_is_fund_like(self) -> None:
        self.assertTrue(is_fund_like({"cs": "صندوق سرمایه گذاری قابل معامله", "l30": "x"}))
        self.assertFalse(is_fund_like({"cs": "زراعت", "l30": "هلال"}))


if __name__ == "__main__":
    unittest.main()
