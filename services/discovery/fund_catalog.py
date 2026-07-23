"""کشف روزانه صندوق‌های قابل معامله از BRS."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from core.classification.fund_type import classify_fund_type
from services.providers.base import MarketDataProvider
from services.providers.factory import get_market_data_provider
from services.providers.models import SymbolQuote
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)


class FundCatalogService:
    """کشف + نرمال‌سازی کاتالوگ صندوق‌ها."""

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        store: Optional[SnapshotStore] = None,
    ) -> None:
        self.provider = provider or get_market_data_provider()
        self.store = store or SnapshotStore()

    def discover(self) -> list[SymbolQuote]:
        funds = self.provider.get_fund_symbols()
        # dedupe by symbol
        by_sym: dict[str, SymbolQuote] = {}
        for q in funds:
            if not q.symbol:
                continue
            by_sym[q.symbol] = q
        result = list(by_sym.values())
        logger.info("discovered unique funds=%s", len(result))
        return result

    def build_catalog_payload(self, funds: list[SymbolQuote]) -> dict[str, Any]:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        items = []
        type_counts: dict[str, int] = {}
        for q in funds:
            ftype = classify_fund_type(q)
            type_counts[ftype] = type_counts.get(ftype, 0) + 1
            items.append(
                {
                    "symbol": q.symbol,
                    "name": q.name,
                    "ins_code": q.ins_code,
                    "isin": q.isin,
                    "sector": q.sector,
                    "board": q.board,
                    "fund_type": ftype,
                    "close_price": q.close_price,
                    "last_price": q.last_price,
                    "change_pct": q.change_close_pct,
                    "volume": q.volume,
                    "value": q.value,
                    "time": q.time,
                }
            )
        items.sort(key=lambda x: (x.get("value") or 0), reverse=True)
        return {
            "generated_at": now,
            "source": getattr(self.provider, "name", "unknown"),
            "count": len(items),
            "type_counts": type_counts,
            "funds": items,
        }

    def discover_and_save(self) -> tuple[list[SymbolQuote], dict[str, Any], Any]:
        funds = self.discover()
        payload = self.build_catalog_payload(funds)
        path = self.store.save_json("fund_catalog", payload)
        self.store.save_latest("fund_catalog", payload)
        # also compact registry-like
        registry = [
            {
                "symbol": x["symbol"],
                "name": x["name"],
                "ins_code": x["ins_code"],
                "type": x["fund_type"],
                "active": True,
                "isin": x.get("isin"),
                "sector": x.get("sector"),
            }
            for x in payload["funds"]
        ]
        self.store.save_json("fund_registry_live", registry)
        self.store.save_latest("fund_registry_live", registry)
        return funds, payload, path
