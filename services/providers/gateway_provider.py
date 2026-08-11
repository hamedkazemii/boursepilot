"""
GatewayProvider — uses Iran market gateway (port 9000) instead of direct BRS.

The gateway has live market data without BRS quota limits.
Implements MarketSnapshotProvider interface.
"""

from __future__ import annotations

import logging
import requests
from typing import Any, Optional, List

from config import settings
from services.providers.models import SymbolQuote, NavData
from services.providers.exceptions import ProviderNotFoundError, ProviderHTTPError

logger = logging.getLogger(__name__)


class GatewayProvider:
    """
    Market data provider using the Iran market gateway (port 9000).

    The gateway caches live BRS data and has no daily quota limits.
    Implements MarketDataProvider interface for the collector.
    """

    name = "gateway"

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 10.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = (base_url or settings.MARKET_GATEWAY_URL).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        # Ensure headers dict exists (for mock sessions)
        if not hasattr(self.session, 'headers'):
            self.session.headers = {}
        self.session.headers.update({"User-Agent": settings.BRS_USER_AGENT})
        logger.info("GatewayProvider initialized: %s", self.base_url)

    @property
    def is_available(self) -> bool:
        """Check if gateway is reachable."""
        try:
            resp = self.session.get(f"{self.base_url}/health", timeout=3)
            return resp.status_code == 200 and resp.json().get("status") == "ok"
        except Exception:
            return False

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """GET request to gateway."""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 404:
                raise ProviderNotFoundError(f"Not found: {endpoint}")
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Gateway request failed: %s", e)
            raise ProviderHTTPError(f"Gateway error: {e}")

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> List[SymbolQuote]:
        """Get all symbols from gateway."""
        data = self._get("/symbols", params={"limit": 1000, "offset": 0})

        quotes = []
        for item in data:
            quote = self._map_to_symbol_quote(item)
            if quote:
                quotes.append(quote)

        logger.info("Gateway get_all_symbols: %d symbols", len(quotes))
        return quotes

    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> List[SymbolQuote]:
        """Get fund-like symbols from gateway."""
        data = self._get("/funds", params={"limit": 500, "offset": 0})

        quotes = []
        for item in data:
            quote = self._map_to_symbol_quote(item)
            if quote and quote.is_fund_like:
                quotes.append(quote)

        logger.info("Gateway get_fund_symbols: %d fund symbols", len(quotes))
        return quotes

    def get_symbol(self, symbol: str) -> SymbolQuote:
        """Get single symbol from gateway."""
        try:
            data = self._get(f"/symbol/{symbol}")
            quote = self._map_to_symbol_quote(data)
            if not quote:
                raise ProviderNotFoundError(f"Symbol not found: {symbol}")
            return quote
        except ProviderNotFoundError:
            raise
        except Exception as e:
            logger.error("Gateway get_symbol failed for %s: %s", symbol, e)
            raise ProviderHTTPError(f"Gateway error: {e}")

    def get_nav(self, symbol: str) -> Optional[NavData]:
        """Get NAV from gateway (not fully implemented yet)."""
        try:
            data = self._get("/nav", params={"l18": symbol})
            if data and "error" not in data:
                return NavData(
                    symbol=symbol,
                    issue_nav=data.get("issue_nav"),
                    redeem_nav=data.get("redeem_nav"),
                    date=data.get("date"),
                    time=data.get("time"),
                )
        except Exception as e:
            logger.warning("Gateway get_nav failed for %s: %s", symbol, e)
        return None

    def get_shareholders(self, symbol: str) -> list:
        """Get shareholders from gateway (not implemented)."""
        return []

    def _map_to_symbol_quote(self, item: dict) -> Optional[SymbolQuote]:
        """Map gateway JSON to SymbolQuote DTO."""
        try:
            sym = item.get("symbol") or item.get("l18")
            name = item.get("name") or item.get("l30")

            if not sym:
                return None

            # Orderbook
            from services.providers.models import OrderBookSnapshot, OrderBookLevel
            bids = []
            if "orderbook" in item and item["orderbook"]:
                ob = item["orderbook"]
                for b in ob.get("bids", []):
                    bids.append(OrderBookLevel(
                        side=b.get("side", "bid"),
                        level=b.get("level", 1),
                        price=b.get("price", 0),
                        quantity=b.get("quantity", 0),
                        order_count=b.get("order_count", 0),
                    ))
            asks = []
            if "orderbook" in item and item["orderbook"]:
                ob = item["orderbook"]
                for a in ob.get("asks", []):
                    asks.append(OrderBookLevel(
                        side=a.get("side", "ask"),
                        level=a.get("level", 1),
                        price=a.get("price", 0),
                        quantity=a.get("quantity", 0),
                        order_count=a.get("order_count", 0),
                    ))
            orderbook = OrderBookSnapshot(bids=tuple(bids), asks=tuple(asks))

            # Money flow
            from services.providers.models import MoneyFlowSnapshot
            money_flow = MoneyFlowSnapshot()
            if "money_flow" in item and item["money_flow"]:
                mf = item["money_flow"]
                money_flow = MoneyFlowSnapshot(
                    buy_real_count=mf.get("buy_real_count", 0),
                    buy_legal_count=mf.get("buy_legal_count", 0),
                    sell_real_count=mf.get("sell_real_count", 0),
                    sell_legal_count=mf.get("sell_legal_count", 0),
                    buy_real_volume=mf.get("buy_real_volume", 0.0),
                    buy_legal_volume=mf.get("buy_legal_volume", 0.0),
                    sell_real_volume=mf.get("sell_real_volume", 0.0),
                    sell_legal_volume=mf.get("sell_legal_volume", 0.0),
                )

            return SymbolQuote(
                symbol=sym,
                name=name,
                ins_code=item.get("ins_code", ""),
                isin=item.get("isin"),
                sector=item.get("sector"),
                sector_id=item.get("sector_id"),
                board=item.get("board"),
                state=item.get("state"),
                last_price=item.get("last_price"),
                close_price=item.get("close_price"),
                yesterday_price=item.get("yesterday_price"),
                open_price=item.get("open_price"),
                change_last=item.get("change_last"),
                change_last_pct=item.get("change_last_pct"),
                change_close=item.get("change_close"),
                change_close_pct=item.get("change_close_pct"),
                volume=item.get("volume"),
                value=item.get("value"),
                trade_count=item.get("trade_count"),
                avg_volume_1m=item.get("avg_volume_1m"),
                low=item.get("low"),
                high=item.get("high"),
                threshold_min=item.get("threshold_min"),
                threshold_max=item.get("threshold_max"),
                market_value=item.get("market_value"),
                shares=item.get("shares"),
                time=item.get("time"),
                date=item.get("date"),
                orderbook=orderbook,
                money_flow=money_flow,
                is_fund_like=item.get("is_fund_like", False),
                raw=item.get("raw", {}),
            )
        except Exception as e:
            logger.warning("Failed to map gateway item: %s", e)
            return None