"""
پیاده‌سازی MarketDataProvider روی BrsApi.ir با Quota Manager.

Endpointهای پشتیبانی شده:
- AllSymbols.php?key=&type= (1=همه، 2=صندوق‌ها، 3=سهام)
- Symbol.php?key=&l18=
- Nav.php?key=&l18=
- Shareholder.php?key=&l18=
- History.php?key=&l18=&type= (1=حقیقی/حقوقی، 2=قیمتی)
- Candlestick.php?key=&l18=&type= (1=لحظه‌ای، 2=روزانه تعدیل‌نشده، 3=روزانه تعدیل‌شده)
- Transaction.php?key=&l18=
- Codal/Announcement.php?key=&l18=&category=&...

معماری:
- تمام درخواست‌ها از طریق BrsQuotaManager عبور می‌کنند
- Rate limit: 1000 req/5min (AIO plan)
- Daily budget قابل تنظیم برای هر endpoint
- Cache، deduplication، retry با backoff
- Logging کامل مصرف quota
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

from config import settings
from services.providers.brs_client import BrsClient
from services.providers.brs_mapper import (
    map_nav,
    map_shareholders,
    map_symbol_quote,
)
from services.providers.brs_quota_manager import (
    BRSQuotaManager,
    get_quota_manager,
    QuotaExceededError,
)
from services.providers.exceptions import ProviderHTTPError, ProviderNotFoundError
from services.providers.models import NavData, ShareholderRow, SymbolQuote
from services.providers.textnorm import normalize_symbol

logger = logging.getLogger(__name__)


class BrsProvider:
    """Provider رسمی داده بازار صندوقچی با مدیریت quota."""

    name = "brs"

    @property
    def is_available(self) -> bool:
        return True

    def __init__(
        self,
        client: Optional[BrsClient] = None,
        quota_manager: Optional[BRSQuotaManager] = None,
        use_quota_manager: bool = True,
    ) -> None:
        self.client = client or BrsClient()
        self.quota_manager = quota_manager or (get_quota_manager() if use_quota_manager else None)
        self._use_quota = use_quota_manager and self.quota_manager is not None
        
        if self._use_quota:
            logger.info("BrsProvider initialized with QuotaManager")
        else:
            logger.warning("BrsProvider initialized WITHOUT QuotaManager (direct calls)")

    # ================================================================
    # Public API - All using QuotaManager
    # ================================================================

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        """
        دریافت همه نمادها با قیمت لحظه‌ای.
        
        symbol_type پیش‌فرض از settings.BRS_ALL_SYMBOLS_TYPE (معمولاً 1).
        """
        stype = settings.BRS_ALL_SYMBOLS_TYPE if symbol_type is None else int(symbol_type)
        logger.info("BRS AllSymbols type=%s", stype)
        
        if self._use_quota:
            payload = self._quota_request(
                "AllSymbols",
                {"type": stype},
                lambda url, params: self.client.get_json("Tsetmc/AllSymbols.php", params),
            )
        else:
            payload = self.client.get_json("Tsetmc/AllSymbols.php", params={"type": stype})
        
        rows = self._ensure_list(payload, context="AllSymbols")
        quotes: list[SymbolQuote] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                quotes.append(map_symbol_quote(row))
            except Exception as exc:  # noqa: BLE001
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
        """جزئیات کامل یک نماد."""
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Symbol l18=%s", symbol_n)
        
        if self._use_quota:
            payload = self._quota_request(
                "Symbol",
                {"l18": symbol_n},
                lambda url, params: self.client.get_json("Tsetmc/Symbol.php", params),
            )
        else:
            payload = self.client.get_json("Tsetmc/Symbol.php", params={"l18": symbol_n})
        
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسخ Symbol.php نامعتبر است", payload=payload)
        
        quote = map_symbol_quote(payload)
        if not quote.symbol:
            raise ProviderNotFoundError(f"نماد پیدا نشد: {symbol_n}")
        return quote

    def get_nav(self, symbol: str) -> NavData:
        """NAV صدور/ابطال برای صندوق ETF."""
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Nav l18=%s", symbol_n)
        
        if self._use_quota:
            payload = self._quota_request(
                "Nav",
                {"l18": symbol_n},
                lambda url, params: self.client.get_json("Tsetmc/Nav.php", params),
                use_cache=True,  # NAV cache 5 min
            )
        else:
            payload = self.client.get_json("Tsetmc/Nav.php", params={"l18": symbol_n})
        
        if isinstance(payload, list):
            if not payload:
                raise ProviderNotFoundError(f"NAV پیدا نشد: {symbol_n}")
            payload = payload[0]
        if not isinstance(payload, dict):
            raise ProviderHTTPError("پاسخ Nav.php نامعتبر است", payload=payload)
        return map_nav(symbol_n, payload)

    def get_shareholders(self, symbol: str) -> list[ShareholderRow]:
        """اطلاعات سهامداران حقیقی/حقوقی."""
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Shareholder l18=%s", symbol_n)
        
        if self._use_quota:
            payload = self._quota_request(
                "Shareholder",
                {"l18": symbol_n},
                lambda url, params: self.client.get_json("Tsetmc/Shareholder.php", params),
            )
        else:
            payload = self.client.get_json("Tsetmc/Shareholder.php", params={"l18": symbol_n})
        
        return map_shareholders(payload)

    def get_history(
        self,
        symbol: str,
        history_type: int = 2,  # 1=حقیقی/حقوقی، 2=قیمتی
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> list[dict]:
        """
        تاریخچه معاملات و قیمت.
        
        Returns: list of dict with keys: date, open, high, low, close, volume, value, change_pct, etc.
        """
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS History l18=%s type=%s", symbol_n, history_type)
        
        params = {"l18": symbol_n, "type": history_type}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        
        if self._use_quota:
            payload = self._quota_request(
                "History",
                params,
                lambda url, params: self.client.get_json("Tsetmc/History.php", params),
                use_cache=True,  # History cache 1 hour
            )
        else:
            payload = self.client.get_json("Tsetmc/History.php", params)
        
        return self._ensure_list(payload, context="History")

    def get_candlestick(
        self,
        symbol: str,
        candlestick_type: int = 3,  # 1=لحظه‌ای، 2=روزانه تعدیل‌نشده، 3=روزانه تعدیل‌شده
        count: Optional[int] = None,
        date: Optional[str] = None,
    ) -> list[dict]:
        """
        کندل‌های شمعی برای تحلیل تکنیکال.
        
        Returns: list of dict with keys: date, time, open, high, low, close, volume
        """
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Candlestick l18=%s type=%s", symbol_n, candlestick_type)
        
        params = {"l18": symbol_n, "type": candlestick_type}
        if count is not None:
            params["count"] = count
        if date:
            params["date"] = date
        
        if self._use_quota:
            payload = self._quota_request(
                "Candlestick",
                params,
                lambda url, params: self.client.get_json("Tsetmc/Candlestick.php", params),
                use_cache=True,  # Candlestick cache 1 hour
            )
        else:
            payload = self.client.get_json("Tsetmc/Candlestick.php", params)
        
        return self._ensure_list(payload, context="Candlestick")

    def get_transaction(self, symbol: str) -> list[dict]:
        """جزئیات معاملات (تیک‌به‌تیک یا خلاصه معاملات)."""
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ProviderNotFoundError("symbol خالی است")
        logger.info("BRS Transaction l18=%s", symbol_n)
        
        if self._use_quota:
            payload = self._quota_request(
                "Transaction",
                {"l18": symbol_n},
                lambda url, params: self.client.get_json("Tsetmc/Transaction.php", params),
            )
        else:
            payload = self.client.get_json("Tsetmc/Transaction.php", params={"l18": symbol_n})
        
        return self._ensure_list(payload, context="Transaction")

    def get_codal_announcements(
        self,
        symbol: Optional[str] = None,
        category: Optional[int] = 1,
        audited: Optional[bool] = None,
        unaudited: Optional[bool] = None,
        only_main_company: Optional[bool] = None,
        only_subsidiaries: Optional[bool] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        page: Optional[int] = 1,
    ) -> list[dict]:
        """
        دریافت اطلاعیه‌های کدال.
        
        Returns: list of dict (raw announcement data)
        """
        if symbol:
            symbol_n = normalize_symbol(symbol)
        else:
            symbol_n = None
        
        logger.info("BRS CodalAnnouncement l18=%s category=%s page=%s", symbol_n, category, page)
        
        params: dict[str, Any] = {}
        if symbol_n:
            params["l18"] = symbol_n
        if category is not None:
            params["category"] = category
        if audited is not None:
            params["audited"] = "true" if audited else "false"
        if unaudited is not None:
            params["unaudited"] = "true" if unaudited else "false"
        if only_main_company is not None:
            params["only_main_company"] = "true" if only_main_company else "false"
        if only_subsidiaries is not None:
            params["only_subsidiaries"] = "true" if only_subsidiaries else "false"
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        if page is not None:
            params["page"] = page
        
        if self._use_quota:
            payload = self._quota_request(
                "CodalAnnouncement",
                params,
                lambda url, params: self.client.get_codal_announcements(**params),
                use_cache=True,  # CODAL cache 5 min
            )
        else:
            payload = self.client.get_codal_announcements(**params)
        
        # CODAL response has {count_announcement, count_page, announcement: [...]}
        if isinstance(payload, dict) and "announcement" in payload:
            return payload["announcement"]
        elif isinstance(payload, list):
            return payload
        return []

    # ================================================================
    # Quota Manager Integration
    # ================================================================

    def _quota_request(
        self,
        endpoint_name: str,
        params: dict,
        fetcher,
        *,
        use_cache: bool = True,
        force_refresh: bool = False,
    ) -> Any:
        """اجرای درخواست از طریق QuotaManager."""
        if not self._use_quota or self.quota_manager is None:
            # Fallback to direct call
            url = f"{self.client.base_url}{endpoint_name}"
            return fetcher(url, params)
        
        try:
            return self.quota_manager.request(
                endpoint_name=endpoint_name,
                params=params,
                fetcher=fetcher,
                use_cache=use_cache,
                force_refresh=force_refresh,
            )
        except QuotaExceededError as e:
            logger.error("Quota exceeded for %s: %s", endpoint_name, e)
            # Try to return cached data if available
            if use_cache and not force_refresh:
                cache_key = self.quota_manager._build_cache_key(endpoint_name, params)
                cached = self.quota_manager._get_from_cache(cache_key, 86400)  # 24h fallback
                if cached is not None:
                    logger.warning("Returning stale cached data for %s due to quota exhaustion", endpoint_name)
                    return cached
            raise ProviderHTTPError(f"Quota exceeded for {endpoint_name}: {e}")

    def get_quota_report(self) -> dict:
        """گزارش مصرف quota."""
        if self._use_quota and self.quota_manager:
            return self.quota_manager.get_usage_report()
        return {"error": "QuotaManager not enabled"}

    def reset_quota_counters(self) -> None:
        """ریست شمارنده‌های روزانه (برای cron شبانه)."""
        if self._use_quota and self.quota_manager:
            self.quota_manager.reset_daily_counters()

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _ensure_list(payload: Any, context: str) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "items", "result", "symbols", "announcement", "candle_daily_adjusted", "candle_intraday", "candle_daily_unadjusted"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            raise ProviderHTTPError(f"پاسخ {context} لیست نیست", payload=payload)
        raise ProviderHTTPError(f"پاسخ {context} نامعتبر است", payload=payload)