"""تست واحد برای MarketGatewayProvider و GatewayClient.

تمام تست‌ها بدون دسترسی به سرور داخلی ایران اجرا می‌شوند (با Mock).
"""

from __future__ import annotations

import pytest

from services.providers.exceptions import ProviderConfigError, ProviderHTTPError, ProviderNotFoundError
from services.providers.factory import DemoProvider, get_market_data_provider
from services.providers.gateway_client import MarketGatewayClient
from services.providers.gateway_mock import MockMarketGateway
from services.providers.gateway_provider import GatewayProvider
from services.providers.models import SymbolQuote
import requests
from unittest.mock import MagicMock, patch


class MockSession:
    """Mock requests.Session for testing GatewayProvider without network."""
    
    def __init__(self, responses: dict):
        self.responses = responses
        self.last_url = None
        self.last_params = None
        self.headers = {}
    
    def get(self, url, params=None, timeout=None):
        self.last_url = url
        self.last_params = params
        # Extract endpoint from URL
        # url = "http://mock-gateway/symbols" -> endpoint = "symbols"
        # url = "http://mock-gateway/symbol/عیار" -> endpoint = "symbol/عیار"
        # url = "http://mock-gateway/nav?l18=عیار" -> endpoint = "nav"
        parts = url.split('/')
        # Get the full path after the domain
        # parts = ["http:", "", "mock-gateway", "symbols"] or ["http:", "", "mock-gateway", "symbol", "عیار"]
        if len(parts) >= 4:
            endpoint = '/'.join(parts[3:])
        else:
            endpoint = parts[-1] if parts else ""
        if '?' in endpoint:
            endpoint = endpoint.split('?')[0]
        
        class MockResponse:
            def __init__(self, data, status_code=200):
                self._data = data
                self.status_code = status_code
            
            def json(self):
                return self._data
            
            def raise_for_status(self):
                if self.status_code >= 400:
                    raise requests.exceptions.HTTPError(f"{self.status_code} Error")
        
        # Try both with and without leading slash
        if endpoint in self.responses:
            return MockResponse(self.responses[endpoint])
        if '/' + endpoint in self.responses:
            return MockResponse(self.responses['/' + endpoint])
        
        # Return 404 for unknown endpoints
        return MockResponse({"error": "not found"}, 404)


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
# Gateway Provider Tests (with Mock HTTP Session)
# ---------------------------------------------------------------------------

