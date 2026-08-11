"""
کلاینت HTTP سطح پایین BrsApi.ir

- کلید فقط از config/env
- User-Agent مرورگر (الزام فایروال)
- بدون hardcode داده بازار
"""

from __future__ import annotations

import logging
import time
from typing import Any, Mapping, Optional
from urllib.parse import urljoin

import requests

from config import settings
from services.providers.exceptions import ProviderAuthError, ProviderConfigError, ProviderHTTPError
from services.providers.reliability import reliable_provider
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)


class BrsClient:
    """GET JSON از endpointهای Tsetmc روی BrsApi."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.BRS_API_KEY).strip()
        self.base_url = (base_url or settings.BRS_BASE_URL).rstrip("/") + "/"
        self.timeout = float(timeout if timeout is not None else settings.BRS_TIMEOUT_SECONDS)
        self.max_retries = int(max_retries if max_retries is not None else settings.BRS_MAX_RETRIES)

        if not self.api_key:
            raise ProviderConfigError(
                "BRS_API_KEY تنظیم نشده است. کلید را در محیط/secret قرار دهید."
            )

        self.session = session or requests.Session()
        self.snapshot_store = SnapshotStore()
        ua = user_agent or settings.BRS_USER_AGENT
        self.session.headers.update(
            {
                "User-Agent": ua,
                "Accept": "application/json,text/plain,*/*",
                "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def _url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        return urljoin(self.base_url, endpoint)

    @reliable_provider("brs_api")
    def get_json(
        self,
        endpoint: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        """
        درخواست GET و پارس JSON.
        """
        query: dict[str, Any] = {"key": self.api_key}
        if params:
            for k, v in params.items():
                if v is None:
                    continue
                query[k] = v

        url = self._url(endpoint)
        response = self.session.get(url, params=query, timeout=self.timeout)
        return self._parse_response(response, endpoint=endpoint)

    def fallback_get_json(self, endpoint: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        logger.info("Attempting fallback for endpoint: %s", endpoint)
        return self.snapshot_store.load_json(endpoint.replace('/', '_'))

    # CODAL Endpoints
    # ================================================================
    
    def get_codal_announcements(
        self,
        symbol: Optional[str] = None,
        category: Optional[int] = None,
        audited: Optional[bool] = None,
        unaudited: Optional[bool] = None,
        only_main_company: Optional[bool] = None,
        only_subsidiaries: Optional[bool] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        page: Optional[int] = None,
    ) -> Any:
        """
        دریافت اطلاعیه‌های کدال از endpoint Announcement.php
        
        پارامترها:
        - symbol: نماد (l18)
        - category: دسته‌بندی (۱=صندوق، ۲=شرکت، ۳=سهامداران و...)
        - audited: حسابرسی شده (true/false)
        - unaudited: حسابرسی نشده (true/false)
        - only_main_company: تنها شرکت مادر
        - only_subsidiaries: تنها شرکت‌های تابعه
        - date_start: تاریخ شروع YYYY-MM-DD
        - date_end: تاریخ پایان YYYY-MM-DD
        - page: شماره صفحه
        """
        params: dict[str, Any] = {}
        if symbol:
            params["l18"] = symbol
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
        
        # Codal endpoint is at https://Api.BrsApi.ir/Codal/Announcement.php (not under Tsetmc)
        codal_base = "https://Api.BrsApi.ir/"
        query: dict[str, Any] = {"key": self.api_key}
        for k, v in params.items():
            if v is None:
                continue
            query[k] = v
        
        url = urljoin(codal_base, "Codal/Announcement.php")
        response = self.session.get(url, params=query, timeout=self.timeout)
        return self._parse_response(response, endpoint="Codal/Announcement.php")
    
    # ================================================================
    # Tsetmc Endpoints (under /Tsetmc/)
    # ================================================================
    
    def get_all_symbols(self, symbol_type: int = 1) -> Any:
        """
        لیست تمام نمادها با قیمت لحظه‌ای.
        
        Args:
            symbol_type: 1=همه، 2=صندوق‌ها، 3=سهام
        """
        return self.get_json("Tsetmc/AllSymbols.php", {"type": symbol_type})
    
    def get_symbol(self, symbol: str) -> Any:
        """جزئیات کامل یک نماد."""
        return self.get_json("Tsetmc/Symbol.php", {"l18": symbol})
    
    def get_nav(self, symbol: str) -> Any:
        """NAV صدور/ابطال برای صندوق ETF."""
        return self.get_json("Tsetmc/Nav.php", {"l18": symbol})
    
    def get_shareholders(self, symbol: str) -> Any:
        """اطلاعات سهامداران حقیقی/حقوقی."""
        return self.get_json("Tsetmc/Shareholder.php", {"l18": symbol})
    
    def get_history(
        self,
        symbol: str,
        history_type: int = 2,  # 1=حقیقی/حقوقی، 2=قیمتی
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Any:
        """
        تاریخچه معاملات و قیمت.
        
        Args:
            symbol: نماد فارسی
            history_type: 1=داده حقیقی/حقوقی روزانه، 2=تاریخچه قیمتی روزانه (open, high, low, close, volume)
            from_date: تاریخ شروع YYYY-MM-DD
            to_date: تاریخ پایان YYYY-MM-DD
        """
        params = {"l18": symbol, "type": history_type}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        return self.get_json("Tsetmc/History.php", params)
    
    def get_candlestick(
        self,
        symbol: str,
        candlestick_type: int = 3,  # 1=لحظه‌ای، 2=روزانه تعدیل‌نشده، 3=روزانه تعدیل‌شده
        count: Optional[int] = None,
        date: Optional[str] = None,
    ) -> Any:
        """
        کندل‌های شمعی برای تحلیل تکنیکال.
        
        Args:
            symbol: نماد فارسی
            candlestick_type: 1=لحظه‌ای روز جاری، 2=روزانه تعدیل‌نشده، 3=روزانه تعدیل‌شده (پیش‌فرض)
            count: تعداد کندل (پیش‌فرض همه)
            date: تاریخ خاص YYYY-MM-DD (برای نوع 1)
        """
        params = {"l18": symbol, "type": candlestick_type}
        if count is not None:
            params["count"] = count
        if date:
            params["date"] = date
        return self.get_json("Tsetmc/Candlestick.php", params)
    
    def get_transaction(self, symbol: str) -> Any:
        """جزئیات معاملات (تیک‌به‌تیک یا خلاصه معاملات)."""
        return self.get_json("Tsetmc/Transaction.php", {"l18": symbol})
    
    # ================================================================
    # Response Parsing
    # ================================================================
    
    def _parse_response(self, response: requests.Response, endpoint: str) -> Any:
        status = response.status_code
        text_head = (response.text or "")[:300]

        # تلاش برای JSON حتی روی status غیر 200
        payload: Any
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderHTTPError(
                f"پاسخ JSON نامعتبر از BRS ({endpoint}) status={status}: {text_head}",
                status_code=status,
            ) from exc

        # الگوی خطای استاندارد BrsApi
        if isinstance(payload, dict) and payload.get("successful") is False:
            message = str(payload.get("message_error") or payload.get("status") or "BRS error")
            code = payload.get("code_http") or status
            if status in (401, 403) or code in (401, 403) or payload.get("status") == "unauthorized":
                raise ProviderAuthError(message, status_code=int(code) if code else status, payload=payload)
            raise ProviderHTTPError(message, status_code=int(code) if code else status, payload=payload)

        if status == 401 or status == 403:
            raise ProviderAuthError(
                f"دسترسی BRS رد شد status={status}",
                status_code=status,
                payload=payload,
            )

        if status >= 400:
            raise ProviderHTTPError(
                f"خطای HTTP BRS status={status} endpoint={endpoint}: {text_head}",
                status_code=status,
                payload=payload,
            )

        return payload
