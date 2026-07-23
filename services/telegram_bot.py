"""ربات دستوری ساده صندوقچی (long polling).

دستورها:
  /start /help /rank /worst /preopen /fund <نماد> /market
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import requests

from config import settings
from core.classification.fund_type import classify_fund_type
from core.preopen.analyzer import PreopenAnalyzer
from core.ranking.fund_ranker import FundRanker
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.discovery.fund_catalog import FundCatalogService
from services.providers.exceptions import ProviderError
from services.providers.factory import get_market_data_provider
from services.snapshot.store import SnapshotStore
from services.telegram import TelegramService
from services.telegram_publisher import (format_fund_telegram,
                                         format_preopen_telegram,
                                         format_ranking_telegram)

logger = logging.getLogger(__name__)


class SandoghchiBot:
    def __init__(
        self,
        telegram: Optional[TelegramService] = None,
        poll_timeout: int = 25,
    ) -> None:
        self.telegram = telegram or TelegramService()
        if not self.telegram.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
        self.poll_timeout = poll_timeout
        self.session = requests.Session()
        self.offset: Optional[int] = None
        self.provider = get_market_data_provider()
        self.engine = ScoreEngine()
        self.store = SnapshotStore()
        self.ranker = FundRanker()
        self._ranked_cache: list[FundAssessment] = []
        self._ranked_at: float = 0.0

    def run_forever(self) -> None:
        logger.info("Sandoghchi bot polling started")
        while True:
            try:
                updates = self.get_updates()
                for upd in updates:
                    self.handle_update(upd)
            except Exception as exc:  # noqa: BLE001
                logger.exception("poll loop error: %s", exc)
                time.sleep(2)

    def get_updates(self) -> list[dict[str, Any]]:
        url = f"https://api.telegram.org/bot{self.telegram.bot_token}/getUpdates"
        params: dict[str, Any] = {"timeout": self.poll_timeout}
        if self.offset is not None:
            params["offset"] = self.offset
        r = self.session.get(url, params=params, timeout=self.poll_timeout + 10)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"getUpdates failed: {data}")
        updates = data.get("result") or []
        for upd in updates:
            self.offset = int(upd["update_id"]) + 1
        return updates

    from services.telegram.storage.users import register
from services.telegram.handlers.start import WELCOME


def handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("channel_post") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = (message.get("text") or "").strip()
        if not chat_id or not text or not text.startswith("/"):
            return

        cmd_part = text.split()[0]
        cmd = cmd_part.split("@", 1)[0].lower()
        args = text[len(cmd_part):].strip()

        reply = self.dispatch(cmd, args)
        if reply:
            self.telegram.send_message(reply, chat_id=chat_id)

    def dispatch(self, cmd: str, args: str) -> str:
        try:
            if cmd in {"/start", "/help"}:
                return self.cmd_help()
            if cmd == "/rank":
                return self.cmd_rank()
            if cmd == "/worst":
                return self.cmd_worst()
            if cmd == "/preopen":
                return self.cmd_preopen()
            if cmd == "/market":
                return self.cmd_market()
            if cmd == "/fund":
                if not args:
                    return "مثال: /fund عیار"
                return self.cmd_fund(args)
            return "دستور ناشناخته. /help را ببینید."
        except Exception as exc:  # noqa: BLE001
            logger.exception("command failed %s", cmd)
            return f"خطا در اجرای دستور: {exc}"

    def cmd_help(self) -> str:
        return (
            f"👋 به {settings.PRODUCT_NAME} خوش آمدید\n\n"
            "دستورها:\n"
            "/rank — برترین صندوق‌ها\n"
            "/worst — ضعیف‌ترین‌ها\n"
            "/preopen — وضعیت پیش‌سفارش\n"
            "/fund عیار — جزئیات یک صندوق\n"
            "/market — خلاصه بازار صندوق‌ها\n"
            "/help — راهنما\n\n"
            "گزارش‌های زمان‌بندی‌شده در کانال منتشر می‌شوند."
        )

    def cmd_rank(self) -> str:
        ranked = self._get_ranked()
        return format_ranking_telegram(ranked, top_n=15, worst_n=0)

    def cmd_worst(self) -> str:
        ranked = self._get_ranked()
        worst = list(reversed(ranked[-10:])) if ranked else []
        lines = [f"⚠️ {settings.PRODUCT_NAME} | ضعیف‌ترین صندوق‌ها", ""]
        for a in worst:
            lines.append(f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
            if a.summary_reasons:
                lines.append(f"   • {a.summary_reasons[0]}")
        return "\n".join(lines) if worst else "داده‌ای نیست."

    def cmd_preopen(self) -> str:
        funds = FundCatalogService(provider=self.provider, store=self.store).discover()
        types = {q.symbol: classify_fund_type(q) for q in funds}
        signals = PreopenAnalyzer().rank(funds, fund_types=types)
        return format_preopen_telegram(signals, top_n=15)

    def cmd_market(self) -> str:
        ranked = self._get_ranked()
        if not ranked:
            return "هنوز رنکینگی موجود نیست."
        n = len(ranked)
        buys = sum(1 for a in ranked if a.recommendation in {"strong_buy", "buy"})
        sells = sum(1 for a in ranked if a.recommendation in {"weak", "sell"})
        avg = sum(a.final_score for a in ranked) / n
        by_type: dict[str, int] = {}
        for a in ranked:
            by_type[a.fund_type] = by_type.get(a.fund_type, 0) + 1
        lines = [
            f"📈 {settings.PRODUCT_NAME} | خلاصه بازار صندوق‌ها",
            f"تعداد: {n}",
            f"میانگین امتیاز: {avg:.1f}",
            f"توصیه خرید/قوی: {buys}",
            f"ضعیف/فروش: {sells}",
            "",
            "ترکیب انواع:",
        ]
        for t, c in sorted(by_type.items(), key=lambda kv: -kv[1])[:10]:
            lines.append(f"• {t}: {c}")
        lines.append("")
        lines.append(f"بهترین: {ranked[0].symbol} ({ranked[0].final_score:.1f})")
        lines.append(f"ضعیف‌ترین: {ranked[-1].symbol} ({ranked[-1].final_score:.1f})")
        return "\n".join(lines)

    def cmd_fund(self, symbol: str) -> str:
        symbol = symbol.strip()
        try:
            quote = self.provider.get_symbol(symbol)
        except ProviderError as exc:
            return f"خطا در دریافت نماد {symbol}: {exc}"
        nav = None
        try:
            nav = self.provider.get_nav(quote.symbol)
        except ProviderError:
            nav = None
        assessment = self.engine.assess(quote, nav=nav)
        return format_fund_telegram(assessment)

    def _get_ranked(self, max_age_sec: float = 1800) -> list[FundAssessment]:
        now = time.time()
        if self._ranked_cache and (now - self._ranked_at) < max_age_sec:
            return self._ranked_cache
        funds = FundCatalogService(provider=self.provider, store=self.store).discover()
        assessments = [self.engine.assess(q, nav=None) for q in funds]
        ranked = self.ranker.rank(assessments)
        self._ranked_cache = ranked
        self._ranked_at = now
        return ranked
