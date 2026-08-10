from __future__ import annotations
import os
"""Factory for market data provider with Gateway, LocalDB, BRS, Demo fallback."""

import logging
from typing import Optional

from config import settings
from services.providers.base import MarketDataProvider
from services.providers.brs_provider import BrsProvider
from services.providers.exceptions import ProviderConfigError
from services.providers.gateway_provider import GatewayProvider
from services.providers.localdb_provider import LocalDBProvider

logger = logging.getLogger(__name__)


class DemoProvider:
    name = "demo"

    def get_all_symbols(self, symbol_type=None):
        from services.providers.models import SymbolQuote
        return []

    def get_fund_symbols(self, symbol_type=None):
        return []

    def get_symbol(self, symbol):
        raise ProviderConfigError("Demo mode: market data not available.")

    def get_nav(self, symbol):
        raise ProviderConfigError("Demo mode: NAV not available.")

    def get_shareholders(self, symbol):
        return []


def get_market_data_provider(name: Optional[str] = None) -> MarketDataProvider:
    requested = (name or os.getenv("MARKET_DATA_PROVIDER") or settings.MARKET_DATA_PROVIDER or "auto").strip().lower()
    logger.info("creating market data provider (requested=%s)", requested)

    if requested in {"gateway", "auto"}:
        if settings.MARKET_GATEWAY_URL:
            try:
                provider = GatewayProvider()
                if provider.is_available:
                    logger.info("provider selected: gateway (%s)", settings.MARKET_GATEWAY_URL)
                    return provider
            except Exception as exc:
                logger.warning("gateway init failed: %s", exc)
        if requested == "gateway":
            logger.warning("gateway requested but MARKET_GATEWAY_URL not set")

    if requested in {"localdb", "auto"}:
        try:
            provider = LocalDBProvider()
            logger.info("provider selected: localdb")
            return provider
        except Exception as exc:
            logger.warning("localdb init failed: %s", exc)
        if requested == "localdb":
            logger.warning("localdb requested but init failed")

    if requested in {"brs", "brsapi", "brs_api", "auto"}:
        if settings.BRS_API_KEY and settings.BRS_API_KEY != "***":
            try:
                provider = BrsProvider()
                logger.info("provider selected: brs")
                return provider
            except Exception as exc:
                logger.warning("brs init failed: %s", exc)
        if requested in {"brs", "brsapi", "brs_api"}:
            logger.warning("brs requested but BRS_API_KEY not set")

    logger.warning("no live provider available — switching to DEMO mode")
    return DemoProvider()


def get_provider_status() -> dict:
    return {
        "gateway": {"configured": bool(settings.MARKET_GATEWAY_URL), "url": settings.MARKET_GATEWAY_URL or None},
        "localdb": {"configured": True},
        "brs": {"configured": bool(settings.BRS_API_KEY and settings.BRS_API_KEY != "***")},
        "active": settings.MARKET_DATA_PROVIDER,
    }