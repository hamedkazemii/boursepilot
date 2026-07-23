"""ربات صندوقچی: رنکینگ روندی + پروفایل/پرتفو + مشاور AI."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from config import settings
from core.ai.advisor import AIAdvisor
from core.analytics.market_summary import build_market_summary
from core.classification.fund_type import classify_fund_type
from core.preopen.analyzer import PreopenAnalyzer
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.discovery.fund_catalog import FundCatalogService
from services.portfolio.service import PortfolioService
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
from services.telegram.rank_loader import get_cached_payload, load_rankings
from services.telegram.smart_report import (
    build_smart_morning_messages,
    format_fund_card,
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
        try:
            self.provider = get_market_data_provider()
        except Exception as exc:  # noqa: BLE001
            logger.warning("provider init failed: %s", exc)
            self.provider = None
        self.engine = ScoreEngine()
        self.store = SnapshotStore()
        self.portfolio = PortfolioService()
        self.ai = AIAdvisor()
        self._ranked_cache: list[FundAssessment] = []
        self._ranked_at = 0.0
        self._ranked_source = ""
        self._awaiting_ask: set[str] = set()
        self.warm_cache = warm_cache

    def setup(self) -> dict[str, Any]:
        dropped = self.telegram.api("deleteWebhook", {"drop_pending_updates": False})
        me = self.telegram.get_me()
        info = {"delete_webhook": bool(dropped.get("ok")), "bot": (me.get("result") or {})}
        logger.info("bot setup @%s", info["bot"].get("username"))
        if self.warm_cache:
            try:
                self._get_ranked()
            except Exception as exc:  # noqa: BLE001
                logger.warning("warm failed: %s", exc)
        return info

    def run_forever(self) -> None:
        info = self.setup()
        logger.info("polling @%s", info.get("bot", {}).get("username"))
        while True:
            try:
                self._poll_once()
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.exception("poll error: %s", exc)
                time.sleep(2)

    def _poll_once(self) -> None:
        params: dict[str, Any] = {
            "timeout": self.poll_timeout,
            "allowed_updates": ["message", "callback_query", "channel_post"],
        }
        if self.offset is not None:
            params["offset"] = self.offset
        old = self.telegram.timeout
        self.telegram.timeout = max(old, float(self.poll_timeout) + 15)
        try:
            data = self.telegram.api("getUpdates", params)
        finally:
            self.telegram.timeout = old
        if not data.get("ok"):
            time.sleep(1)
            return
        for upd in data.get("result") or []:
            self.offset = int(upd["update_id"]) + 1
            try:
                self._handle_update(upd)
            except Exception as exc:  # noqa: BLE001
                logger.exception("update failed: %s", exc)

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
        user = msg.get("from") or {}
        if chat_id and user:
            self.portfolio.ensure_user(
                user.get("id") or chat_id,
                username=user.get("username") or "",
                first_name=user.get("first_name") or "",
                last_name=user.get("last_name") or "",
            )
        if not chat_id or not text:
            return
        if chat.get("type") == "channel" and not text.startswith("/"):
            return
        if text.startswith("/"):
            self._handle_command(chat_id, text, user=user)
            return
        # free text
        uid = str(user.get("id") or chat_id)
        if uid in self._awaiting_ask or chat.get("type") == "private":
            self._awaiting_ask.discard(uid)
            self._cmd_ask(chat_id, text, user=user)
        else:
            self._reply(chat_id, self._cmd_fund(text.split()[0]), reply_markup=fund_actions_keyboard(text.split()[0]))

    def _handle_callback(self, cq: dict[str, Any]) -> None:
        cq_id = str(cq.get("id") or "")
        data = str(cq.get("data") or "")
        msg = cq.get("message") or {}
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        user = cq.get("from") or {}
        user_id = str(user.get("id") or "")
        self.telegram.answer_callback_query(cq_id, text="⏳")
        target = chat_id or user_id
        if user_id:
            self.portfolio.ensure_user(
                user_id,
                username=user.get("username") or "",
                first_name=user.get("first_name") or "",
                last_name=user.get("last_name") or "",
            )
        logger.info("callback %s chat=%s user=%s", data, chat_id, user_id)
        try:
            if data.startswith("cmd:"):
                self._run_command(target, data.split(":", 1)[1], args="", user=user)
            elif data.startswith("fund:"):
                sym = data.split(":", 1)[1]
                self._reply(target, self._cmd_fund(sym), reply_markup=fund_actions_keyboard(sym))
            elif data.startswith("watch:"):
                sym = data.split(":", 1)[1]
                self.portfolio.add_watch(user_id or target, sym)
                self._reply(target, f"⭐ {sym} به واچ‌لیست اضافه شد.", reply_markup=after_report_keyboard())
            elif data.startswith("pfadd:"):
                sym = data.split(":", 1)[1]
                self._reply(
                    target,
                    f"برای افزودن {sym} بفرستید:\n/pf_add {sym} <تعداد> [قیمت‌خرید]",
                    reply_markup=main_menu_keyboard(),
                )
            else:
                self._reply(target, "دکمه ناشناخته", reply_markup=main_menu_keyboard())
        except Exception as exc:  # noqa: BLE001
            logger.exception("callback failed: %s", exc)
            self._reply(target, f"خطا: {exc}", reply_markup=main_menu_keyboard())

    def _handle_command(self, chat_id: str, text: str, user: Optional[dict] = None) -> None:
        parts = text.split(maxsplit=1)
        cmd = parts[0].split("@")[0].lstrip("/").lower()
        args = parts[1].strip() if len(parts) > 1 else ""
        self._run_command(chat_id, cmd, args=args, user=user or {})

    def _run_command(self, chat_id: str, cmd: str, args: str = "", user: Optional[dict] = None) -> None:
        user = user or {}
        uid = str(user.get("id") or chat_id)
        logger.info("cmd /%s chat=%s", cmd, chat_id)
        try:
            if cmd in {"start", "menu"}:
                self.portfolio.ensure_user(uid, username=user.get("username") or "", first_name=user.get("first_name") or "")
                self._reply(
                    chat_id,
                    f"سلام 👋 به {settings.PRODUCT_NAME} خوش آمدید.\nپروفایل شما ساخته/به‌روز شد.\nاز منو استفاده کنید.",
                    reply_markup=main_menu_keyboard(),
                )
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
                self._reply(chat_id, self._source_note() + format_ranking_telegram(ranked), reply_markup=after_report_keyboard())
            elif cmd == "market":
                self._send_market(chat_id)
            elif cmd == "preopen":
                self._send_preopen(chat_id)
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
                self._ranked_at = 0
                self._reply(chat_id, "در حال بروزرسانی…")
                self._get_ranked(force=True)
                self._send_today(chat_id)
            elif cmd == "fund":
                if not args:
                    self._reply(chat_id, "مثال: /fund عیار", reply_markup=main_menu_keyboard())
                    return
                self._reply(chat_id, self._cmd_fund(args), reply_markup=fund_actions_keyboard(args.split()[0]))
            elif cmd in {"profile", "me"}:
                self._cmd_profile(chat_id, uid)
            elif cmd == "risk":
                val = (args or "medium").split()[0].lower()
                mapping = {"low": "low", "کم": "low", "medium": "medium", "متوسط": "medium", "high": "high", "زیاد": "high"}
                rp = mapping.get(val, "medium")
                self.portfolio.update_profile(uid, risk_profile=rp)
                self._reply(chat_id, f"ریسک پروفایل = {rp}", reply_markup=main_menu_keyboard())
            elif cmd == "capital":
                num = _parse_number(args)
                if num is None:
                    self._reply(chat_id, "مثال: /capital 50000000")
                    return
                self.portfolio.update_profile(uid, capital=num)
                self._reply(chat_id, f"سرمایه ثبت شد: {num:,.0f}", reply_markup=main_menu_keyboard())
            elif cmd in {"portfolio", "pf"}:
                self._cmd_portfolio(chat_id, uid)
            elif cmd in {"pf_add", "add"}:
                self._cmd_pf_add(chat_id, uid, args)
            elif cmd in {"pf_del", "del"}:
                if not args:
                    self._reply(chat_id, "مثال: /pf_del عیار")
                    return
                self.portfolio.remove_holding(uid, args.split()[0])
                self._reply(chat_id, f"حذف شد: {args.split()[0]}", reply_markup=after_report_keyboard())
            elif cmd == "watch":
                if not args:
                    self._reply(chat_id, "مثال: /watch عیار")
                    return
                self.portfolio.add_watch(uid, args.split()[0])
                self._reply(chat_id, f"⭐ {args.split()[0]} اضافه شد", reply_markup=after_report_keyboard())
            elif cmd in {"watchlist", "watch"}:
                items = self.portfolio.list_watch(uid)
                self._reply(chat_id, "⭐ واچ‌لیست:\n" + ("\n".join(f"• {x}" for x in items) if items else "خالی"), reply_markup=main_menu_keyboard())
            elif cmd in {"ask", "ai", "مشاور"}:
                if not args:
                    self._awaiting_ask.add(uid)
                    self._reply(chat_id, "سوال خود را بفرستید.\nمثال: ۵۰ میلیون ریسک کم یک‌ساله")
                    return
                self._cmd_ask(chat_id, args, user=user)
            else:
                self._reply(chat_id, "دستور ناشناخته. /help", reply_markup=main_menu_keyboard())
        except Exception as exc:  # noqa: BLE001
            logger.exception("cmd failed: %s", exc)
            self._reply(chat_id, f"خطا: {exc}", reply_markup=main_menu_keyboard())

    # ---- sends ----
    def _source_note(self) -> str:
        if self._ranked_source == "live":
            return ""
        if self._ranked_source in {"offline", "demo", "snapshot"}:
            return f"ℹ️ منبع داده: {self._ranked_source} (در صورت قطع BRS)\n\n"
        return ""

    def _send_today(self, chat_id: str) -> None:
        self._reply(chat_id, "⏳ تحلیل روندی همه صندوق‌ها…")
        ranked = self._get_ranked()
        n = len(ranked)
        top_n = 5 if n >= 10 else max(1, n // 2)
        worst_n = 5 if n >= 10 else max(1, n // 2)
        msgs = build_smart_morning_messages(ranked, meta=get_cached_payload(), top_n=top_n, worst_n=worst_n)
        if self._source_note():
            msgs[0] = self._source_note() + msgs[0]
        # sanity footer
        if n >= 10:
            gap = ranked[0].final_score - ranked[-1].final_score
            msgs[0] += f"\n\n✅ جهان تحلیل: {n} صندوق | فاصله بهترین تا ضعیف‌ترین: {gap:.1f}"
        self.telegram.send_messages(msgs, chat_id=chat_id, reply_markup_last=after_report_keyboard())

    def _send_top(self, chat_id: str) -> None:
        ranked = self._get_ranked()
        msgs = format_top_fund_messages(ranked, n=5)
        if self._source_note() and msgs:
            msgs[0] = self._source_note() + msgs[0]
        self.telegram.send_messages(msgs, chat_id=chat_id, reply_markup_last=after_report_keyboard())

    def _send_worst(self, chat_id: str) -> None:
        ranked = self._get_ranked()
        # ensure true bottom
        worst = list(reversed(ranked[-5:])) if len(ranked) >= 5 else list(reversed(ranked))
        msgs = [format_fund_card(a, kind="worst") for a in worst]
        if self._source_note() and msgs:
            msgs[0] = self._source_note() + msgs[0]
        # hard check scores
        if ranked and worst and worst[0].final_score > ranked[0].final_score:
            self._reply(chat_id, "خطای منطقی رتبه‌بندی شناسایی شد؛ در حال بازسازی…")
            self._ranked_cache = []
            ranked = self._get_ranked(force=True)
            worst = list(reversed(ranked[-5:]))
            msgs = [format_fund_card(a, kind="worst") for a in worst]
        self.telegram.send_messages(msgs, chat_id=chat_id, reply_markup_last=after_report_keyboard())

    def _send_market(self, chat_id: str) -> None:
        ranked = self._get_ranked()
        self._reply(chat_id, self._source_note() + format_market_summary_telegram(ranked, meta=get_cached_payload()), reply_markup=after_report_keyboard())

    def _send_preopen(self, chat_id: str) -> None:
        try:
            if not self.provider:
                raise RuntimeError("provider offline")
            funds = FundCatalogService(provider=self.provider, store=self.store).discover()
            types = {q.symbol: classify_fund_type(q) for q in funds}
            signals = PreopenAnalyzer().rank(funds, fund_types=types)
            text = format_preopen_telegram(signals)
        except Exception as exc:  # noqa: BLE001
            text = f"پیش‌گشایش در دسترس نیست: {exc}"
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_group(self, chat_id: str, fund_type: str) -> None:
        ranked = [a for a in self._get_ranked() if fund_type in (a.fund_type or "")]
        if not ranked:
            self._reply(chat_id, f"گروه {fund_type} یافت نشد", reply_markup=main_menu_keyboard())
            return
        lines = [f"📁 گروه {fund_type} | n={len(ranked)}", "🏆 برتر گروه:"]
        for a in ranked[:5]:
            lines.append(f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
        lines.append("⚠️ ضعیف گروه:")
        for a in list(reversed(ranked[-3:])):
            lines.append(f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
        self._reply(chat_id, "\n".join(lines), reply_markup=after_report_keyboard())

    def _cmd_fund(self, symbol: str) -> str:
        symbol = symbol.strip()
        ranked = self._get_ranked()
        for a in ranked:
            if a.symbol == symbol or symbol in a.symbol or symbol in (a.name or ""):
                return format_fund_telegram(a)
        if self.provider:
            try:
                q = self.provider.get_symbol(symbol)
                nav = None
                try:
                    nav = self.provider.get_nav(symbol)
                except ProviderError:
                    pass
                return format_fund_telegram(self.engine.assess(q, nav=nav))
            except Exception as exc:  # noqa: BLE001
                return f"خطا: {exc}"
        return f"نماد {symbol} پیدا نشد"

    def _cmd_profile(self, chat_id: str, uid: str) -> None:
        u = self.portfolio.ensure_user(uid)
        text = (
            "👤 پروفایل شما\n"
            f"شناسه: {u.get('telegram_id')}\n"
            f"نام: {u.get('first_name') or ''} {u.get('last_name') or ''}\n"
            f"ریسک: {u.get('risk_profile')}\n"
            f"افق: {u.get('horizon_months')} ماه\n"
            f"سرمایه: {float(u.get('capital') or 0):,.0f}\n\n"
            "تنظیم:\n/risk low|medium|high\n/capital 50000000"
        )
        self._reply(chat_id, text, reply_markup=main_menu_keyboard())

    def _cmd_portfolio(self, chat_id: str, uid: str) -> None:
        ranked = self._get_ranked()
        prices = {a.symbol: float(a.last_price or a.close_price or 0) for a in ranked if a.last_price or a.close_price}
        text = self.portfolio.portfolio_summary_text(uid, prices=prices)
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _cmd_pf_add(self, chat_id: str, uid: str, args: str) -> None:
        parts = args.split()
        if len(parts) < 2:
            self._reply(chat_id, "مثال: /pf_add عیار 100 25000")
            return
        sym = parts[0]
        qty = _parse_number(parts[1])
        cost = _parse_number(parts[2]) if len(parts) > 2 else None
        if qty is None:
            self._reply(chat_id, "تعداد نامعتبر است")
            return
        self.portfolio.upsert_holding(uid, sym, quantity=qty, avg_cost=cost)
        self._reply(chat_id, f"✅ {sym} ثبت شد (qty={qty})", reply_markup=after_report_keyboard())

    def _cmd_ask(self, chat_id: str, question: str, user: Optional[dict] = None) -> None:
        uid = str((user or {}).get("id") or chat_id)
        u = self.portfolio.ensure_user(uid)
        ranked = self._get_ranked()
        pf = self.portfolio.portfolio_summary_text(uid)
        ans = self.ai.answer(question, user=u, ranked=ranked, portfolio_text=pf)
        # store chat
        try:
            from core.database.connection import get_database
            db = get_database()
            now = time.strftime("%Y-%m-%dT%H:%M:%S")
            with db.transaction() as conn:
                conn.execute(
                    "INSERT INTO chat_messages(user_id, telegram_id, role, content, created_at) VALUES (?,?,?,?,?)",
                    (u["id"], uid, "user", question, now),
                )
                conn.execute(
                    "INSERT INTO chat_messages(user_id, telegram_id, role, content, created_at) VALUES (?,?,?,?,?)",
                    (u["id"], uid, "assistant", ans, now),
                )
        except Exception:
            pass
        self._reply(chat_id, ans, reply_markup=after_report_keyboard())

    def _reply(self, chat_id: str, text: str, *, reply_markup: Optional[dict[str, Any]] = None) -> None:
        self.telegram.send_message(text, chat_id=str(chat_id), reply_markup=reply_markup)

    def _get_ranked(self, force: bool = False, max_age_sec: float = 900) -> list[FundAssessment]:
        now = time.time()
        if not force and self._ranked_cache and (now - self._ranked_at) < max_age_sec:
            return self._ranked_cache
        ranked, source = load_rankings(provider=self.provider, allow_live=True, allow_demo=True)
        # sanity: top score must exceed worst
        if len(ranked) >= 5 and ranked[0].final_score <= ranked[-1].final_score:
            logger.error("ranking sanity failed; rebuilding offline")
            ranked, source = load_rankings(provider=None, allow_live=False, allow_demo=True)
        self._ranked_cache = ranked
        self._ranked_source = source
        self._ranked_at = now
        # learn
        try:
            self.ai.learn_from_ranking(ranked, market=(get_cached_payload() or {}).get("market"))
        except Exception:
            pass
        summary = build_market_summary(ranked)
        logger.info("ranked source=%s n=%s power=%s best=%s top=%.1f worst=%.1f", source, len(ranked), summary.market_power, summary.best_group, ranked[0].final_score if ranked else -1, ranked[-1].final_score if ranked else -1)
        return ranked


def _parse_number(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.replace(",", "").replace("٬", "").replace("میلیون", "e6").replace("میلیارد", "e9").strip()
    t = re.sub(r"[^0-9eE.+-]", "", t)
    try:
        return float(t)
    except Exception:
        return None
