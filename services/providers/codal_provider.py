"""
CodalProvider - دریافت و نرمال‌سازی اطلاعیه‌های کدال از BRS API
استفاده می‌کند از BrsClient موجود با همان credentials (API Key, Base URL)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from services.providers.brs_client import BrsClient
from services.providers.exceptions import ProviderConfigError

logger = logging.getLogger(__name__)


@dataclass
class CodalDisclosure:
    """مدل نرمال‌سازی شده برای یک اطلاعیه کدال"""
    symbol: str                    # نماد (l18)
    company_name: str              # نام شرکت/صندوق (l30)
    title: str                     # عنوان اطلاعیه
    code: str                      # کد اطلاعیه (ن-۱۰، ن-۲۰، ...)
    date_title: Optional[str]      # تاریخ عنوان (شمسی)
    date_send: str                 # تاریخ ارسال (شمسی)
    time_send: str                 # زمان ارسال
    date_publish: str              # تاریخ انتشار (شمسی)
    time_publish: str              # زمان انتشار
    link: Optional[str]            # لینک تصمیم/اطلاعیه در کدال
    link_pdf: Optional[str]        # لینک پیوست PDF
    link_excel: Optional[str]      # لینک پیوست Excel
    link_attachment: Optional[str] # لینک پیوست‌های کلی
    raw_data: dict                 # داده خام کامل برای دیباگ


class CodalProvider:
    """
    Provider برای دریافت اطلاعیه‌های کدال از BRS API.
    
    معماری:
    - استفاده از BrsClient موجود (همان API Key و Base URL)
    - متد get_latest برای آخرین اطلاعیه‌های یک نماد
    - متد get_by_symbol برای جستجوی با فیلترها
    - نرمال‌سازی خروجی به CodalDisclosure
    - Cache ساده در حافظه برای جلوگیری از درخواست تکراری
    - Graceful failure - خطای کدال نباید Market Data را خراب کند
    """
    
    def __init__(
        self,
        brs_client: Optional[BrsClient] = None,
        cache_ttl_seconds: int = 300,  # 5 دقیقه پیش‌فرض
    ) -> None:
        self._client = brs_client or BrsClient()
        self._cache: dict[str, tuple[list[CodalDisclosure], float]] = {}
        self._cache_ttl = cache_ttl_seconds
    
    def _cache_key(self, **kwargs) -> str:
        return "|".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
    
    def _get_cached(self, key: str) -> Optional[list[CodalDisclosure]]:
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: list[CodalDisclosure]) -> None:
        self._cache[key] = (data, time.time())
    
    def _normalize(self, raw: dict[str, Any]) -> CodalDisclosure:
        """تبدیل پاسخ خام BRS به مدل نرمال‌سازی شده"""
        return CodalDisclosure(
            symbol=raw.get("l18", ""),
            company_name=raw.get("l30", ""),
            title=raw.get("title", ""),
            code=raw.get("code", ""),
            date_title=raw.get("date_title"),
            date_send=raw.get("date_send", ""),
            time_send=raw.get("time_send", ""),
            date_publish=raw.get("date_publish", ""),
            time_publish=raw.get("time_publish", ""),
            link=raw.get("link"),
            link_pdf=raw.get("link_pdf"),
            link_excel=raw.get("link_excel"),
            link_attachment=raw.get("link_attachment"),
            raw_data=raw,
        )
    
    def get_latest(
        self,
        symbol: str,
        limit: int = 10,
        category: Optional[int] = 1,  # 1 = صندوق‌ها
    ) -> list[CodalDisclosure]:
        """
        آخرین اطلاعیه‌های یک نماد خاص.
        category=1 برای فیلتر فقط صندوق‌ها (اختیاری).
        """
        import time
        key = self._cache_key(method="latest", symbol=symbol, limit=limit, category=category)
        cached = self._get_cached(key)
        if cached is not None:
            return cached[:limit]
        
        try:
            # درخواست از BRS - صفحه 1، تمام فیلترها به جز نماد
            raw_response = self._client.get_codal_announcements(
                symbol=symbol,
                category=category,
                page=1,
            )
            
            announcements = raw_response.get("announcement", []) if isinstance(raw_response, dict) else []
            normalized = [self._normalize(a) for a in announcements[:limit]]
            self._set_cache(key, normalized)
            return normalized
            
        except Exception as e:
            logger.warning("Codal get_latest failed for %s: %s", symbol, e)
            # خطا نباید 시장 Data را متوقف کند
            return []
    
    def get_by_symbol(
        self,
        symbol: str,
        *,
        category: Optional[int] = None,
        audited: Optional[bool] = None,
        unaudited: Optional[bool] = None,
        only_main_company: Optional[bool] = None,
        only_subsidiaries: Optional[bool] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        page: int = 1,
    ) -> list[CodalDisclosure]:
        """
        جستجوی پیشرفته اطلاعیه‌ها با تمام فیلترهای BRS CODAL.
        """
        import time
        key = self._cache_key(
            method="by_symbol", symbol=symbol, category=category, audited=audited,
            unaudited=unaudited, only_main_company=only_main_company,
            only_subsidiaries=only_subsidiaries, date_start=date_start,
            date_end=date_end, page=page,
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        
        try:
            raw_response = self._client.get_codal_announcements(
                symbol=symbol,
                category=category,
                audited=audited,
                unaudited=unaudited,
                only_main_company=only_main_company,
                only_subsidiaries=only_subsidiaries,
                date_start=date_start,
                date_end=date_end,
                page=page,
            )
            
            announcements = raw_response.get("announcement", []) if isinstance(raw_response, dict) else []
            normalized = [self._normalize(a) for a in announcements]
            self._set_cache(key, normalized)
            return normalized
            
        except Exception as e:
            logger.warning("Codal get_by_symbol failed for %s: %s", symbol, e)
            return []
    
    def get_latest_all(self, limit: int = 20, category: int = 1) -> list[CodalDisclosure]:
        """
        آخرین اطلاعیه‌های همه نمادها (بدون فیلتر نماد).
        """
        import time
        key = self._cache_key(method="latest_all", limit=limit, category=category)
        cached = self._get_cached(key)
        if cached is not None:
            return cached[:limit]
        
        try:
            raw_response = self._client.get_codal_announcements(
                category=category,
                page=1,
            )
            
            announcements = raw_response.get("announcement", []) if isinstance(raw_response, dict) else []
            normalized = [self._normalize(a) for a in announcements[:limit]]
            self._set_cache(key, normalized)
            return normalized
            
        except Exception as e:
            logger.warning("Codal get_latest_all failed: %s", e)
            return []
    
    def clear_cache(self) -> None:
        """پاک کردن کش"""
        self._cache.clear()


# Import time for cache
import time