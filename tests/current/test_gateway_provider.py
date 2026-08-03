"""تست واحد برای MarketGatewayProvider و GatewayClient.

تمام تست‌ها بدون دسترسی به سرور داخلی ایران اجرا می‌شوند (با Mock).
"""

from __future__ import annotations

import pytest

from services.providers.exceptions import ProviderConfigError, ProviderHTTPError, ProviderNotFoundError
from services.providers.factory import DemoProvider, get_market_data_provider
from services.providers.gateway_client import MarketGatewayClient
from services.providers.gateway_mock import MockMarketGateway
from services.providers.gateway_provider import MarketGatewayProvider
from services.providers.models import SymbolQuote


# ---------------------------------------------------------------------------
# Mock Gateway Tests
# ---------------------------------------------------------------------------

class TestMockGateway:
    def test_mock_returns_symbols(self):
        mock = MockMarketGateway()
        data = mock.get_json("symbols")
        assert isinstance(data, list)
        assert len(data) >= 3  # عیار، یاقوت، کاریزما

    def test_mock_symbol_lookup(self):
        mock = MockMarketGateway()
        data = mock.get_json("symbol", params={"l18": "عیار"})
        assert isinstance(data, dict)
        assert data["l18"] == "عیار"

    def test_mock_nav_lookup(self):
        mock = MockMarketGateway()
        data = mock.get_json("nav", params={"l18": "یاقوت"})
        assert data["psubtran"] > 0

    def test_mock_not_found(self):
        mock = MockMarketGateway()
        data = mock.get_json("symbol", params={"l18": "نامعتبر"})
        assert "error" in data


# ---------------------------------------------------------------------------
# Gateway Provider Tests (with Mock)
# ---------------------------------------------------------------------------

class TestMarketGatewayProvider:
    def test_provider_with_mock_client(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        assert provider.is_available is True

    def test_get_all_symbols(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        symbols = provider.get_all_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) >= 3
        assert all(isinstance(s, SymbolQuote) for s in symbols)

    def test_get_fund_symbols_filters_non_fund(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        funds = provider.get_fund_symbols()
        symbols = [f.symbol for f in funds]
        assert "عیار" in symbols
        assert "یاقوت" in symbols
        assert "ذوب" not in symbols  # سهام معمولی

    def test_get_symbol_found(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        quote = provider.get_symbol("عیار")
        assert quote.symbol == "عیار"
        assert quote.is_fund_like is True

    def test_get_symbol_not_found(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        with pytest.raises((ProviderHTTPError, ProviderNotFoundError)):
            provider.get_symbol("نامعتبر")

    def test_get_nav(self):
        mock = MockMarketGateway()
        provider = MarketGatewayProvider(client=mock)
        nav = provider.get_nav("عیار")
        assert nav.redeem_nav is not None
        assert nav.redeem_nav > 0
        assert nav.symbol == "عیار"

    def test_unavailable_without_client(self):
        provider = MarketGatewayProvider(client=None)
        assert provider.is_available is False
        with pytest.raises(ProviderHTTPError):
            provider.get_all_symbols()


# ---------------------------------------------------------------------------
# Factory & Demo Mode Tests
# ---------------------------------------------------------------------------

class TestFactoryDemoMode:
    def test_demo_provider_created_when_nothing_configured(self, monkeypatch):
        monkeypatch.setenv("MARKET_GATEWAY_URL", "")
        monkeypatch.setenv("BRS_API_KEY", "")
        provider = get_market_data_provider("auto")
        assert isinstance(provider, DemoProvider)
        assert provider.name == "demo"

    def test_demo_provider_methods(self):
        demo = DemoProvider()
        assert demo.get_all_symbols() == []
        assert demo.get_fund_symbols() == []
        assert demo.get_shareholders("x") == []
        with pytest.raises(ProviderConfigError):
            demo.get_symbol("x")
        with pytest.raises(ProviderConfigError):
            demo.get_nav("x")


# ---------------------------------------------------------------------------
# Gateway Client Config Tests
# ---------------------------------------------------------------------------

class TestGatewayClientConfig:
    def test_raises_when_no_url(self, monkeypatch):
        monkeypatch.setenv("MARKET_GATEWAY_URL", "")
        with pytest.raises(ProviderConfigError):
            MarketGatewayClient()

    def test_accepts_url_from_env(self):
        client = MarketGatewayClient(base_url="http://localhost:9999/api")
        assert client.base_url == "http://localhost:9999/api/"
