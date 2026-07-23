"""ربات دستوری + دکمه‌ای صندوقچی (long polling).

دکمه‌های اینلاین فقط وقتی کار می‌کنند که این پروسه در حال اجرا باشد.
اگر BRS در دسترس نباشد از snapshot/دمو استفاده می‌شود تا UI نشکند.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from config import settings
from core.analytics.market_summary import build_market_summary
from core.classification.fund_type import classify_fund_type
from core.preopen.analyzer import PreopenAnalyzer
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.discovery.fund_catalog import FundCatalogService
from services.providers.exceptions import ProviderError
from services.providers.factory import get_market_data_provider
from services.snapshot.store import SnapshotStore
from services.telegram import TelegramService
from services.telegram.keyboards import (
    after_report_keyboard,
    fund_actions_keyboard,
    help_text,
    main_menu_keyboard,
)
from services.telegram.rank_loader import load_rankings
from services.telegram.smart_report import (
    build_smart_morning_messages,
    format_market_summary_telegram,
    format_top_fund_messages,
    format_worst_fund_messages,
)
from services.telegram_publisher import (
    format_fund_telegram,
    format_preopen_telegram,
    format_ranking_telegram,
)

logger = logging.getLogger(__name__)


class SandoghchiBot:
    def __init__(
        self,
        telegram: Optional[TelegramService] = None,
        poll_timeout: int = 25,
        warm_cache: bool = True,
    ) -> None:
        self.telegram = telegram or TelegramService()
        if not self.telegram.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
        self.poll_timeout = poll_timeout
        self.offset: Optional[int] = None
        self.provider = None
        try:
            self.provider = get_market_data_provider()
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider init failed: %s", exc)
        self.engine = ScoreEngine()
        self.store = SnapshotStore()
        self._ranked_cache: list[FundAssessment] = []
        self._ranked_at: float = 0.0
        self._ranked_source: str = ""
        self._warming = False
        self.warm_cache = warm_cache

    # ------------------------------------------------------------------ run
    def setup(self) -> dict[str, Any]:
        dropped = self.telegram.api("deleteWebhook", {"drop_pending_updates": False})
        me = self.telegram.get_me()
        info = {
            "delete_webhook": bool(dropped.get("ok")),
            "bot": (me.get("result") or {}),
        }
        logger.info(
            "bot setup ok=@%s webhook_cleared=%s",
            info["bot"].get("username"),
            info["delete_webhook"],
        )
        if self.warm_cache:
            try:
                ranked = self._get_ranked()
                logger.info("warm cache source=%s n=%s", self._ranked_source, len(ranked))
            except Exception as exc:  # noqa: BLE001
                logger.warning("warm cache failed: %s", exc)
        return info

    def run_forever(self) -> None:
        info = self.setup()
        uname = info.get("bot", {}).get("username", "?")
        logger.info("bot polling started @%s", uname)
        while True:
            try:
                self._poll_once()
            except KeyboardInterrupt:
                logger.info("bot stopped by user")
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("poll loop error: %s", exc)
                time.sleep(2)

    def _poll_once(self) -> None:
        params: dict[str, Any] = {
            "timeout": self.poll_timeout,
            "allowed_updates": ["message", "callback_query", "channel_post"],
        }
        if self.offset is not None:
            params["offset"] = self.offset
        old_timeout = self.telegram.timeout
        self.telegram.timeout = max(old_timeout, float(self.poll_timeout) + 15)
        try:
            data = self.telegram.api("getUpdates", params)
        finally:
            self.telegram.timeout = old_timeout

        if not data.get("ok"):
            logger.warning("getUpdates failed: %s", str(data)[:300])
            time.sleep(1)
            return

        for upd in data.get("result") or []:
            self.offset = int(upd["update_id"]) + 1
            try:
                self._handle_update(upd)
            except Exception as exc:  # noqa: BLE001
                logger.exception("handle update failed: %s", exc)

    def _handle_update(self, upd: dict[str, Any]) -> None:
        if "callback_query" in upd:
            self._handle_callback(upd["callback_query"])
            return

        msg = upd.get("message") or upd.get("edited_message") or upd.get("channel_post")
        if not msg:
            return
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = (msg.get("text") or "").strip()
        if not chat_id or not text:
            return

        if chat.get("type") == "channel" and not text.startswith("/"):
            return

        if text.startswith("/"):
            self._handle_command(chat_id, text)
        else:
            self._reply(chat_id, self._cmd_fund(text.split()[0]))

    def _handle_callback(self, cq: dict[str, Any]) -> None:
        cq_id = str(cq.get("id") or "")
        data = str(cq.get("data") or "")
        msg = cq.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        user = cq.get("from") or {}
        user_id = str(user.get("id") or "")

        # فوراً loading دکمه را ببند
        self.telegram.answer_callback_query(cq_id, text="⏳ اجرا…")

        target = chat_id or user_id
        if not target:
            logger.warning("callback without target data=%s", data)
            return

        logger.info("callback data=%s chat=%s user=%s", data, chat_id, user_id)

        # اگر از کانال زده شده و کاربر خصوصی دارد، هم به کانال هم خصوصی جواب مفید بده
        # (کانال برای گزارش عمومی، خصوصی برای تعامل)
        try:
            if data.startswith("cmd:"):
                cmd = data.split(":", 1)[1].strip().lower()
                self._run_command(target, cmd, args="")
                # اگر کانال بود و user جدا، منوی خصوصی هم بفرست تا دکمه‌ها برایش شخصی کار کند
                if chat.get("type") == "channel" and user_id and user_id != target:
                    try:
                        self._cmd_start(user_id)
                    except Exception:
                        pass
            elif data.startswith("fund:"):
                symbol = data.split(":", 1)[1].strip()
                text = self._cmd_fund(symbol)
                self._reply(target, text, reply_markup=fund_actions_keyboard(symbol))
            else:
                self._reply(target, "دکمه ناشناخته. /menu", reply_markup=main_menu_keyboard())
        except Exception as exc:  # noqa: BLE001
            logger.exception("callback handler failed: %s", exc)
            self._reply(target, f"خطا: {exc}", reply_markup=main_menu_keyboard())

    def _handle_command(self, chat_id: str, text: str) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].split("@")[0].lstrip("/").lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        self._run_command(chat_id, cmd, args=args)

    def _run_command(self, chat_id: str, cmd: str, args: str = "") -> None:
        logger.info("command /%s chat=%s args=%r", cmd, chat_id, args)
        try:
            if cmd in {"start", "menu"}:
                self._cmd_start(chat_id)
            elif cmd == "help":
                self._reply(chat_id, help_text(), reply_markup=main_menu_keyboard())
            elif cmd == "today":
                self._send_today(chat_id)
            elif cmd == "top":
                self._send_top(chat_id)
            elif cmd == "worst":
                self._send_worst(chat_id)
            elif cmd == "rank":
                ranked = self._get_ranked()
                text_out = format_ranking_telegram(ranked, top_n=12, worst_n=6)
                note = self._source_note()
                self._reply(chat_id, note + text_out, reply_markup=after_report_keyboard())
            elif cmd == "preopen":
                self._send_preopen(chat_id)
            elif cmd == "market":
                self._send_market(chat_id)
            elif cmd == "gold":
                self._send_group(chat_id, "طلا")
            elif cmd == "fixed":
                self._send_group(chat_id, "درآمد ثابت")
            elif cmd == "stock":
                self._send_group(chat_id, "سهامی")
            elif cmd == "leverage":
                self._send_group(chat_id, "اهرم")
            elif cmd == "refresh":
                self._ranked_cache = []
                self._ranked_at = 0.0
                self._reply(chat_id, "کش پاک شد. تلاش برای داده زنده…")
                self._get_ranked(prefer_live=True)
                self._send_today(chat_id)
            elif cmd == "fund":
                if not args:
                    self._reply(chat_id, "مثال: /fund عیار", reply_markup=main_menu_keyboard())
                    return
                self._reply(
                    chat_id,
                    self._cmd_fund(args),
                    reply_markup=fund_actions_keyboard(args.strip()),
                )
            else:
                self._reply(
                    chat_id,
                    "دستور ناشناخته. از دکمه‌ها یا /menu استفاده کنید.",
                    reply_markup=main_menu_keyboard(),
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception("command %s failed: %s", cmd, exc)
            self._reply(chat_id, f"خطا در اجرای دستور: {exc}", reply_markup=main_menu_keyboard())

    # -------------------------------------------------------------- commands
    def _cmd_start(self, chat_id: str) -> None:
        text = (
            f"سلام 👋 به {settings.PRODUCT_NAME} خوش آمدید.\n"
            "\n"
            "دکمه‌های زیر را بزنید.\n"
            "پیشنهاد: «📊 امروز»\n"
            "\n"
            "نکته: برای کارکرد کامل دکمه‌ها، همین ربات باید در حال اجرا باشد."
        )
        self._reply(chat_id, text, reply_markup=main_menu_keyboard())

    def _source_note(self) -> str:
        if self._ranked_source == "demo":
            return "⚠️ داده نمایشی (BRS در دسترس نبود)\n\n"
        if self._ranked_source == "snapshot":
            return "ℹ️ از آخرین snapshot محلی\n\n"
        return ""

    def _send_today(self, chat_id: str) -> None:
        self._reply(chat_id, "⏳ در حال محاسبه گزارش هوشمند…")
        ranked = self._get_ranked()
        msgs = build_smart_morning_messages(ranked, top_n=5, worst_n=5)
        if self._ranked_source in {"demo", "snapshot"}:
            msgs[0] = self._source_note() + msgs[0]
        self.telegram.send_messages(
            msgs,
            chat_id=chat_id,
            reply_markup_last=after_report_keyboard(),
        )

    def _send_top(self, chat_id: str) -> None:
        self._reply(chat_id, "⏳ برترین‌ها…")
        ranked = self._get_ranked()
        msgs = format_top_fund_messages(ranked, n=5)
        if not msgs:
            self._reply(chat_id, "داده‌ای نیست.", reply_markup=main_menu_keyboard())
            return
        if self._ranked_source in {"demo", "snapshot"}:
            msgs[0] = self._source_note() + msgs[0]
        self.telegram.send_messages(
            msgs,
            chat_id=chat_id,
            reply_markup_last=after_report_keyboard(),
        )

    def _send_worst(self, chat_id: str) -> None:
        self._reply(chat_id, "⏳ ضعیف‌ها…")
        ranked = self._get_ranked()
        msgs = format_worst_fund_messages(ranked, n=5)
        if not msgs:
            self._reply(chat_id, "داده‌ای نیست.", reply_markup=main_menu_keyboard())
            return
        self.telegram.send_messages(
            msgs,
            chat_id=chat_id,
            reply_markup_last=after_report_keyboard(),
        )

    def _send_market(self, chat_id: str) -> None:
        ranked = self._get_ranked()
        text = self._source_note() + format_market_summary_telegram(ranked)
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_preopen(self, chat_id: str) -> None:
        self._reply(chat_id, "⏳ اسکن پیش‌گشایش…")
        try:
            if self.provider is None:
                raise RuntimeError("provider unavailable")
            funds = FundCatalogService(provider=self.provider, store=self.store).discover()
            types = {q.symbol: classify_fund_type(q) for q in funds}
            signals = PreopenAnalyzer().rank(funds, fund_types=types)
            text = format_preopen_telegram(signals)
        except Exception as exc:  # noqa: BLE001
            logger.warning("preopen failed: %s", exc)
            text = (
                "⚠️ پیش‌گشایش الان در دسترس نیست (داده زنده BRS).\n"
                f"جزئیات: {exc}\n"
                "از /today یا /market استفاده کنید."
            )
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_group(self, chat_id: str, fund_type: str) -> None:
        ranked = self._get_ranked()
        items = [a for a in ranked if fund_type in (a.fund_type or "")]
        if not items:
            self._reply(
                chat_id,
                f"صندوقی در گروه «{fund_type}» پیدا نشد.",
                reply_markup=main_menu_keyboard(),
            )
            return
        lines = [
            self._source_note().rstrip(),
            f"📁 {settings.PRODUCT_NAME} | گروه {fund_type}",
            f"تعداد: {len(items)}",
            "",
            "🏆 برترین‌های گروه",
        ]
        for a in items[:8]:
            chg = f"{a.change_pct:+.2f}%" if a.change_pct is not None else "-"
            lines.append(
                f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label} | {chg}"
            )
        self._reply(chat_id, "\n".join([x for x in lines if x is not None]), reply_markup=after_report_keyboard())

    def _cmd_fund(self, symbol: str) -> str:
        symbol = (symbol or "").strip()
        if not symbol:
            return "نماد خالی است. مثال: /fund عیار"

        # اول از کش رنکینگ
        ranked = self._get_ranked()
        for a in ranked:
            if a.symbol == symbol or symbol in a.symbol or symbol in a.name:
                return format_fund_telegram(a)

        if self.provider is None:
            return f"نماد «{symbol}» در کش نیست و provider در دسترس نیست."

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

    # ---------------------------------------------------------------- helpers
    def _reply(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: Optional[dict[str, Any]] = None,
    ) -> None:
        ok = self.telegram.send_message(text, chat_id=str(chat_id), reply_markup=reply_markup)
        if not ok:
            logger.error("reply failed chat=%s chars=%s", chat_id, len(text or ""))

    def _get_ranked(self, max_age_sec: float = 1800, prefer_live: bool | None = None) -> list[FundAssessment]:
        import os

        now = time.time()
        if self._ranked_cache and (now - self._ranked_at) < max_age_sec:
            return self._ranked_cache
        if self._warming:
            while self._warming:
                time.sleep(0.15)
            if self._ranked_cache:
                return self._ranked_cache

        # پیش‌فرض: اول snapshot (سریع) — live فقط با refresh یا prefer_live
        if prefer_live is None:
            prefer_live = os.getenv("BOT_PREFER_LIVE", "").lower() in {"1", "true", "yes"}

        self._warming = True
        try:
            ranked, source = load_rankings(
                provider=self.provider if prefer_live else None,
                store=self.store,
                engine=self.engine,
                allow_live=bool(prefer_live and self.provider is not None),
                allow_demo=True,
            )
            # اگر snapshot خالی بود و provider داریم، live را یک‌بار امتحان کن
            if not ranked and self.provider is not None:
                ranked, source = load_rankings(
                    provider=self.provider,
                    store=self.store,
                    engine=self.engine,
                    allow_live=True,
                    allow_demo=True,
                )
            self._ranked_cache = ranked
            self._ranked_source = source
            self._ranked_at = time.time()
            summary = build_market_summary(ranked)
            logger.info(
                "ranked ready source=%s n=%s power=%s best=%s",
                source,
                summary.funds_count,
                summary.market_power,
                summary.best_group,
            )
            return ranked
        finally:
            self._warming = False
