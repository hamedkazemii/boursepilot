"""
Sync V1 — MarketSnapshotProvider interface.

Abstract interface that the collector depends on.
The existing BrsProvider satisfies this interface
without any modifications to its code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class MarketSnapshotProvider(ABC):
    """
    Abstract interface for market data providers.

    The collector uses this interface to remain
    provider-agnostic. Any class implementing
    these methods can be used as a data source.

    The existing BrsProvider satisfies this interface:
    - get_symbol(symbol) -> SymbolQuote
    - get_nav(symbol) -> NavData
    - get_all_symbols() -> list[SymbolQuote]
    - get_fund_symbols() -> list[SymbolQuote]
    """

    @abstractmethod
    def get_symbol(self, symbol: str) -> object:
        """
        Get a single symbol's market data.

        Returns:
            SymbolQuote or similar DTO with attributes:
            symbol, name, ins_code, last_price, close_price,
            yesterday_price, change_last_pct, volume, value,
            orderbook, sector, isin.

        Raises:
            ProviderNotFoundError: If symbol not found.
        """
        ...

    @abstractmethod
    def get_nav(self, symbol: str) -> Optional[object]:
        """
        Get NAV data for a symbol.

        Returns:
            NavData or similar DTO with attributes:
            symbol, issue_nav, redeem_nav, date, time.

        Returns None if NAV is not available.
        """
        ...

    @abstractmethod
    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list:
        """
        Get all available symbols.

        Returns:
            List of SymbolQuote or similar DTO objects.
        """
        ...

    @abstractmethod
    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> list:
        """
        Get only fund-like symbols.

        Returns:
            List of SymbolQuote or similar DTO objects
            that represent funds/ETFs.
        """
        ...
