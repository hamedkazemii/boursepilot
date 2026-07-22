"""
قرارداد واحد داده بازار.

هسته تحلیل / اسکنر / رنکینگ فقط با این Protocol کار می‌کند.
پیاده‌سازی فعلی: BrsProvider
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from services.providers.models import (
    NavData,
    ShareholderRow,
    SymbolQuote,
)


@runtime_checkable
class MarketDataProvider(Protocol):
    """اینترفیس مشترک providerهای داده بازار."""

    name: str

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        """لیست نقل‌قول نمادها (برای کشف صندوق‌های قابل معامله)."""
        ...

    def get_symbol(self, symbol: str) -> SymbolQuote:
        """جزئیات یک نماد با l18."""
        ...

    def get_nav(self, symbol: str) -> NavData:
        """NAV صدور/ابطال صندوق."""
        ...

    def get_shareholders(self, symbol: str) -> list[ShareholderRow]:
        """سهامداران عمده (در صورت پشتیبانی provider)."""
        ...

    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        """زیرمجموعه صندوق‌مانند از get_all_symbols."""
        ...
