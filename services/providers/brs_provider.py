"""
پیاده‌سازی MarketDataProvider روی BrsApi.ir

Endpointهای استفاده‌شده:
- AllSymbols.php?key=&type=
- Symbol.php?key=&l18=
- Nav.php?key=&l18=
- Shareholder.php?key=&l18=
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from config import settings
from services.providers.brs_client import BrsClient
from services.providers.brs_mapper import (map_nav, map_shareholders,
                                           map_symbol_quote)
from services.providers.exceptions import (ProviderHTTPError,
                                           ProviderNotFoundError)
from services.providers.models import NavData, ShareholderRow, SymbolQuote
from services.providers.textnorm import normalize_symbol

logger = logging.getLogger(__name__)


class BrsProvider:
    """Provider رسمی داده بازار صندوقچی."""

    name = "brs"

    def __init__(self, client: Optional[BrsClient] = None) -> None:
        self.client = client or BrsClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        """
        دریافت همه نمادها.

        symbol_type پیش‌فرض از settings.BRS_ALL_SYMBOLS_TYPE (معمولاً 1).
        """
        stype = settings.BRS_ALL_SYMBOLS_TYPE if symbol_type is None else int(symbol_type)
        logger.info("BRS AllSymbols type=%s", stype)
        payload = self.client.get_json("AllSymbols.php", params={"type": stype})
        rows = self._ensure_list(payload, context="AllSymbols")
        quotes: list[SymbolQuote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                quotes.append(map_symbol_quote(row))
            except Exception as exc:  # noqa: BLE001 - یک ردیف خراب کل لیست را نمی‌خواباند
                logger.exception("skip bad AllSymbols row: %s", exc)
        logger.info("BRS AllSymbols mapped=%s", len(quotes))
        return quotes

    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        """فیلتر صندوق‌مانند (~۴۰۰) از AllSymbols."""
        all_quotes = self.get_all_symbols(symbol_type=symbol_type)
        funds = [q for q in all_quotes if q.is_fund_like]
        logger.info("BRS fund-like symbols=%s / total=%s", len(funds), len(all_quotes))
        return funds

    def get_symbol(self, symbol: str) -> SymbolQuote:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Symbol l18=%s", symbol_n)
        payload = self.client.get_json("Symbol.php", params={"l18": symbol_n})
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسخ Symbol.php نامعتبر است", payload=payload)
        # اگر error-like باشد client معمولاً raise کرده
        quote = map_symbol_quote(payload)
        if not quote.symbol:
            raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
        return quote

    def get_nav(self, symbol: str) -> NavData:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Nav l18=%s", symbol_n)
        payload = self.client.get_json("Nav.php", params={"l18": symbol_n})
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"NAV پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسخ Nav.php نامعتبر است", payload=payload)
        return map_nav(symbol_n, payload)

    def get_shareholders(self, symbol: str) -> list[ShareholderRow]:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Shareholder l18=%s", symbol_n)
        payload = self.client.get_json("Shareholder.php", params={"l18": symbol_n})
        return map_shareholders(payload)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_list(payload: Any, context: str) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            # بعضی نسخه‌ها ممکن است data/list داشته باشند
            for key in ("data", "items", "result", "symbols"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            raise ProviderHTTPError(f"پاسخ {context} لیست نیست", payload=payload)
        raise ProviderHTTPError(f"پاسخ {context} نامعتبر است", payload=payload)
