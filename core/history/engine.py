"""موتور تاریخچه: دریافت، ذخیره SQLite، به‌روزرسانی افزایشی و کش."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from config import settings
from core.classification.fund_type import classify_fund_type
from core.database.connection import Database, get_database
from core.history.repository import HistoryRepository
from core.scoring.models import FundAssessment
from services.providers.base import MarketDataProvider
from services.providers.factory import get_market_data_provider
from services.providers.models import SymbolQuote

logger = logging.getLogger(__name__)

_PROVIDER_UNSET = object()


class HistoryEngine:
    """
    Historical Engine v1

    - کشف/همگام‌سازی همه صندوق‌ها
    - ذخیره OHLC / حجم / ارزش / قدرت خریدار-فروشنده
    - upsert روزانه (incremental)
    - کش پاسخ‌های تکراری provider (اختیاری از طریق repo.cache_*)
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        provider: Any = _PROVIDER_UNSET,
        repo: Optional[HistoryRepository] = None,
        cache_ttl_seconds: Optional[int] = None,
    ) -> None:
        self.db = db or get_database()
        # provider:
        # - omitted => try live factory
        # - explicit None => offline mode
        # - instance => use it
        if provider is _PROVIDER_UNSET:
            try:
                self.provider = get_market_data_provider()
            except Exception as exc:  # noqa: BLE001
                logger.warning("history engine provider unavailable: %s", exc)
                self.provider = None
        else:
            self.provider = provider
        self.repo = repo or HistoryRepository(self.db)
        self.cache_ttl_seconds = (
            settings.HISTORY_CACHE_TTL_SECONDS
            if cache_ttl_seconds is None
            else int(cache_ttl_seconds)
        )

    def sync_daily(
        self,
        *,
        limit: Optional[int] = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        همگام‌سازی روزانه از provider.

        اگر برای trade_date امروز قبلاً داده کامل ذخیره شده باشد و force=False،
        از re-fetch سنگین جلوگیری می‌کند (فقط آمار برمی‌گرداند).
        """
        started = datetime.now().astimezone()
        logger.info("history sync start force=%s", force)

        quotes = self._load_fund_quotes(limit=limit)
        fund_types = {
            q.symbol: classify_fund_type(q)
            for q in quotes
            if q.symbol
        }

        stats = self.repo.bulk_upsert_quotes(quotes, fund_types=fund_types)
        trade_date = self._dominant_trade_date(quotes)

        # market snapshot خلاصه
        changes = [q.change_close_pct for q in quotes if q.change_close_pct is not None]
        values = [float(q.value) for q in quotes if q.value]
        volumes = [float(q.volume) for q in quotes if q.volume]
        avg_chg = sum(changes) / len(changes) if changes else None
        total_value = sum(values) if values else None
        total_volume = sum(volumes) if volumes else None

        # best/worst group by avg change
        by_type: dict[str, list[float]] = {}
        for q in quotes:
            ft = fund_types.get(q.symbol) or "سایر"
            if q.change_close_pct is None:
                continue
            by_type.setdefault(ft, []).append(float(q.change_close_pct))
        group_avg = {
            k: sum(v) / len(v) for k, v in by_type.items() if v
        }
        best_group = max(group_avg, key=group_avg.get) if group_avg else ""
        worst_group = min(group_avg, key=group_avg.get) if group_avg else ""

        market_status = self._market_status(avg_chg)
        market_power = self._market_power(avg_chg, quotes)

        snap_id = self.repo.save_market_snapshot(
            trade_date=trade_date,
            funds_count=len(quotes),
            market_status=market_status,
            market_power=market_power,
            best_group=best_group,
            worst_group=worst_group,
            total_value=total_value,
            total_volume=total_volume,
            avg_change_pct=avg_chg,
            payload={
                "group_avg_change": group_avg,
                "source": getattr(self.provider, "name", "unknown"),
            },
        )

        # پاکسازی کش منقضی
        purged = self.repo.cache_purge_expired()

        result = {
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "trade_date": trade_date,
            "funds": len(quotes),
            "history": stats,
            "market_status": market_status,
            "market_power": market_power,
            "best_group": best_group,
            "worst_group": worst_group,
            "avg_change_pct": avg_chg,
            "snapshot_id": snap_id,
            "cache_purged": purged,
            "db_path": str(self.db.path),
        }
        logger.info(
            "history sync done funds=%s inserted=%s updated=%s",
            len(quotes),
            stats.get("inserted"),
            stats.get("updated"),
        )
        return result

    def persist_scores(
        self,
        ranked: list[FundAssessment],
        *,
        score_date: Optional[str] = None,
    ) -> int:
        """ذخیره امتیازهای روزانه در daily_scores."""
        day = score_date or datetime.now().astimezone().date().isoformat()
        for a in ranked:
            self.repo.upsert_daily_score(a, day)
        return len(ranked)

    def get_series(self, symbol: str, limit: int = 120) -> list[dict[str, Any]]:
        return self.repo.get_history(symbol, limit=limit)

    def stats(self) -> dict[str, Any]:
        funds = self.repo.list_funds()
        return {
            "db_path": str(self.db.path),
            "funds": len(funds),
            "history_rows": self.repo.history_count(),
            "latest_trade_date": self.repo.latest_trade_date(),
        }

    # ---- cache helpers for future provider wrappers ----
    def cached_json(
        self,
        endpoint: str,
        params: dict[str, Any],
        fetcher,
    ) -> Any:
        """کش عمومی JSON برای جلوگیری از درخواست تکراری."""
        key = self._cache_key(endpoint, params)
        hit = self.repo.cache_get(key)
        if hit is not None:
            logger.debug("cache hit %s", key[:16])
            return json.loads(hit)

        data = fetcher()
        expires = (
            datetime.now().astimezone() + timedelta(seconds=self.cache_ttl_seconds)
        ).isoformat(timespec="seconds")
        self.repo.cache_set(
            key,
            endpoint=endpoint,
            params_json=json.dumps(params, ensure_ascii=False, sort_keys=True),
            response_json=json.dumps(data, ensure_ascii=False, default=str),
            expires_at=expires,
        )
        return data

    def _load_fund_quotes(self, limit: Optional[int] = None) -> list[SymbolQuote]:
        # اگر provider متد get_fund_symbols دارد از آن استفاده کن
        if hasattr(self.provider, "get_fund_symbols"):
            quotes = self.provider.get_fund_symbols()
        else:
            quotes = [q for q in self.provider.get_all_symbols() if getattr(q, "is_fund_like", False)]
        if limit is not None and limit > 0:
            quotes = quotes[: int(limit)]
        return quotes

    @staticmethod
    def _dominant_trade_date(quotes: list[SymbolQuote]) -> str:
        dates = [str(q.date).strip() for q in quotes if q.date]
        if not dates:
            return datetime.now().astimezone().date().isoformat()
        # پرتکرارترین
        freq: dict[str, int] = {}
        for d in dates:
            freq[d] = freq.get(d, 0) + 1
        return max(freq, key=freq.get)

    @staticmethod
    def _market_status(avg_change: Optional[float]) -> str:
        if avg_change is None:
            return "نامشخص"
        if avg_change >= 0.8:
            return "مثبت قوی"
        if avg_change >= 0.15:
            return "مثبت"
        if avg_change > -0.15:
            return "خنثی"
        if avg_change > -0.8:
            return "منفی"
        return "منفی قوی"

    @staticmethod
    def _market_power(avg_change: Optional[float], quotes: list[SymbolQuote]) -> float:
        """قدرت بازار 0..100 — ترکیبی از میانگین تغییر و نسبت نمادهای مثبت."""
        if not quotes:
            return 50.0
        signed = [q.change_close_pct for q in quotes if q.change_close_pct is not None]
        if not signed:
            return 50.0
        up = sum(1 for x in signed if x > 0)
        breadth = up / len(signed)  # 0..1
        avg = avg_change if avg_change is not None else 0.0
        # map avg change ~[-3, +3] to 0..100
        mom = max(0.0, min(100.0, 50.0 + avg * 12.0))
        power = 0.55 * mom + 0.45 * (breadth * 100.0)
        return round(max(0.0, min(100.0, power)), 1)

    @staticmethod
    def _cache_key(endpoint: str, params: dict[str, Any]) -> str:
        raw = endpoint + "|" + json.dumps(params, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
