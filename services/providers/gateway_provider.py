"""Provider استاندارد برای Market Gateway داخلی.

این provider تمام درخواست‌های بازار را از طریق Gateway داخلی هدایت می‌کند.
اگر Gateway در دسترس نباشد، سیستم به‌صورت خودکار وارد Demo Mode می‌شود.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.providers.base import MarketDataProvider
from services.providers.brs_mapper import map_nav, map_shareholders, map_symbol_quote
from services.providers.exceptions import (
    ProviderConfigError,
    ProviderHTTPError,
    ProviderNotFoundError,
)
from services.providers.gateway_client import MarketGatewayClient
from services.providers.models import NavData, ShareholderRow, SymbolQuote
from services.providers.textnorm import normalize_symbol

logger = logging.getLogger(__name__)


class MarketGatewayProvider:
    """Provider رسمی داده بازار از طریق Gateway داخلی."""

    name = "gateway"

    def __init__(self, client: Optional[MarketGatewayClient] = None) -> None:
        self.client = client

    @property
    def is_available(self) -> bool:
        """آیا Gateway در دسترس است؟"""
        return self.client is not None

    # ------------------------------------------------------------------
    # Public API — MarketDataProvider Protocol
    # ------------------------------------------------------------------

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        params: dict[str, Any] = {}
        if symbol_type is not None:
            params["type"] = symbol_type
        payload = self._request("symbols", params=params)
        rows = self._ensure_list(payload, context="symbols")
        quotes: list[SymbolQuote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                quotes.append(map_symbol_quote(row))
            except Exception as exc:  # noqa: BLE001
                logger.exception("skip bad symbol row: %s", exc)
        logger.info("Gateway all_symbols mapped=%s", len(quotes))
        return quotes

    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        all_quotes = self.get_all_symbols(symbol_type=symbol_type)
        funds = [q for q in all_quotes if q.is_fund_like]
        logger.info("Gateway fund-like=%s / total=%s", len(funds), len(all_quotes))
        return funds

    def get_symbol(self, symbol: str) -> SymbolQuote:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        payload = self._request("symbol", params={"l18": symbol_n})
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسش symbol نامعتبر است", payload=payload)
        quote = map_symbol_quote(payload)
        if not quote.symbol:
            raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
        return quote

    def get_nav(self, symbol: str) -> NavData:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        payload = self._request("nav", params={"l18": symbol_n})
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"NAV پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسخ nav نامعتبر است", payload=payload)
        return map_nav(symbol_n, payload)

    def get_shareholders(self, symbol: str) -> list[ShareholderRow]:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        payload = self._request("shareholders", params={"l18": symbol_n})
        return map_shareholders(payload)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _request(self, endpoint: str, params: Optional[dict[str, Any]] = None) -> Any:
        if not self.client:
            raise ProviderHTTPError("Gateway در دسترس نیست — لطفاً Demo Mode را فعال کنید")
        return self.client.get_json(endpoint, params=params)

    @staticmethod
    def _ensure_list(payload: Any, context: str) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "items", "result", "symbols"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            raise ProviderHTTPError(f"پاسخ {context} لیست نیست", payload=payload)
        raise ProviderHTTPError(f"پاسخ {context} نامعتبر است", payload=payload)
