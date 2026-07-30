"""بارگذاری رنکینگ برای ربات از پایپلاین تحلیل (با کش)."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from core.pipeline.daily_analysis import DailyAnalysisPipeline
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.providers.base import MarketDataProvider
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)

_CACHE: dict[str, Any] = {"ranked": [], "source": "", "at": 0.0, "payload": {}}


def load_rankings(
    *,
    provider: Optional[MarketDataProvider] = None,
    store: Optional[SnapshotStore] = None,
    engine: Optional[ScoreEngine] = None,
    allow_live: bool = True,
    allow_demo: bool = True,
    max_age_sec: float = 900,
    limit: Optional[int] = None,
) -> tuple[list[FundAssessment], str]:
    now = time.time()
    if _CACHE["ranked"] and (now - float(_CACHE["at"] or 0)) < max_age_sec:
        return list(_CACHE["ranked"]), str(_CACHE["source"])

    try:
        pipe = DailyAnalysisPipeline(
            provider=provider if allow_live else None,
            store=store,
            fetch_nav=False,
            allow_offline_seed=allow_demo,
        )
        # if provider forced None, pipeline still offline-seeds
        if not allow_live:
            pipe.provider = None
            pipe._provider_error = "live disabled"
        result = pipe.run(limit=limit)
        ranked = result["ranked"]
        source = result["source"]
        if ranked:
            _CACHE.update({"ranked": ranked, "source": source, "at": now, "payload": result["payload"]})
            return ranked, source
    except Exception as exc:  # noqa: BLE001
        logger.warning("analysis pipeline failed: %s", exc)

    if allow_demo:
        from core.pipeline.daily_analysis import DailyAnalysisPipeline as P

        pipe = P(provider=None, allow_offline_seed=True)
        pipe.provider = None
        result = pipe.run(limit=limit or 30)
        ranked = result["ranked"]
        _CACHE.update({"ranked": ranked, "source": "demo", "at": now, "payload": result["payload"]})
        return ranked, "demo"

    return [], "empty"


def get_cached_payload() -> dict[str, Any]:
    return dict(_CACHE.get("payload") or {})
