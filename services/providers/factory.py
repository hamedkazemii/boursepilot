"""ساخت provider فعال از روی تنظیمات — با پشتیبانی Gateway و Demo Mode.

اولویت:
1. gateway — اگر MARKET_GATEWAY_URL تنظیم شده باشد
2. brs — اگر BRS_API_KEY معتبر باشد  
3. demo — اگر هیچ‌کدام در دسترس نباشد (بدون کرش)
"""

from __future__ import annotations

import logging
from typing import Optional

from config import settings
from services.providers.base import MarketDataProvider
from services.providers.brs_provider import BrsProvider
from services.providers.exceptions import ProviderConfigError
from services.providers.gateway_provider import MarketGatewayProvider

logger = logging.getLogger(__name__)


class DemoProvider:
    """Provider دمو — وقتی هیچ provider واقعی در دسترس نیست."""

    name = "demo"

    def get_all_symbols(self, symbol_type=None):
        from services.providers.models import SymbolQuote
        return []

    def get_fund_symbols(self, symbol_type=None):
        return []

    def get_symbol(self, symbol):
        raise ProviderConfigError("سیستم در حالت دمو است. داده بازار در دسترس نیست.")

    def get_nav(self, symbol):
        raise ProviderConfigError("سیستم در حالت دمو است. NAV در دسترس نیست.")

    def get_shareholders(self, symbol):
        return []


def get_market_data_provider(name: Optional[str] = None) -> MarketDataProvider:
    """
    Factory برای MarketDataProvider با-firstلback هوشمند.

    اولویت:
    1. gateway — اگر MARKET_GATEWAY_URL تنظیم شده
    2. brs — اگر BRS_API_KEY معتبر باشد
    3. demo — در غیر این صورت (بدون کرش)
    """
    requested = (name or settings.MARKET_DATA_PROVIDER or "auto").strip().lower()
    logger.info("creating market data provider (requested=%s)", requested)

    # اگر gateway مشخص شده یا auto و Gateway URL موجود است
    if requested in {"gateway", "auto"}:
        if settings.MARKET_GATEWAY_URL:
            try:
                provider = MarketGatewayProvider()
                if provider.is_available:
                    logger.info("provider selected: gateway (%s)", settings.MARKET_GATEWAY_URL)
                    return provider
            except Exception as exc:  # noqa: BLE001
                logger.warning("gateway init failed: %s", exc)
        if requested == "gateway":
            logger.warning("gateway requested but MARKET_GATEWAY_URL not set — falling back")

    # BRS fallback
    if requested in {"brs", "brsapi", "brs_api", "auto"}:
        if settings.BRS_API_KEY and settings.BRS_API_KEY != "***":
            try:
                provider = BrsProvider()
                logger.info("provider selected: brs")
                return provider
            except Exception as exc:  # noqa: BLE001
                logger.warning("brs init failed: %s", exc)
        if requested in {"brs", "brsapi", "brs_api"}:
            logger.warning("brs requested but BRS_API_KEY not set — falling back")

    # Demo mode — آخرین راه
    logger.warning("no live provider available — switching to DEMO mode")
    return DemoProvider()


def get_provider_status() -> dict:
    """وضعیت providerها برای نمایش در status/debug."""
    return {
        "gateway": {
            "configured": bool(settings.MARKET_GATEWAY_URL),
            "url": settings.MARKET_GATEWAY_URL or None,
        },
        "brs": {
            "configured": bool(settings.BRS_API_KEY and settings.BRS_API_KEY != "***"),
        },
        "active": settings.MARKET_DATA_PROVIDER,
    }