class TestMarketGatewayProvider:
    def _make_mock_provider(self):
        """Create GatewayProvider with mocked HTTP session."""
        mock_session = MockSession({
            "health": {"status": "ok"},
            "symbols": [
                {
                    "symbol": "عیار",
                    "name": "صندوق سرمایه‌گذاری عیار",
                    "ins_code": "123456",
                    "close_price": 12500,
                    "last_price": 12600,
                    "change_last": 150,
                    "change_last_pct": 1.2,
                    "volume": 50000,
                    "value": 625000000,
                    "trade_count": 120,
                    "is_fund_like": True,
                    "sector": "درآمد ثابت",
                    "yesterday_price": 12450,
                    "open_price": 12500,
                    "high": 12650,
                    "low": 12400,
                },
                {
                    "symbol": "یاقوت",
                    "name": "صندوق یاقوت",
                    "ins_code": "123457",
                    "close_price": 3400,
                    "last_price": 3450,
                    "change_last": 71,
                    "change_last_pct": 2.1,
                    "volume": 120000,
                    "value": 408000000,
                    "trade_count": 250,
                    "is_fund_like": True,
                    "sector": "سهامی",
                    "yesterday_price": 3379,
                    "open_price": 3400,
                    "high": 3480,
                    "low": 3350,
                },
                {
                    "symbol": "کاریزما",
                    "name": "صندوق کاریزما",
                    "ins_code": "123458",
                    "close_price": 8900,
                    "last_price": 8850,
                    "change_last": -45,
                    "change_last_pct": -0.5,
                    "volume": 30000,
                    "value": 267000000,
                    "trade_count": 80,
                    "is_fund_like": True,
                    "sector": "طلا",
                    "yesterday_price": 8895,
                    "open_price": 8900,
                    "high": 8950,
                    "low": 8800,
                },
                {
                    "symbol": "ذوب",
                    "name": "سهام ذوب آهن",
                    "ins_code": "123459",
                    "close_price": 4500,
                    "last_price": 4520,
                    "change_last": 14,
                    "change_last_pct": 0.3,
                    "volume": 200000,
                    "value": 900000000,
                    "trade_count": 400,
                    "is_fund_like": False,
                    "sector": "فلزات",
                    "yesterday_price": 4506,
                    "open_price": 4500,
                    "high": 4550,
                    "low": 4480,
                },
            ],
            "funds": [
                {
                    "symbol": "عیار",
                    "name": "صندوق سرمایه‌گذاری عیار",
                    "ins_code": "123456",
                    "close_price": 12500,
                    "last_price": 12600,
                    "change_last": 150,
                    "change_last_pct": 1.2,
                    "volume": 50000,
                    "value": 625000000,
                    "trade_count": 120,
                    "is_fund_like": True,
                    "sector": "درآمد ثابت",
                    "yesterday_price": 12450,
                    "open_price": 12500,
                    "high": 12650,
                    "low": 12400,
                },
                {
                    "symbol": "یاقوت",
                    "name": "صندوق یاقوت",
                    "ins_code": "123457",
                    "close_price": 3400,
                    "last_price": 3450,
                    "change_last": 71,
                    "change_last_pct": 2.1,
                    "volume": 120000,
                    "value": 408000000,
                    "trade_count": 250,
                    "is_fund_like": True,
                    "sector": "سهامی",
                    "yesterday_price": 3379,
                    "open_price": 3400,
                    "high": 3480,
                    "low": 3350,
                },
            ],
            "symbol/عیار": {
                "symbol": "عیار",
                "name": "صندوق سرمایه‌گذاری عیار",
                "ins_code": "123456",
                "close_price": 12500,
                "last_price": 12600,
                "change_last": 150,
                "change_last_pct": 1.2,
                "volume": 50000,
                "value": 625000000,
                "trade_count": 120,
                "is_fund_like": True,
                "sector": "درآمد ثابت",
                "yesterday_price": 12450,
                "open_price": 12500,
                "high": 12650,
                "low": 12400,
            },
            "nav": {
                "l18": "عیار",
                "issue_nav": 12400,
                "redeem_nav": 12350,
                "date": "1403/01/01",
                "time": "12:00:00",
            },
        })
        return GatewayProvider(base_url="http://mock-gateway", session=mock_session)

    def test_provider_with_mock_session(self):
        provider = self._make_mock_provider()
        assert provider.is_available is True

    def test_get_all_symbols(self):
        provider = self._make_mock_provider()
        symbols = provider.get_all_symbols()
        assert isinstance(symbols, list)
        assert len(symbols) >= 3
        assert all(isinstance(s, SymbolQuote) for s in symbols)

    def test_get_fund_symbols_filters_non_fund(self):
        provider = self._make_mock_provider()
        funds = provider.get_fund_symbols()
        symbols = [f.symbol for f in funds]
        assert "عیار" in symbols
        assert "یاقوت" in symbols
        assert "ذوب" not in symbols  # سهام معمولی

    def test_get_symbol_found(self):
        provider = self._make_mock_provider()
        quote = provider.get_symbol("عیار")
        assert quote.symbol == "عیار"
        assert quote.is_fund_like is True

    def test_get_symbol_not_found(self):
        # Create provider with empty nav response for not found
        mock_session = MockSession({
            "health": {"status": "ok"},
            "symbol/نامعتبر": {"error": "not found"},
        })
        provider = GatewayProvider(base_url="http://mock-gateway", session=mock_session)
        with pytest.raises((ProviderHTTPError, ProviderNotFoundError)):
            provider.get_symbol("نامعتبر")

    def test_get_nav(self):
        provider = self._make_mock_provider()
        nav = provider.get_nav("عیار")
        assert nav.redeem_nav is not None
        assert nav.redeem_nav > 0
        assert nav.symbol == "عیار"

    def test_unavailable_without_client(self):
        # Provider without base_url should fail availability check
        mock_session = MockSession({})  # No health endpoint
        provider = GatewayProvider(base_url="http://mock-gateway", session=mock_session)
        assert provider.is_available is False
        with pytest.raises(ProviderNotFoundError):
            provider.get_all_symbols()


# ---------------------------------------------------------------------------
# Factory & Demo Mode Tests
# ---------------------------------------------------------------------------

class TestFactoryDemoMode:
    def test_demo_provider_created_when_nothing_configured(self, monkeypatch):
        monkeypatch.setenv("MARKET_GATEWAY_URL", "")
        monkeypatch.setenv("BRS_API_KEY", "")
        # Test with a mocked environment where gateway, localdb, and BRS are not available
        with patch('services.providers.factory.GatewayProvider') as mock_gateway, \
             patch('services.providers.factory.LocalDBProvider') as mock_localdb_class, \
             patch('services.providers.factory.BrsProvider') as mock_brs_class:
            mock_gateway_instance = MagicMock()
            mock_gateway_instance.is_available = False
            mock_gateway.return_value = mock_gateway_instance
            
            mock_localdb_class.side_effect = Exception("DB not available")
            mock_brs_class.side_effect = Exception("BRS not available")
            
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
