"""
ساخت provider فعال از روی تنظیمات.

فعلاً فقط brs؛ مسیر توسعه برای providerهای بعدی باز است.
"""

from __future__ import annotations

import logging
from typing import Optional

from config import settings
from services.providers.base import MarketDataProvider
from services.providers.brs_provider import BrsProvider
from services.providers.exceptions import ProviderConfigError

logger = logging.getLogger(__name__)


def get_market_data_provider(name: Optional[str] = None) -> MarketDataProvider:
    """
    Factory برای MarketDataProvider.

    name: brs (پیش‌فرض از settings.MARKET_DATA_PROVIDER)
    """
    provider_name = (name or settings.MARKET_DATA_PROVIDER or "brs").strip().lower()
    logger.info("creating market data provider: %s", provider_name)

    if provider_name in {"brs", "brsapi", "brs_api"}:
        return BrsProvider()

    raise ProviderConfigError(
        f"provider ناشناخته: {provider_name!r}. مقدار مجاز در این فاز: brs"
    )
