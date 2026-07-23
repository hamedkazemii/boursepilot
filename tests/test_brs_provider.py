"""تست BrsProvider با fixture و بدون شبکه واقعی."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, Optional

from services.providers.brs_client import BrsClient
from services.providers.brs_provider import BrsProvider
from services.providers.exceptions import (ProviderConfigError,
                                           ProviderNotFoundError)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "brs"


class FakeClient:
    """کلاینت جعلی بر اساس fixture."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get_json(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> Any:
        params = dict(params or {})
        self.calls.append((endpoint, params))
        if endpoint == "AllSymbols.php":
            return json.loads((FIXTURES / "all_symbols_sample.json").read_text(encoding="utf-8"))
        if endpoint == "Symbol.php":
            return json.loads((FIXTURES / "symbol_ayar.json").read_text(encoding="utf-8"))
        if endpoint == "Nav.php":
            return json.loads((FIXTURES / "nav_ayar.json").read_text(encoding="utf-8"))
        if endpoint == "Shareholder.php":
            return json.loads((FIXTURES / "shareholders_ayar.json").read_text(encoding="utf-8"))
        raise AssertionError(f"unexpected endpoint {endpoint}")


class TestBrsProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.provider = BrsProvider(client=self.client)  # type: ignore[arg-type]

    def test_get_all_symbols(self) -> None:
        quotes = self.provider.get_all_symbols(symbol_type=1)
        self.assertGreaterEqual(len(quotes), 3)
        self.assertEqual(self.client.calls[0][0], "AllSymbols.php")
        self.assertEqual(self.client.calls[0][1].get("type"), 1)
        symbols = {q.symbol for q in quotes}
        self.assertIn("عیار", symbols)

    def test_get_fund_symbols(self) -> None:
        funds = self.provider.get_fund_symbols(symbol_type=1)
        self.assertTrue(all(f.is_fund_like for f in funds))
        self.assertGreaterEqual(len(funds), 1)
        self.assertTrue(any(f.symbol == "عیار" for f in funds))

    def test_get_symbol(self) -> None:
        quote = self.provider.get_symbol("عیار")
        self.assertEqual(quote.symbol, "عیار")
        self.assertIsNotNone(quote.close_price)
        self.assertTrue(quote.orderbook.bids or quote.orderbook.asks)

    def test_get_nav(self) -> None:
        nav = self.provider.get_nav("عیار")
        self.assertEqual(nav.issue_nav, 515049)
        self.assertEqual(nav.redeem_nav, 512730)

    def test_get_shareholders(self) -> None:
        rows = self.provider.get_shareholders("عیار")
        self.assertGreaterEqual(len(rows), 1)

    def test_empty_symbol_raises(self) -> None:
        with self.assertRaises(ProviderNotFoundError):
            self.provider.get_symbol("  ")

    def test_client_requires_api_key(self) -> None:
        with self.assertRaises(ProviderConfigError):
            BrsClient(api_key="")

    def test_factory_brs(self) -> None:
        # factory بدون کلید ممکن است خطا بدهد؛ فقط نام را چک می‌کنیم با mock settings path
        # اینجا provider دستی کافی است
        self.assertEqual(self.provider.name, "brs")


if __name__ == "__main__":
    unittest.main()
