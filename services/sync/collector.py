"""
Sync V1 — FundCollector

Reads from a MarketSnapshotProvider interface and creates
FundSnapshot objects stored as local JSON files for validation.

Does NOT modify any existing provider code.
The existing BrsProvider satisfies the MarketSnapshotProvider
interface without any modifications to its code.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from services.sync.models import FundSnapshot
from services.sync.providers import MarketSnapshotProvider
from services.discovery.universe_store import get_universe_store, get_valid_fund_symbols

logger = logging.getLogger(__name__)


class FundCollector:
    """
    Collects fund market data from a MarketSnapshotProvider
    and stores normalized snapshots locally as JSON files.

    Usage:
        from services.providers.brs_provider import BrsProvider
        from services.sync import FundCollector

        provider = BrsProvider()
        collector = FundCollector(provider=provider)
        collector.collect_fund("فندق ملت")

    The provider argument satisfies the MarketSnapshotProvider
    interface. The default BrsProvider already implements it.
    """

    def __init__(
        self,
        provider: Optional[MarketSnapshotProvider] = None,
        snapshot_dir: Optional[str] = None,
    ) -> None:
        from config import settings

        if provider is None:
            from services.providers.brs_provider import BrsProvider

            provider = BrsProvider()

        self.provider = provider
        self.snapshot_dir = Path(
            snapshot_dir or settings.SNAPSHOT_DIR
        )
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            "FundCollector initialized — snapshots dir: %s",
            self.snapshot_dir,
        )

    # ------------------------------------------------------------------
    # Collection
    # ------------------------------------------------------------------

    def collect_fund(self, symbol: str) -> Optional[FundSnapshot]:
        """
        Collect a single fund's snapshot from the provider.

        Uses the MarketSnapshotProvider.get_symbol() and
        MarketSnapshotProvider.get_nav() interfaces — no new
        provider code is touched.

        Returns a FundSnapshot or None if the symbol is not found.
        """
        try:
            quote = self.provider.get_symbol(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to get quote for %s: %s", symbol, exc)
            return None

        nav = None
        try:
            nav = self.provider.get_nav(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to get NAV for %s: %s", symbol, exc)

        snapshot = self._build_snapshot(quote, nav)
        self._store_snapshot(snapshot)
        return snapshot

    def collect_all_funds(
        self, limit: Optional[int] = None, include_nav: bool = False
    ) -> list[FundSnapshot]:
        """
        Collect snapshots for all fund-like symbols.

        Uses fund_universe (Source of Truth: BRS AllSymbols cs_id=68),
        then collects each fund individually.

        Args:
            limit: Maximum number of funds to collect. None = all.
            include_nav: Whether to fetch NAV data (slow, quota-heavy). Default False for sync.

        Returns:
            List of FundSnapshot objects.
        """
        # Get valid fund symbols from central universe store
        fund_symbols = get_valid_fund_symbols()
        
        if limit is not None:
            fund_symbols = fund_symbols[:limit]

        snapshots: list[FundSnapshot] = []
        for symbol in fund_symbols:
            try:
                quote = self.provider.get_symbol(symbol)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to get quote for %s: %s", symbol, exc)
                continue

            nav = None
            if include_nav:
                try:
                    nav = self.provider.get_nav(symbol)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to get NAV for %s: %s", symbol, exc)

            snapshot = self._build_snapshot(quote, nav)
            self._store_snapshot(snapshot)
            snapshots.append(snapshot)

        logger.info(
            "Collected %d fund snapshots",
            len(snapshots),
        )
        return snapshots

    def collect_symbol(
        self, symbol: str, include_nav: bool = True
    ) -> Optional[FundSnapshot]:
        """
        Collect a single symbol (fund or not) snapshot.

        Args:
            symbol: The symbol to collect (e.g. "صندوق ملت").
            include_nav: Whether to fetch NAV data.

        Returns:
            FundSnapshot or None if not found.
        """
        try:
            quote = self.provider.get_symbol(symbol)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to get quote for %s: %s", symbol, exc)
            return None

        nav = None
        if include_nav:
            try:
                nav = self.provider.get_nav(symbol)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to get NAV for %s: %s", symbol, exc)

        snapshot = self._build_snapshot(quote, nav)
        self._store_snapshot(snapshot)
        return snapshot

    # ------------------------------------------------------------------
    # Snapshot building
    # ------------------------------------------------------------------

    def _build_snapshot(
        self,
        quote: object,
        nav: Optional[object],
    ) -> FundSnapshot:
        """
        Build a FundSnapshot from a SymbolQuote and optional NavData.

        Uses attribute access on the existing provider DTOs
        (SymbolQuote, NavData) — no modification to those classes.
        """
        # Extract order book summary (top-of-book only)
        best_bid = None
        best_ask = None
        bid_volume = None
        ask_volume = None

        if hasattr(quote, "orderbook") and quote.orderbook:
            if quote.orderbook.bids:
                best_bid = quote.orderbook.bids[0].price
                bid_volume = quote.orderbook.bids[0].quantity
            if quote.orderbook.asks:
                best_ask = quote.orderbook.asks[0].price
                ask_volume = quote.orderbook.asks[0].quantity

        # Extract NAV
        nav_issue = None
        nav_redeem = None
        nav_date = None

        if nav is not None:
            nav_issue = getattr(nav, "issue_nav", None)
            nav_redeem = getattr(nav, "redeem_nav", None)
            nav_date = getattr(nav, "date", None)

        # Build raw dict from quote
        raw = {}
        if hasattr(quote, "to_dict"):
            raw = quote.to_dict()
            # Remove large fields from raw
            raw.pop("orderbook", None)
            raw.pop("money_flow", None)
            raw.pop("raw", None)

        return FundSnapshot(
            symbol=getattr(quote, "symbol", ""),
            name=getattr(quote, "name", ""),
            ins_code=getattr(quote, "ins_code", ""),
            isin=getattr(quote, "isin", None),
            sector=getattr(quote, "sector", None),
            fund_type=getattr(quote, "fund_type", None),
            last_price=getattr(quote, "last_price", None),
            close_price=getattr(quote, "close_price", None),
            yesterday_price=getattr(quote, "yesterday_price", None),
            change_last_pct=getattr(quote, "change_last_pct", None),
            volume=getattr(quote, "volume", None),
            value=getattr(quote, "value", None),
            nav_issue=nav_issue,
            nav_redeem=nav_redeem,
            nav_date=nav_date,
            best_bid=best_bid,
            best_ask=best_ask,
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            source="brs",
            captured_at=datetime.now(timezone.utc).isoformat(),
            raw=raw,
        )

    # ------------------------------------------------------------------
    # Local storage (file-based, no database)
    # ------------------------------------------------------------------

    def _store_snapshot(self, snapshot: FundSnapshot) -> Path:
        """
        Store a FundSnapshot as a local JSON file.

        File naming: {symbol}_{timestamp}.json
        Stored in SNAPSHOT_DIR.

        This is file-based storage only — no database tables,
        no persistence layer changes, no production DB impact.
        """
        safe_symbol = snapshot.symbol.replace("/", "_").replace(" ", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_symbol}_{timestamp}.json"
        filepath = self.snapshot_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(
                snapshot.to_dict(),
                f,
                ensure_ascii=False,
                indent=2,
            )

        logger.debug("Stored snapshot: %s", filepath)
        return filepath

    def list_snapshots(
        self,
        symbol: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        List stored snapshot files as metadata (no DB query).

        Args:
            symbol: Filter by symbol prefix. None = all.
            limit: Maximum results.

        Returns:
            List of snapshot metadata dicts.
        """
        files = sorted(self.snapshot_dir.glob("*.json"), reverse=True)
        if symbol:
            safe = symbol.replace("/", "_").replace(" ", "_")
            files = [f for f in files if f.stem.startswith(safe)]

        results: list[dict[str, Any]] = []
        for fpath in files[:limit]:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                results.append(data)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to read %s: %s", fpath, exc)

        return results

    def clear_snapshots(self, older_than_hours: int = 24) -> int:
        """
        Remove old snapshot files.

        Args:
            older_than_hours: Delete files older than this.

        Returns:
            Number of files deleted.
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        deleted = 0

        for fpath in self.snapshot_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(
                fpath.stat().st_mtime,
                tz=timezone.utc,
            )
            if mtime < cutoff:
                fpath.unlink()
                deleted += 1

        logger.info("Cleared %d old snapshots", deleted)
        return deleted
