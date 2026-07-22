"""پایپ‌لاین روزانه: کشف → (NAV اختیاری) → امتیاز → رنکینگ → ذخیره/گزارش."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import settings
from core.ranking.fund_ranker import FundRanker
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from reports.persian_ranking import PersianRankingReport
from services.discovery.fund_catalog import FundCatalogService
from services.providers.base import MarketDataProvider
from services.providers.exceptions import ProviderError
from services.providers.factory import get_market_data_provider
from services.providers.models import NavData, SymbolQuote
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)


class DailyRankPipeline:
    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        store: Optional[SnapshotStore] = None,
        score_engine: Optional[ScoreEngine] = None,
        fetch_nav: Optional[bool] = None,
        max_nav_workers: Optional[int] = None,
    ) -> None:
        self.provider = provider or get_market_data_provider()
        self.store = store or SnapshotStore()
        self.catalog = FundCatalogService(provider=self.provider, store=self.store)
        self.engine = score_engine or ScoreEngine()
        self.ranker = FundRanker()
        self.report = PersianRankingReport()
        self.fetch_nav = (
            settings.FETCH_NAV_IN_DAILY_RANK if fetch_nav is None else bool(fetch_nav)
        )
        self.max_nav_workers = (
            settings.NAV_FETCH_WORKERS if max_nav_workers is None else int(max_nav_workers)
        )

    def run(self, limit: Optional[int] = None) -> dict[str, Any]:
        started = datetime.now().astimezone()
        logger.info("daily rank pipeline start fetch_nav=%s", self.fetch_nav)

        funds, catalog_payload, _ = self.catalog.discover_and_save()
        if limit is not None and limit > 0:
            funds = funds[: int(limit)]

        nav_map: dict[str, NavData] = {}
        if self.fetch_nav:
            nav_map = self._fetch_navs(funds)

        assessments: list[FundAssessment] = []
        for q in funds:
            nav = nav_map.get(q.symbol)
            try:
                assessments.append(self.engine.assess(q, nav=nav))
            except Exception as exc:  # noqa: BLE001
                logger.exception("assess failed for %s: %s", q.symbol, exc)

        ranked = self.ranker.rank(assessments)
        by_type = {k: [a.to_dict() for a in v] for k, v in self.ranker.by_type(ranked).items()}

        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "started_at": started.isoformat(timespec="seconds"),
            "product": settings.PRODUCT_NAME,
            "source": getattr(self.provider, "name", "unknown"),
            "count": len(ranked),
            "fetch_nav": self.fetch_nav,
            "nav_success": len(nav_map),
            "top": [a.to_dict() for a in self.ranker.top(ranked, 20)],
            "worst": [a.to_dict() for a in self.ranker.worst(ranked, 10)],
            "by_type_counts": {k: len(v) for k, v in by_type.items()},
            "rankings": [a.to_dict() for a in ranked],
            "by_type": by_type,
            "catalog_count": catalog_payload.get("count"),
        }

        rank_path = self.store.save_json("daily_ranking", payload)
        self.store.save_latest("daily_ranking", payload)

        quotes_payload = {
            "generated_at": payload["generated_at"],
            "count": len(funds),
            "quotes": [self._quote_compact(q) for q in funds],
        }
        self.store.save_json("fund_quotes", quotes_payload)
        self.store.save_latest("fund_quotes", quotes_payload)

        text = self.report.generate(ranked, meta=payload)
        text_path = self.store.path_for("daily_ranking").with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")
        latest_txt = self.store.base_dir / "latest" / "daily_ranking.txt"
        latest_txt.parent.mkdir(parents=True, exist_ok=True)
        latest_txt.write_text(text, encoding="utf-8")

        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "daily_ranking.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (reports_dir / "daily_ranking.txt").write_text(text, encoding="utf-8")

        logger.info("daily rank done count=%s path=%s", len(ranked), rank_path)
        return {
            "count": len(ranked),
            "rank_path": str(rank_path),
            "text_path": str(text_path),
            "top": payload["top"][:5],
            "payload": payload,
            "text": text,
        }

    def _fetch_navs(self, funds: list[SymbolQuote]) -> dict[str, NavData]:
        out: dict[str, NavData] = {}
        workers = max(1, min(self.max_nav_workers, 8))
        logger.info("fetching NAV for %s funds workers=%s", len(funds), workers)

        def job(sym: str) -> tuple[str, Optional[NavData]]:
            try:
                return sym, self.provider.get_nav(sym)
            except ProviderError:
                return sym, None
            except Exception:
                return sym, None

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(job, q.symbol) for q in funds if q.symbol]
            for fut in as_completed(futs):
                sym, nav = fut.result()
                if nav is not None:
                    out[sym] = nav
        logger.info("NAV fetched ok=%s", len(out))
        return out

    @staticmethod
    def _quote_compact(q: SymbolQuote) -> dict[str, Any]:
        d = q.to_dict()
        d.pop("raw", None)
        return d
