"""
Adapter قدیمی TSETMC.

مسیر اصلی محصول صندوقچی: BrsProvider.
این کلاس فقط برای سازگاری/آینده نگه داشته شده و در فاز API فعال نیست.
"""

from __future__ import annotations


class TSETMCProvider:
    """غیرفعال — از BrsProvider استفاده کنید."""

    name = "tsetmc"

    def get_symbol_data(self, symbol: str):
        raise NotImplementedError(
            "TSETMCProvider در مسیر اصلی صندوقچی استفاده نمی‌شود. "
            "از services.providers.BrsProvider یا get_market_data_provider() استفاده کنید."
        )
