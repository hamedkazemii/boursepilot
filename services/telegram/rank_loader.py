"""بارگذاری رنکینگ برای ربات: زنده → snapshot → دمو."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from core.ranking.fund_ranker import FundRanker
from core.scoring.models import FactorScore, FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.discovery.fund_catalog import FundCatalogService
from services.providers.base import MarketDataProvider
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)


def assessments_from_payload(payload: dict[str, Any]) -> list[FundAssessment]:
    out: list[FundAssessment] = []
    for row in payload.get("rankings") or payload.get("top") or []:
        factors = []
        for f in row.get("factors") or []:
            factors.append(
                FactorScore(
                    key=f.get("key", ""),
                    title=f.get("title", ""),
                    score=float(f.get("score") or 0),
                    label=f.get("label", ""),
                    reasons=tuple(f.get("reasons") or []),
                    metrics=f.get("metrics") or {},
                )
            )
        out.append(
            FundAssessment(
                symbol=row.get("symbol") or "",
                name=row.get("name") or "",
                fund_type=row.get("fund_type") or "",
                ins_code=str(row.get("ins_code") or ""),
                sector=row.get("sector"),
                final_score=float(row.get("final_score") or 0),
                recommendation=row.get("recommendation") or "neutral",
                recommendation_label=row.get("recommendation_label") or "",
                rank=row.get("rank"),
                factors=tuple(factors),
                summary_reasons=tuple(row.get("summary_reasons") or []),
                close_price=row.get("close_price"),
                last_price=row.get("last_price"),
                change_pct=row.get("change_pct"),
                volume=row.get("volume"),
                value=row.get("value"),
                issue_nav=row.get("issue_nav"),
                redeem_nav=row.get("redeem_nav"),
                premium_pct=row.get("premium_pct"),
                extras=row.get("extras") or {},
            )
        )
    # اگر فقط top بود، rank را از نو بزن
    if out and out[0].rank is None:
        out = FundRanker().rank(out)
    return out


def load_snapshot_rankings(store: Optional[SnapshotStore] = None) -> list[FundAssessment]:
    store = store or SnapshotStore()
    candidates = [
        store.base_dir / "latest" / "daily_ranking.json",
        Path("reports/daily_ranking.json"),
        Path("data/fund_ranking.json"),
        Path("data/fund_scores.json"),
    ]
    # روز جاری
    try:
        candidates.insert(0, store.path_for("daily_ranking"))
    except Exception:
        pass

    for path in candidates:
        try:
            if not path.exists():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                payload = {"rankings": payload}
            ranked = assessments_from_payload(payload)
            if ranked:
                logger.info("loaded rankings from %s count=%s", path, len(ranked))
                return ranked
        except Exception as exc:  # noqa: BLE001
            logger.warning("snapshot load failed %s: %s", path, exc)
    return []


def demo_rankings() -> list[FundAssessment]:
    """داده نمایشی تا دکمه‌ها حتی بدون شبکه کار کنند."""
    samples = [
        ("عیار", "صندوق طلای عیار", "طلا", 88.0, 2.1, -0.3),
        ("زر", "صندوق طلای زر", "طلا", 81.0, 1.4, 0.2),
        ("اهرم", "صندوق اهرمی", "اهرم", 74.0, 0.9, None),
        ("موج", "صندوق سهامی موج", "سهامی", 66.0, 0.4, None),
        ("آگاس", "صندوق سهامی", "سهامی", 58.0, -0.3, None),
        ("یاقوت", "درآمد ثابت یاقوت", "درآمد ثابت", 49.0, 0.1, None),
        ("آرام", "درآمد ثابت آرام", "درآمد ثابت", 41.0, -0.5, None),
        ("کم‌ریسک", "درآمد ثابت کم‌ریسک", "درآمد ثابت", 33.0, -1.2, None),
    ]
    items: list[FundAssessment] = []
    for i, (sym, name, ftype, score, chg, prem) in enumerate(samples, 1):
        rec = "buy" if score >= 65 else "neutral" if score >= 45 else "sell"
        label = "خرید" if rec == "buy" else "خنثی" if rec == "neutral" else "فروش"
        items.append(
            FundAssessment(
                symbol=sym,
                name=name,
                fund_type=ftype,
                ins_code=str(i),
                sector="صندوق",
                final_score=score,
                recommendation=rec,
                recommendation_label=label,
                rank=i,
                factors=(
                    FactorScore("liquidity", "نقدشوندگی", min(95, score + 5), "خوب", ("عمق مناسب بازار",)),
                    FactorScore("momentum", "مومنتوم", max(20, score - 8), "متوسط", (f"تغییر روز {chg:+.1f}%",)),
                    FactorScore("money_flow", "جریان پول", score - 3, "قابل قبول", ("ورود نسبی پول",)),
                ),
                summary_reasons=(
                    f"امتیاز نهایی {score:.1f} → توصیه: {label}",
                    "نقطه قوت — نقدشوندگی: عمق مناسب بازار",
                    f"تغییر روز: {chg:+.2f}%",
                ),
                change_pct=chg,
                volume=1_000_000 * i,
                value=2e10 / i,
                premium_pct=prem,
            )
        )
    return items


def load_rankings(
    *,
    provider: Optional[MarketDataProvider] = None,
    store: Optional[SnapshotStore] = None,
    engine: Optional[ScoreEngine] = None,
    allow_live: bool = True,
    allow_demo: bool = True,
) -> tuple[list[FundAssessment], str]:
    """
    Returns: (ranked, source) where source in live|snapshot|demo
    """
    store = store or SnapshotStore()
    engine = engine or ScoreEngine()
    ranker = FundRanker()

    if allow_live and provider is not None:
        try:
            funds = FundCatalogService(provider=provider, store=store).discover()
            assessments = [engine.assess(q, nav=None) for q in funds]
            ranked = ranker.rank(assessments)
            if ranked:
                # persist for next offline use
                try:
                    payload = {
                        "count": len(ranked),
                        "rankings": [a.to_dict() for a in ranked],
                        "source": "live",
                    }
                    store.save_latest("daily_ranking", payload)
                    Path("reports").mkdir(exist_ok=True)
                    Path("reports/daily_ranking.json").write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("persist live ranking failed: %s", exc)
                return ranked, "live"
        except Exception as exc:  # noqa: BLE001
            logger.warning("live ranking failed, fallback snapshot: %s", exc)

    ranked = load_snapshot_rankings(store)
    if ranked:
        return ranked, "snapshot"

    if allow_demo:
        logger.warning("using demo rankings")
        return demo_rankings(), "demo"

    return [], "empty"
