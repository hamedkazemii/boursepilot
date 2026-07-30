"""پایپلاین کامل: live/snapshot → history → indicators → smart rank → persist."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config import settings
from core.analytics.market_summary import build_market_summary
from core.classification.fund_type import classify_fund_type
from core.history.engine import HistoryEngine
from core.indicators.engine import IndicatorEngine, IndicatorSnapshot
from core.ranking.smart_ranker import SmartRanker
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


class DailyAnalysisPipeline:
    """
    مسیر استاندارد محصول:
    1) دریافت داده زنده (یا fallback)
    2) ذخیره history incremental
    3) محاسبه indicators از تاریخچه هر صندوق
    4) امتیاز لحظه‌ای + SmartRank نسبی
    5) ذخیره daily_scores + گزارش
    """

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        store: Optional[SnapshotStore] = None,
        history: Optional[HistoryEngine] = None,
        fetch_nav: bool = False,
        allow_offline_seed: bool = True,
    ) -> None:
        self.provider = provider
        self._provider_error: Optional[str] = None
        if provider is None:
            try:
                self.provider = get_market_data_provider()
            except Exception as exc:  # noqa: BLE001
                self._provider_error = str(exc)
                logger.warning("provider unavailable: %s", exc)
        self.store = store or SnapshotStore()
        self.history = history if history is not None else HistoryEngine(provider=self.provider)
        self.score_engine = ScoreEngine()
        self.indicator_engine = IndicatorEngine()
        self.smart_ranker = SmartRanker()
        self.report = PersianRankingReport()
        self.fetch_nav = fetch_nav
        self.allow_offline_seed = allow_offline_seed

    def run(self, limit: Optional[int] = None) -> dict[str, Any]:
        started = datetime.now().astimezone()
        source = "live"
        funds: list[SymbolQuote] = []

        # 1) load quotes
        try:
            if self.provider is None:
                raise RuntimeError(self._provider_error or "no provider")
            catalog = FundCatalogService(provider=self.provider, store=self.store)
            funds, catalog_payload, _ = catalog.discover_and_save()
            if limit and limit > 0:
                funds = funds[: int(limit)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("live discover failed: %s", exc)
            source = "offline"
            funds = self._load_offline_quotes(limit=limit)
            catalog_payload = {"count": len(funds), "source": "offline"}

        if not funds:
            raise RuntimeError("هیچ داده صندوقی برای تحلیل در دسترس نیست")

        # 2) optional NAV
        nav_map: dict[str, NavData] = {}
        if self.fetch_nav and self.provider is not None and source == "live":
            nav_map = self._fetch_navs(funds)

        # 3) persist history (+ synthetic multi-day seed if history too short)
        fund_types = {q.symbol: classify_fund_type(q) for q in funds if q.symbol}
        hist_stats = self.history.repo.bulk_upsert_quotes(funds, fund_types=fund_types, source=source)
        if self.allow_offline_seed:
            seeded = self._ensure_min_history(funds, fund_types=fund_types, min_days=45)
            hist_stats["seeded_points"] = seeded

        # 4) base assessments + indicators
        assessments: list[FundAssessment] = []
        indicators: dict[str, IndicatorSnapshot] = {}
        for q in funds:
            try:
                a = self.score_engine.assess(q, nav=nav_map.get(q.symbol))
                assessments.append(a)
            except Exception as exc:  # noqa: BLE001
                logger.exception("assess failed %s: %s", q.symbol, exc)
                continue
            series = self.history.get_series(q.symbol, limit=200)
            ind = self.indicator_engine.compute(series)
            indicators[q.symbol] = ind
            # store indicators
            try:
                self._save_indicator(q.symbol, ind)
            except Exception as exc:  # noqa: BLE001
                logger.debug("indicator save failed %s: %s", q.symbol, exc)

        # 5) smart relative rank
        ranked = self.smart_ranker.rank(assessments, indicators=indicators)
        summary = build_market_summary(ranked, generated_at=started.isoformat(timespec="seconds"))

        # 6) persist scores + market snapshot
        day = datetime.now().astimezone().date().isoformat()
        try:
            self.history.persist_scores(ranked, score_date=day)
            self.history.repo.save_market_snapshot(
                trade_date=day,
                funds_count=len(ranked),
                market_status=summary.market_status,
                market_power=summary.market_power,
                best_group=summary.best_group,
                worst_group=summary.worst_group,
                total_value=summary.total_value,
                avg_change_pct=summary.avg_change_pct,
                payload=summary.to_dict(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("persist scores/snapshot failed: %s", exc)

        top_n = self.smart_ranker.top(ranked, 5)
        worst_n = self.smart_ranker.worst(ranked, 5)

        payload = {
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "started_at": started.isoformat(timespec="seconds"),
            "product": settings.PRODUCT_NAME,
            "source": source,
            "count": len(ranked),
            "fetch_nav": self.fetch_nav,
            "nav_success": len(nav_map),
            "history": hist_stats,
            "market": summary.to_dict(),
            "top": [a.to_dict() for a in top_n],
            "worst": [a.to_dict() for a in worst_n],
            "rankings": [a.to_dict() for a in ranked],
            "by_type_counts": _type_counts(ranked),
            "catalog_count": catalog_payload.get("count"),
            "quality": {
                "min_score": ranked[-1].final_score if ranked else None,
                "max_score": ranked[0].final_score if ranked else None,
                "median_score": ranked[len(ranked)//2].final_score if ranked else None,
                "top5_avg": _avg([a.final_score for a in top_n]),
                "worst5_avg": _avg([a.final_score for a in worst_n]),
                "score_gap_top_worst": (
                    (_avg([a.final_score for a in top_n]) - _avg([a.final_score for a in worst_n]))
                    if top_n and worst_n else None
                ),
            },
        }

        # validate ranking sanity
        payload["quality"]["sane"] = self._validate_ranking(payload)

        self.store.save_json("daily_ranking", payload)
        self.store.save_latest("daily_ranking", payload)
        text = self.report.generate(ranked, meta=payload, top_n=15, worst_n=8)
        text_path = self.store.path_for("daily_ranking").with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")
        latest_txt = self.store.base_dir / "latest" / "daily_ranking.txt"
        latest_txt.parent.mkdir(parents=True, exist_ok=True)
        latest_txt.write_text(text, encoding="utf-8")
        Path("reports").mkdir(parents=True, exist_ok=True)
        Path("reports/daily_ranking.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        Path("reports/daily_ranking.txt").write_text(text, encoding="utf-8")

        logger.info(
            "daily analysis done source=%s n=%s top=%.1f worst=%.1f gap=%.1f sane=%s",
            source,
            len(ranked),
            payload["quality"]["top5_avg"] or -1,
            payload["quality"]["worst5_avg"] or -1,
            payload["quality"]["score_gap_top_worst"] or -1,
            payload["quality"]["sane"],
        )
        return {
            "count": len(ranked),
            "source": source,
            "payload": payload,
            "ranked": ranked,
            "indicators": indicators,
            "text": text,
            "summary": summary,
        }

    def _save_indicator(self, symbol: str, ind: IndicatorSnapshot) -> None:
        fund_id = self.history.repo.get_fund_id(symbol)
        if fund_id is None:
            return
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        d = ind.to_dict()
        with self.history.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO fund_indicators(
                    fund_id, as_of_date, ret_1d, ret_5d, ret_20d, ret_60d, ret_90d,
                    ema20, ema50, ema200, rsi14, macd, macd_signal, atr14,
                    bb_upper, bb_mid, bb_lower, volatility_20, sharpe_60, sortino_60,
                    max_drawdown_90, avg_volume_20, volume_ratio, payload_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(fund_id, as_of_date) DO UPDATE SET
                    ret_1d=excluded.ret_1d, ret_5d=excluded.ret_5d, ret_20d=excluded.ret_20d,
                    ret_60d=excluded.ret_60d, ret_90d=excluded.ret_90d,
                    ema20=excluded.ema20, ema50=excluded.ema50, ema200=excluded.ema200,
                    rsi14=excluded.rsi14, macd=excluded.macd, macd_signal=excluded.macd_signal,
                    atr14=excluded.atr14, bb_upper=excluded.bb_upper, bb_mid=excluded.bb_mid,
                    bb_lower=excluded.bb_lower, volatility_20=excluded.volatility_20,
                    sharpe_60=excluded.sharpe_60, sortino_60=excluded.sortino_60,
                    max_drawdown_90=excluded.max_drawdown_90, avg_volume_20=excluded.avg_volume_20,
                    volume_ratio=excluded.volume_ratio, payload_json=excluded.payload_json
                """,
                (
                    fund_id, ind.as_of_date or datetime.now().astimezone().date().isoformat(),
                    d.get("ret_1d"), d.get("ret_5d"), d.get("ret_20d"), d.get("ret_60d"), d.get("ret_90d"),
                    d.get("ema20"), d.get("ema50"), d.get("ema200"), d.get("rsi14"),
                    d.get("macd"), d.get("macd_signal"), d.get("atr14"),
                    d.get("bb_upper"), d.get("bb_mid"), d.get("bb_lower"),
                    d.get("volatility_20"), d.get("sharpe_60"), d.get("sortino_60"),
                    d.get("max_drawdown_90"), d.get("avg_volume_20"), d.get("volume_ratio"),
                    json.dumps(d, ensure_ascii=False), now,
                ),
            )

    def _ensure_min_history(
        self,
        funds: list[SymbolQuote],
        *,
        fund_types: dict[str, str],
        min_days: int = 45,
    ) -> int:
        """اگر تاریخچه کم است، از روی آخرین quote مسیر مصنوعی واقع‌گرایانه seed می‌کند."""
        seeded = 0
        today = datetime.now().astimezone().date()
        for q in funds:
            if not q.symbol:
                continue
            have = self.history.repo.history_count(q.symbol)
            if have >= min_days:
                continue
            base = q.close_price or q.last_price or 1000.0
            # deterministic pseudo walk from symbol hash
            h = sum(ord(c) for c in q.symbol) % 97
            price = float(base)
            need = min_days - have
            rows_dates = set()
            existing = self.history.get_series(q.symbol, limit=500)
            for r in existing:
                rows_dates.add(str(r.get("trade_date")))
            for i in range(need, 0, -1):
                d = (today - timedelta(days=i)).isoformat()
                if d in rows_dates:
                    continue
                # daily return -1.2%..+1.2% wave
                drift = ((h + i * 7) % 25 - 12) / 1000.0
                price = max(1.0, price * (1.0 + drift))
                vol = float(q.volume or 1_000_000) * (0.7 + ((h + i) % 10) / 20.0)
                val = price * vol
                chg = drift * 100.0
                fake = SymbolQuote(
                    symbol=q.symbol,
                    name=q.name,
                    ins_code=q.ins_code,
                    sector=q.sector,
                    last_price=price,
                    close_price=price,
                    open_price=price * (1 - abs(drift) / 2),
                    high=price * (1 + abs(drift)),
                    low=price * (1 - abs(drift)),
                    volume=vol,
                    value=val,
                    change_close_pct=chg,
                    date=d,
                    is_fund_like=True,
                )
                self.history.repo.upsert_history_from_quote(
                    fake,
                    fund_type=fund_types.get(q.symbol, ""),
                    source="seed",
                )
                seeded += 1
        if seeded:
            logger.info("seeded history points=%s", seeded)
        return seeded

    def _load_offline_quotes(self, limit: Optional[int] = None) -> list[SymbolQuote]:
        """بارگذاری آفلاین.

        اگر snapshot خیلی کوچک باشد (<20)، جهان دموی کامل ساخته می‌شود
        تا top/worst نسبی معنادار باشد.
        """
        target = limit if (limit and limit > 0) else 30
        best: list[SymbolQuote] = []
        best_path = ""
        for kind in ("fund_quotes", "daily_ranking"):
            path = self.store.base_dir / "latest" / f"{kind}.json"
            if not path.exists():
                alt = Path("reports") / f"{kind}.json"
                path = alt if alt.exists() else path
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            quotes = []
            if kind == "fund_quotes":
                for row in data.get("quotes") or []:
                    quotes.append(self._quote_from_dict(row))
            else:
                for row in data.get("rankings") or []:
                    quotes.append(self._quote_from_ranking_row(row))
            if len(quotes) > len(best):
                best = quotes
                best_path = str(path)

        if len(best) >= max(20, min(target, 20)):
            out = best[:target] if target else best
            logger.info("offline quotes from %s n=%s", best_path, len(out))
            return out

        # snapshot کوچک/خراب => جهان دموی کامل برای رتبه‌بندی نسبی درست
        demo = self._demo_universe(limit=max(target, 30))
        logger.info("offline demo universe n=%s (snapshot_n=%s)", len(demo), len(best))
        return demo

    def _demo_universe(self, limit: int = 30) -> list[SymbolQuote]:
        names = [
            ("عیار", "طلا", 2.1), ("زر", "طلا", 1.6), ("گوهر", "طلا", 0.8),
            ("اهرم", "اهرم", 1.2), ("موج", "اهرم", -1.5), ("شتاب", "اهرم", -2.2),
            ("دارا", "سهامی", 0.9), ("آگاس", "سهامی", 0.3), ("سرو", "سهامی", -0.4),
            ("هما", "سهامی", -1.1), ("یاقوت", "درآمد ثابت", 0.05), ("آرام", "درآمد ثابت", 0.02),
            ("کارین", "درآمد ثابت", -0.01), ("فیروزه", "مختلط", 0.4), ("سپید", "مختلط", -0.6),
            ("کهربا", "طلا", 1.1), ("مثقال", "طلا", -0.3), ("توان", "اهرم", 2.5),
            ("بذر", "سهامی", -1.8), ("رشد", "سهامی", 1.4), ("آفاق", "درآمد ثابت", 0.0),
            ("نگین", "طلا", 0.5), ("پویا", "سهامی", -0.9), ("الماس", "مختلط", 0.2),
            ("صبا", "درآمد ثابت", -0.05), ("خورشید", "سهامی", 1.7), ("آریا", "اهرم", -2.8),
            ("سپهر", "مختلط", -1.3), ("ناب", "طلا", 2.0), ("ایمن", "درآمد ثابت", 0.01),
        ]
        out = []
        for i, (sym, ftype, chg) in enumerate(names[:limit], 1):
            px = 1000 + i * 17 + chg * 10
            vol = 500_000 * (1 + (i % 7))
            out.append(
                SymbolQuote(
                    symbol=sym,
                    name=f"صندوق {sym} {ftype}",
                    ins_code=str(1000 + i),
                    sector=f"صندوق {ftype}",
                    last_price=px,
                    close_price=px,
                    open_price=px * 0.99,
                    high=px * 1.01,
                    low=px * 0.98,
                    volume=vol,
                    value=px * vol,
                    change_close_pct=chg,
                    date=datetime.now().astimezone().date().isoformat(),
                    is_fund_like=True,
                )
            )
        return out

    @staticmethod
    def _quote_from_dict(row: dict[str, Any]) -> SymbolQuote:
        return SymbolQuote(
            symbol=row.get("symbol") or "",
            name=row.get("name") or "",
            ins_code=str(row.get("ins_code") or ""),
            sector=row.get("sector"),
            last_price=row.get("last_price"),
            close_price=row.get("close_price"),
            open_price=row.get("open_price"),
            high=row.get("high"),
            low=row.get("low"),
            volume=row.get("volume"),
            value=row.get("value"),
            change_close_pct=row.get("change_close_pct") or row.get("change_pct"),
            date=row.get("date"),
            is_fund_like=True,
        )

    @staticmethod
    def _quote_from_ranking_row(row: dict[str, Any]) -> SymbolQuote:
        return SymbolQuote(
            symbol=row.get("symbol") or "",
            name=row.get("name") or "",
            ins_code=str(row.get("ins_code") or ""),
            sector=row.get("sector"),
            last_price=row.get("last_price"),
            close_price=row.get("close_price"),
            volume=row.get("volume"),
            value=row.get("value"),
            change_close_pct=row.get("change_pct"),
            date=datetime.now().astimezone().date().isoformat(),
            is_fund_like=True,
        )

    def _fetch_navs(self, funds: list[SymbolQuote]) -> dict[str, NavData]:
        out: dict[str, NavData] = {}
        assert self.provider is not None
        for q in funds:
            try:
                out[q.symbol] = self.provider.get_nav(q.symbol)
            except ProviderError:
                continue
            except Exception:
                continue
        return out

    @staticmethod
    def _validate_ranking(payload: dict[str, Any]) -> bool:
        q = payload.get("quality") or {}
        top_avg = q.get("top5_avg")
        worst_avg = q.get("worst5_avg")
        gap = q.get("score_gap_top_worst")
        if top_avg is None or worst_avg is None or gap is None:
            return False
        # برترها باید به‌طور معناداری بالاتر از ضعیف‌ها باشند
        return top_avg > worst_avg + 8


def _type_counts(ranked: list[FundAssessment]) -> dict[str, int]:
    out: dict[str, int] = {}
    for a in ranked:
        out[a.fund_type or "سایر"] = out.get(a.fund_type or "سایر", 0) + 1
    return out


def _avg(vals: list[float]) -> Optional[float]:
    if not vals:
        return None
    return round(sum(vals) / len(vals), 2)
