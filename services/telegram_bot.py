"""ربات صندوقچی — بازطراحی بر اساس سند هویت برند.

User = Hero, Sandoghchi = Guide | AI = Decision Assistant | DATA → ANALYSIS → INSIGHT
Iran Market First | Trust First | Explainability First | No Hype
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from config import settings
from core.ai.advisor import AIAdvisor
from core.analytics.market_summary import build_market_summary
from core.classification.fund_type import classify_fund_type
from core.database.connection import get_database
from core.market.hours import current_session, MarketSession, SessionName
from core.market.taxonomy import FundCategory, classify_fund_category as categorize_fund, get_category_config
from core.pipeline.daily_analysis import DailyAnalysisPipeline
from core.scoring.models import FundAssessment
from core.scoring.score_engine import ScoreEngine
from services.discovery.fund_catalog import FundCatalogService
from services.portfolio.service import PortfolioService
from services.providers.exceptions import ProviderError
from services.providers.factory import get_market_data_provider
from services.snapshot.store import SnapshotStore
from services.telegram import TelegramService
from services.telegram.brand_messaging import (
    build_brand_message,
    format_ai_advice_brand,
    format_category_report_brand,
    format_fund_card_brand,
    format_fund_deepdive_brand,
    format_help_brand,
    format_home_brand,
    format_market_now_brand,
    format_portfolio_brand,
    format_profile_brand,
    format_today_analysis,
    format_welcome_brand,
)
from services.telegram.keyboards import (
    after_report_keyboard,
    cancel_only_keyboard,
    category_selector_keyboard,
    confirm_cancel_keyboard,
    confirm_delete_keyboard,
    fund_actions_keyboard,
    help_text,
    main_menu_keyboard,
    pf_add_select_keyboard,
    pf_del_prompt_keyboard,
    pf_edit_action_keyboard,
    pf_edit_prompt_keyboard,
    portfolio_actions_keyboard,
    profile_keyboard,
)
from services.telegram.rank_loader import get_cached_payload, load_rankings

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
            if getattr(self.provider, "name", "") == "demo":
                logger.warning("provider in DEMO mode — no live market data")
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
        self._awaiting_fund_search: set[str] = set()
        self._pf_wizard: dict[str, dict[str, Any]] = {}  # uid -> {step, symbol, qty, price, date}
        self._onboarding_state: dict[str, int] = {}  # user_id -> step_index
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
        # free text - state machine priority
        uid = str(user.get("id") or chat_id)
        # 1. Portfolio wizard (highest priority)
        if uid in self._pf_wizard:
            self._handle_pf_wizard(chat_id, text, uid, user)
            return
        # 2. Onboarding
        if uid in self._onboarding_state:
            # onboarding steps don't have numeric input in current flow
            return
        # 3. AI advisor awaiting question
        if uid in self._awaiting_ask:
            self._awaiting_ask.discard(uid)
            self._cmd_ask(chat_id, text, user=user)
            return
        # 4. Fund analysis flow (only when explicitly requested)
        if uid in self._awaiting_fund_search:
            self._handle_fund_analysis_input(chat_id, text, uid)
            return
        # 5. No active flow - ignore free text, show main menu
        if chat.get("type") == "private":
            self._reply(chat_id, "از منوی اصلی یکی رو انتخاب کن:", reply_markup=main_menu_keyboard())
            return

    def _handle_pf_wizard(self, chat_id: str, text: str, uid: str, user: Optional[dict] = None) -> None:
        """راهنمای گام‌به‌گام افزودن/ویرایش صندوق در سبد — هر مرحله فقط یک سؤال."""
        w = self._pf_wizard.get(uid)
        if not w:
            return
        step = w.get("step")
        mode = w.get("mode", "add")
        sym = w.get("symbol", "")
        if step == "symbol":
            # Search for fund by name/symbol within wizard context
            self._handle_wizard_fund_search(chat_id, text, uid, w, user)
            return
        if step == "price":
            price = _parse_number(text)
            if price is None or price <= 0:
                self._reply(chat_id, "این مقدار رو نتونستم تشخیص بدم. قیمت خرید هر واحد رو به ریال بفرست:", reply_markup=cancel_only_keyboard())
                return
            w["price"] = price
            if mode == "fix":
                # fix mode: only price changes, qty stays same → straight to confirm
                w["step"] = "confirm"
                qty = w.get("qty", 0)
                lines = [
                    f"✏️ اصلاح اطلاعات\n━━━━━━━━━━━━━━━━━━━━━━\n",
                    f"صندوق: {sym}",
                    f"قیمت خرید جدید: {price:,.0f} ریال",
                    f"تعداد: {qty:g} واحد",
                    "\nاطلاعات درسته؟",
                ]
                kb = confirm_cancel_keyboard(f"pfwiz_confirm:{uid}")
                self._reply(chat_id, "\n".join(lines), reply_markup=kb)
                return
            w["step"] = "qty"
            self._reply(
                chat_id,
                f"قیمت {price:,.0f} ریال ثبت شد.\n\nچند واحد ازش خریدی؟",
                reply_markup=cancel_only_keyboard(),
            )
        elif step == "qty":
            qty = _parse_number(text)
            if qty is None or qty <= 0:
                self._reply(chat_id, "این مقدار رو نتونستم تشخیص بدم. تعداد واحد رو بفرست:", reply_markup=cancel_only_keyboard())
                return
            w["qty"] = qty
            w["step"] = "date"
            self._reply(
                chat_id,
                f"تعداد {qty:g} واحد ثبت شد.\n\nچه تاریخی خریدیش؟\nمثلاً ۱۴۰۵/۰۵/۱۹",
                reply_markup=cancel_only_keyboard(),
            )
        elif step == "date":
            w["date"] = text.strip()
            w["step"] = "current"
            self._reply(
                chat_id,
                "تاریخ ثبت شد.\n\nالان چند واحد از این صندوق داری؟",
                reply_markup=cancel_only_keyboard(),
            )
        elif step == "current":
            cur = _parse_number(text)
            if cur is None or cur < 0:
                self._reply(chat_id, "این مقدار رو نتونستم تشخیص بدم. تعداد فعلی رو بفرست:", reply_markup=cancel_only_keyboard())
                return
            w["current"] = cur
            w["step"] = "confirm"
            qty = w.get("qty", 0)
            price = w.get("price", 0)
            if mode == "sell":
                lines = [
                    f"📋 اطلاعات فروش\n━━━━━━━━━━━━━━━━━━━━━━\n",
                    f"صندوق: {sym}",
                    f"قیمت فروش: {price:,.0f} ریال",
                    f"تعداد فروش: {qty:g}",
                    f"تاریخ فروش: {w['date']}",
                    f"دارایی فعلی: {cur:g}",
                    "\nاطلاعات درسته؟",
                ]
            else:
                lines = [
                    f"📋 اطلاعات خرید\n━━━━━━━━━━━━━━━━━━━━━━\n",
                    f"صندوق: {sym}",
                    f"قیمت خرید: {price:,.0f} ریال",
                    f"تعداد خرید: {qty:g}",
                    f"تاریخ خرید: {w['date']}",
                    f"دارایی فعلی: {cur:g}",
                    "\nاطلاعات درسته؟",
                ]
            kb = confirm_cancel_keyboard(f"pfwiz_confirm:{uid}")
            self._reply(chat_id, "\n".join(lines), reply_markup=kb)
        else:
            self._pf_wizard.pop(uid, None)

    def _handle_pf_wizard_confirm(self, target: str, uid: str) -> None:
        """تأیید نهایی wizard و ثبت در سبد."""
        w = self._pf_wizard.pop(uid, None)
        if not w:
            self._reply(target, "داده‌ای برای تأیید نیست.", reply_markup=main_menu_keyboard())
            return
        sym = w.get("symbol", "")
        qty = w.get("qty", 0)
        price = w.get("price", 0)
        mode = w.get("mode", "add")
        if mode == "sell":
            # فروش: کاهش تعداد از سبد (حداقل به صفر نرسد)
            self.portfolio.remove_holding(uid, sym)
            self._reply(
                target,
                f"✅ {sym} فروخته شد ({qty:g} واحد @ {price:,.0f} ریال)\n"
                f"💰 ارزش فروش: {qty * price:,.0f} ریال\n"
                f"📅 {w.get('date', '')}",
                reply_markup=portfolio_actions_keyboard(),
            )
        else:
            self.portfolio.upsert_holding(uid, sym, quantity=qty, avg_cost=price)
            self._reply(
                target,
                f"✅ {sym} به سبد اضافه شد.\n"
                f"🔢 {qty:g} واحد @ {price:,.0f} ریال\n"
                f"📅 {w.get('date', '')}\n"
                f"💰 ارزش: {qty * price:,.0f} ریال",
                reply_markup=portfolio_actions_keyboard(),
            )

    def _handle_fund_analysis_input(self, chat_id: str, text: str, uid: str) -> None:
        """ورودی تحلیل صندوق - فقط exact match یا clarification، بدون silent fallback."""
        self._awaiting_fund_search.discard(uid)
        query = text.strip()
        if not query:
            self._reply(chat_id, "اسم یا نماد صندوق رو بفرست.", reply_markup=cancel_only_keyboard())
            self._awaiting_fund_search.add(uid)
            return

        ranked = self._get_ranked()
        matches = []
        # Exact symbol match first
        for a in ranked:
            if a.symbol == query:
                matches = [a]
                break
        # Exact name match
        if not matches:
            for a in ranked:
                if (a.name or "").strip() == query:
                    matches = [a]
                    break
        # Single partial match (unique)
        if not matches:
            partial = [a for a in ranked if query in a.symbol or query in (a.name or "")]
            if len(partial) == 1:
                matches = partial

        if len(matches) == 1:
            a = matches[0]
            self._reply(chat_id, self._cmd_fund(a.symbol), reply_markup=fund_actions_keyboard(a.symbol))
        elif len(matches) > 1:
            options = "\n".join([f"• {a.symbol} — {a.name}" for a in matches[:10]])
            self._reply(
                chat_id,
                f"چند تا صندوق پیدا شد که با «{query}» هم‌خونه:\n\n{options}\n\n"
                f"لطفاً نماد دقیق‌تر رو بفرست.",
                reply_markup=cancel_only_keyboard(),
            )
            self._awaiting_fund_search.add(uid)
        else:
            self._reply(
                chat_id,
                f"صندوقی با نام یا نماد «{query}» پیدا نکردم.\n\n"
                f"لطفاً نام یا نماد دقیق صندوق رو دوباره بفرست.",
                reply_markup=cancel_only_keyboard(),
            )
            self._awaiting_fund_search.add(uid)

    def _handle_wizard_fund_search(self, chat_id: str, text: str, uid: str, wizard: dict, user: Optional[dict] = None) -> None:
        """جستجوی صندوق در حین wizard - فقط exact match یا clarification."""
        catalog = self._get_fund_catalog()
        if not catalog:
            self._reply(chat_id, "داده صندوق‌ها در دسترس نیست. لطفاً بعداً تلاش کن.", reply_markup=cancel_only_keyboard())
            return

        query = text.strip()
        matches = []

        # Exact symbol match first
        for f in catalog:
            if f.get("symbol", "").lower() == query.lower():
                matches = [f]
                break

        # Exact name match
        if not matches:
            for f in catalog:
                if f.get("name", "").lower() == query.lower():
                    matches = [f]
                    break

        # Partial symbol/name match
        if not matches:
            for f in catalog:
                if query.lower() in f.get("symbol", "").lower() or query.lower() in f.get("name", "").lower():
                    matches.append(f)

        if len(matches) == 1:
            # Found exact match
            fund = matches[0]
            sym = fund.get("symbol", "")
            wizard["symbol"] = sym
            wizard["step"] = "price"
            self._reply(
                chat_id,
                f"عالیه 🌱\n\nصندوق «{fund.get('name', sym)}» رو پیدا کردم.\n\n"
                f"حالا بریم سراغ اطلاعات خرید.\n"
                f"قیمت خرید هر واحد رو به ریال برام بنویس.\n\n"
                f"مثال:\n125000",
                reply_markup=cancel_only_keyboard(),
            )
        elif len(matches) > 1:
            # Multiple matches - ask for clarification
            options = "\n".join([f"• {f.get('symbol', '')} — {f.get('name', '')}" for f in matches[:10]])
            self._reply(
                chat_id,
                f"چند تا صندوق پیدا شد که با «{query}» هم‌خونه:\n\n{options}\n\n"
                f"لطفاً نام یا نماد دقیق‌تر رو بفرست.",
                reply_markup=cancel_only_keyboard(),
            )
        else:
            # No match
            self._reply(
                chat_id,
                f"صندوقی با نام یا نماد «{query}» پیدا نکردم.\n\n"
                f"لطفاً نام یا نماد دقیق صندوق رو دوباره بفرست.",
                reply_markup=cancel_only_keyboard(),
            )

    def _get_fund_catalog(self) -> Optional[list[dict]]:
        """دریافت کاتالوگ صندوق‌ها از snapshot store (با fallback به ranked list)."""
        try:
            latest = self.store.load_json("fund_catalog")
            if latest and isinstance(latest, dict) and "funds" in latest and latest["funds"]:
                return latest["funds"]
        except Exception:
            pass
        # Fallback: use ranked assessments as catalog
        try:
            ranked = self._get_ranked()
            if ranked:
                return [{"symbol": a.symbol, "name": a.name or ""} for a in ranked]
        except Exception:
            pass
        return None

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
                cmd = data.split(":", 1)[1]
                if cmd == "fund_search":
                    self._reply(target, "حتماً.\nاسم یا نماد صندوقی که می‌خوای بررسی کنم رو برام بفرست.", reply_markup=cancel_only_keyboard())
                    self._awaiting_fund_search.add(user_id or target)
                else:
                    self._run_command(target, cmd, args="", user=user)
            elif data.startswith("fund:"):
                sym = data.split(":", 1)[1]
                self._reply(target, self._cmd_fund(sym), reply_markup=fund_actions_keyboard(sym))
            elif data.startswith("fund_history:"):
                sym = data.split(":", 1)[1]
                self._reply(target, self._cmd_fund_history(sym), reply_markup=fund_actions_keyboard(sym))
            elif data.startswith("fund_compare:"):
                sym = data.split(":", 1)[1]
                self._reply(target, self._cmd_fund_compare(sym), reply_markup=fund_actions_keyboard(sym))
            elif data.startswith("fund_backtest:"):
                sym = data.split(":", 1)[1]
                self._reply(target, self._cmd_fund_backtest(sym), reply_markup=fund_actions_keyboard(sym))
            elif data.startswith("watch:"):
                sym = data.split(":", 1)[1]
                self.portfolio.add_watch(user_id or target, sym)
                self._reply(target, f"⭐ {sym} به واچ‌لیست اضافه شد.", reply_markup=after_report_keyboard())
            elif data.startswith("pfadd:"):
                sym = data.split(":", 1)[1]
                uid_w = user_id or target
                self._pf_wizard[uid_w] = {"step": "price", "symbol": sym, "qty": None, "price": None, "date": None, "current": None, "mode": "add"}
                self._reply(
                    target,
                    f"حتماً، با هم به سبدت اضافه‌اش می‌کنیم.\n"
                    f"صندوق {sym} رو پیدا کردم.\n\n"
                    f"قیمت خرید هر واحد رو به ریال بهم بگو.",
                    reply_markup=cancel_only_keyboard(),
                )
            elif data.startswith("pfdel:"):
                sym = data.split(":", 1)[1]
                self._reply(target, f"مطمئنی {sym} رو از سبدت حذف کنیم؟", reply_markup=confirm_delete_keyboard(sym))
            elif data.startswith("pfdel_confirm:"):
                sym = data.split(":", 1)[1]
                self.portfolio.remove_holding(user_id or target, sym)
                self._reply(target, f"✅ {sym} از سبد حذف شد.", reply_markup=portfolio_actions_keyboard())
            elif data == "cmd:pf_add_prompt":
                # Show top funds from ranked list as inline buttons
                ranked = self._get_ranked()
                symbols = [a.symbol for a in ranked[:5]]
                uid_w = user_id or target
                self._pf_wizard[uid_w] = {"step": "symbol", "symbol": "", "qty": None, "price": None, "date": None, "current": None, "mode": "add"}
                if symbols:
                    self._reply(target, "حتماً. اول اسم یا نماد صندوق رو بفرست، یا یکی از برترین‌های امروز رو انتخاب کن:", reply_markup=pf_add_select_keyboard(symbols))
                else:
                    self._reply(target, "حتماً. اول اسم یا نماد صندوق رو بفرست.", reply_markup=cancel_only_keyboard())
            elif data == "cmd:pf_del_prompt":
                pf = self.portfolio.get_portfolio(user_id or target)
                symbols = [item["symbol"] for item in pf["items"]]
                if not symbols:
                    self._reply(target, "سبد تو خالیه.", reply_markup=portfolio_actions_keyboard())
                else:
                    self._reply(target, "باشه. کدوم صندوق رو می‌خوای از سبدت حذف کنیم؟", reply_markup=pf_del_prompt_keyboard(symbols))
            elif data == "cmd:pf_edit_prompt":
                pf = self.portfolio.get_portfolio(user_id or target)
                symbols = [item["symbol"] for item in pf["items"]]
                if not symbols:
                    self._reply(target, "سبد تو خالیه.", reply_markup=portfolio_actions_keyboard())
                else:
                    self._reply(target, "حتماً. اول بگو کدوم صندوق رو می‌خوای تغییر بدی.", reply_markup=pf_edit_prompt_keyboard(symbols))
            elif data.startswith("pfedit:"):
                sym = data.split(":", 1)[1]
                self._reply(target, f"ویرایش {sym} — انتخاب کنید:", reply_markup=pf_edit_action_keyboard(sym))
            elif data.startswith("pfedit_buy:"):
                sym = data.split(":", 1)[1]
                uid_w = user_id or target
                self._pf_wizard[uid_w] = {"step": "price", "symbol": sym, "qty": None, "price": None, "date": None, "current": None, "mode": "buy_more"}
                self._reply(target, f"📈 خرید بیشتر {sym}\n\nقیمت خرید هر واحد رو به ریال بهم بگو.", reply_markup=cancel_only_keyboard())
            elif data.startswith("pfedit_sell:"):
                sym = data.split(":", 1)[1]
                uid_w = user_id or target
                self._pf_wizard[uid_w] = {"step": "price", "symbol": sym, "qty": None, "price": None, "date": None, "current": None, "mode": "sell"}
                self._reply(target, f"📉 فروش بخشی {sym}\n\nقیمت فروش هر واحد رو به ریال بهم بگو.", reply_markup=cancel_only_keyboard())
            elif data.startswith("pfedit_fix:"):
                sym = data.split(":", 1)[1]
                pf = self.portfolio.get_portfolio(user_id or target)
                item = next((i for i in pf["items"] if i["symbol"] == sym), None)
                if not item:
                    self._reply(target, f"صندوق {sym} در سبد پیدا نشد.", reply_markup=portfolio_actions_keyboard())
                    return
                uid_w = user_id or target
                # Pre-fill with current values
                self._pf_wizard[uid_w] = {
                    "step": "price",
                    "symbol": sym,
                    "qty": float(item.get("quantity") or 0),
                    "price": None,
                    "date": None,
                    "current": None,
                    "mode": "fix"
                }
                self._reply(
                    target,
                    f"✏️ اصلاح اطلاعات {sym}\n\n"
                    f"تعداد فعلی: {item.get('quantity', 0):g} واحد\n"
                    f"قیمت خرید قبلی: {item.get('avg_cost', 0):,.0f} ریال\n\n"
                    f"قیمت خرید جدید هر واحد رو بفرست (یا همون قبلی رو تکرار کن):",
                    reply_markup=cancel_only_keyboard(),
                )
            elif data.startswith("pfwiz_confirm:"):
                wuid = data.split(":", 1)[1]
                self._handle_pf_wizard_confirm(target, wuid)
            elif data.startswith("pfwiz_cancel:"):
                wuid = data.split(":", 1)[1]
                self._pf_wizard.pop(wuid, None)
                self._reply(target, "انصراف دادیم. هر وقت خواستی می‌تونیم ادامه بدیم.", reply_markup=portfolio_actions_keyboard())
            elif data.startswith("cat_best:"):
                cat = data.split(":", 1)[1].replace("_", " ")
                meta = get_cached_payload()
                self._reply(target, self._cmd_category_best(cat, meta), reply_markup=category_selector_keyboard())
            elif data.startswith("cat_all:"):
                cat = data.split(":", 1)[1].replace("_", " ")
                self._reply(target, self._cmd_category_all(cat), reply_markup=category_selector_keyboard())
            elif data.startswith("cat_compare:"):
                cat = data.split(":", 1)[1].replace("_", " ")
                self._reply(target, self._cmd_category_compare(cat), reply_markup=category_selector_keyboard())
            elif data.startswith("onboard:"):
                self._handle_onboarding_callback(target, data, user_id or target, user)
            elif data == "cmd:onboarding_start":
                self._start_onboarding(target, user_id or target)
            elif data == "cmd:search_prompt":
                self._reply(target, "برای جستجو، نام یا بخشی از نماد صندوق را بفرستید (مثال: عیار)", reply_markup=main_menu_keyboard())
            elif data == "cmd:coming_soon":
                self._reply(target, "این قابلیت در نسخه‌های آینده اضافه خواهد شد.", reply_markup=main_menu_keyboard())
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
            if cmd in {"start", "menu", "home"}:
                # Reset all conversation state — /start همیشه حالت را پاک می‌کند
                self._pf_wizard.pop(uid, None)
                self._awaiting_fund_search.discard(uid)
                self._awaiting_ask.discard(uid)
                self._onboarding_state.pop(uid, None)
                
                self.portfolio.ensure_user(uid, username=user.get("username") or "", first_name=user.get("first_name") or "")
                welcome = format_welcome_brand()
                self._reply(chat_id, welcome, reply_markup=main_menu_keyboard())
            elif cmd == "help":
                self._reply(chat_id, help_text(), reply_markup=main_menu_keyboard())
            elif cmd == "morning_brief":
                self._send_morning_brief(chat_id)
            elif cmd == "today_top":
                self._send_today_top(chat_id)
            elif cmd == "today_worst":
                self._send_today_worst(chat_id)
            elif cmd == "today_analysis":
                self._send_today_analysis(chat_id)
            elif cmd == "market_now":
                self._send_market_now(chat_id)
            elif cmd == "my_portfolio":
                self._send_my_portfolio(chat_id, uid)
            elif cmd == "pf_risk":
                self._send_my_portfolio(chat_id, uid)
            elif cmd == "fund_search":
                self._reply(chat_id, "حتماً.\nاسم یا نماد صندوقی که می‌خوای بررسی کنم رو برام بفرست.", reply_markup=cancel_only_keyboard())
                self._awaiting_fund_search.add(uid)
            elif cmd == "category_best":
                self._send_category_best(chat_id)
            elif cmd == "group":
                if not args:
                    self._reply(chat_id, "مثال: /group طلا", reply_markup=main_menu_keyboard())
                    return
                self._send_group(chat_id, args.strip())
            elif cmd == "my_watchlist":
                items = self.portfolio.list_watch(uid)
                text = "⭐ پیگیری‌های شما:\n" + ("\n".join(f"• {x}" for x in items) if items else "خالی")
                self._reply(chat_id, text, reply_markup=after_report_keyboard())
            elif cmd == "pf_add_prompt":
                ranked = self._get_ranked()
                symbols = [a.symbol for a in ranked[:5]]
                self._pf_wizard[uid] = {"step": "symbol", "symbol": "", "qty": None, "price": None, "date": None, "current": None, "mode": "add"}
                if symbols:
                    self._reply(chat_id, "حتماً. اول اسم یا نماد صندوق رو بفرست، یا یکی از برترین‌های امروز رو انتخاب کن:", reply_markup=pf_add_select_keyboard(symbols))
                else:
                    self._reply(chat_id, "حتماً. اول اسم یا نماد صندوق رو بفرست.", reply_markup=cancel_only_keyboard())
            elif cmd == "pf_del_prompt":
                pf = self.portfolio.get_portfolio(uid)
                symbols = [item["symbol"] for item in pf["items"]]
                if not symbols:
                    self._reply(chat_id, "سبد تو خالیه.", reply_markup=portfolio_actions_keyboard())
                else:
                    self._reply(chat_id, "باشه. کدوم صندوق رو می‌خوای از سبدت حذف کنیم؟", reply_markup=pf_del_prompt_keyboard(symbols))
            elif cmd == "pf_edit_prompt":
                pf = self.portfolio.get_portfolio(uid)
                symbols = [item["symbol"] for item in pf["items"]]
                if not symbols:
                    self._reply(chat_id, "سبد تو خالیه.", reply_markup=portfolio_actions_keyboard())
                else:
                    self._reply(chat_id, "حتماً. اول بگو کدوم صندوق رو می‌خوای تغییر بدی.", reply_markup=pf_edit_prompt_keyboard(symbols))
            elif cmd == "ask":
                if not args:
                    self._awaiting_ask.add(uid)
                    self._reply(chat_id, "سوال خود را بفرستید.\nمثال: ۵۰ میلیون ریسک کم یک‌ساله")
                    return
                self._cmd_ask(chat_id, args, user=user)
            elif cmd == "my_profile":
                self._cmd_profile(chat_id, uid)
            elif cmd == "refresh":
                self._ranked_cache = []
                self._ranked_at = 0
                self._reply(chat_id, "در حال بروزرسانی…")
                self._get_ranked(force=True)
                self._send_morning_brief(chat_id)
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
                self._send_my_portfolio(chat_id, uid)
            elif cmd == "pf_add":
                self._pf_wizard[uid] = {"step": "price", "symbol": args, "qty": None, "price": None, "date": None, "current": None, "mode": "add"}
                self._reply(chat_id, "حتماً، با هم به سبدت اضافه‌اش می‌کنیم.\nصندوق " + args + " رو پیدا کردم.\n\nقیمت خرید هر واحد رو به ریال بگو.", reply_markup=cancel_only_keyboard())
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
            elif cmd == "home":
                self._send_home(chat_id, uid)
            else:
                self._reply(chat_id, "این درخواست را متوجه نشدم. 🤔\n\nمی‌توانید از گزینه‌های زیر استفاده کنید:", reply_markup=main_menu_keyboard())
        except Exception as exc:  # noqa: BLE001
            logger.exception("cmd failed: %s", exc)
            self._reply(chat_id, f"خطا: {exc}", reply_markup=main_menu_keyboard())

    # ---- sends ----
    def _send_home(self, chat_id: str, uid: str) -> None:
        """نمایش صفحه اصلی (Home)."""
        ranked = self._get_ranked()
        meta = get_cached_payload()
        u = self.portfolio.ensure_user(uid)
        text = format_home_brand(ranked, meta, user_profile=u)
        self._reply(chat_id, text, reply_markup=main_menu_keyboard())

    def _send_morning_brief(self, chat_id: str) -> None:
        """گزارش صبحانه کامل بازار (۰۸:۵۰)."""
        self._reply(chat_id, "⏳ گزارش صبحانه بازار در حال تهیه…")
        ranked = self._get_ranked()
        meta = get_cached_payload()
        text = format_market_now_brand(ranked, meta)
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_today_top(self, chat_id: str) -> None:
        """برترین‌های امروز با پیام‌سازی برند."""
        ranked = self._get_ranked()
        top_n = min(5, len(ranked))
        messages = []
        for a in ranked[:top_n]:
            messages.append(format_fund_card_brand(a))
        if messages:
            self.telegram.send_messages(messages, chat_id=chat_id, reply_markup_last=after_report_keyboard())
        else:
            self._reply(chat_id, "داده‌ای برای نمایش وجود ندارد", reply_markup=after_report_keyboard())

    def _send_today_worst(self, chat_id: str) -> None:
        """ضعیف‌ترین‌های امروز."""
        ranked = self._get_ranked()
        worst = list(reversed(ranked[-5:])) if len(ranked) >= 5 else list(reversed(ranked))
        messages = []
        for a in worst:
            messages.append(format_fund_card_brand(a))
        if messages:
            self.telegram.send_messages(messages, chat_id=chat_id, reply_markup_last=after_report_keyboard())
        else:
            self._reply(chat_id, "داده‌ای برای نمایش وجود ندارد", reply_markup=after_report_keyboard())

    def _send_market_now(self, chat_id: str) -> None:
        """تحلیل لحظه‌ای بازار."""
        ranked = self._get_ranked()
        meta = get_cached_payload()
        session = current_session()
        text = format_market_now_brand(ranked, meta)
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_today_analysis(self, chat_id: str) -> None:
        """تحلیل امروز: روند بازار + صندوق‌های پتانسیل بالا/ضعیف."""
        ranked = self._get_ranked()
        meta = get_cached_payload()
        session = current_session()
        # Today's analysis: combine current market snapshot + yesterday's comparison
        text = format_today_analysis(ranked, meta, session=session)
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

    def _send_my_portfolio(self, chat_id: str, uid: str) -> None:
        """تحلیل سبد کاربر."""
        ranked = self._get_ranked()
        prices = {a.symbol: float(a.last_price or a.close_price or 0) for a in ranked if a.last_price or a.close_price}
        pf = self.portfolio.get_portfolio(uid)
        u = self.portfolio.ensure_user(uid)
        text = format_portfolio_brand(pf["items"], prices, u, ranked)
        self._reply(chat_id, text, reply_markup=portfolio_actions_keyboard())

    def _send_category_best(self, chat_id: str) -> None:
        """بهترین هر دسته‌بندی."""
        ranked = self._get_ranked()
        meta = get_cached_payload()
        # Group by category
        categories = ["طلا", "درآمد ثابت", "سهامی", "اهرم", "مختلط"]
        messages = []
        for cat in categories:
            cat_ranked = [a for a in ranked if cat in (a.fund_type or "")]
            if cat_ranked:
                msg = format_category_report_brand(cat, cat_ranked, meta)
                messages.append(msg)
        if messages:
            self.telegram.send_messages(messages, chat_id=chat_id, reply_markup_last=after_report_keyboard())
        else:
            self._reply(chat_id, "داده دسته‌بندی وجود ندارد", reply_markup=after_report_keyboard())

    def _send_group(self, chat_id: str, fund_type: str) -> None:
        """تحلیل یک گروه خاص."""
        ranked = [a for a in self._get_ranked() if fund_type in (a.fund_type or "")]
        meta = get_cached_payload()
        if not ranked:
            self._reply(chat_id, f"گروه {fund_type} یافت نشد", reply_markup=main_menu_keyboard())
            return
        text = format_category_report_brand(fund_type, ranked, meta)
        keyboard = category_selector_keyboard()
        self._reply(chat_id, text, reply_markup=keyboard)

    def _cmd_category_best(self, category: str, meta: dict) -> str:
        ranked = self._get_ranked()
        cat_ranked = [a for a in ranked if category in (a.fund_type or "")]
        if not cat_ranked:
            return f"داده برای دسته {category} وجود ندارد"
        return format_category_report_brand(category, cat_ranked, meta)

    def _cmd_category_all(self, category: str) -> str:
        ranked = self._get_ranked()
        cat_ranked = [a for a in ranked if category in (a.fund_type or "")]
        if not cat_ranked:
            return f"داده برای دسته {category} وجود ندارد"
        lines = [f"📊 همه صندوق‌های {category} (n={len(cat_ranked)})"]
        for a in cat_ranked[:10]:
            lines.append(f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
        if len(cat_ranked) > 10:
            lines.append(f"... و {len(cat_ranked) - 10} صندوق دیگر")
        return "\n".join(lines)

    def _cmd_category_compare(self, category: str) -> str:
        ranked = self._get_ranked()
        cat_ranked = [a for a in ranked if category in (a.fund_type or "")]
        if len(cat_ranked) < 2:
            return f"برای مقایسه حداقل ۲ صندوق در دسته {category} نیاز است"
        lines = [f"⚖️ مقایسه درونی {category}"]
        for a in cat_ranked[:5]:
            lines.append(f"{a.symbol}: امتیاز {a.final_score:.1f} | {a.recommendation_label}")
        return "\n".join(lines)

    def _cmd_fund(self, symbol: str) -> str:
        """تحلیل عمیق تک صندوق (Layer 1/2/3)."""
        symbol = symbol.strip()
        ranked = self._get_ranked()
        # 1. Exact symbol match (highest priority)
        for a in ranked:
            if a.symbol == symbol:
                return format_fund_deepdive_brand(a)
        # 2. Exact name match
        for a in ranked:
            if (a.name or "").strip() == symbol:
                return format_fund_deepdive_brand(a)
        # 3. Partial symbol match (unique only)
        partial = [a for a in ranked if symbol in a.symbol]
        if len(partial) == 1:
            return format_fund_deepdive_brand(partial[0])
        # 4. Partial name match (unique only)
        partial = [a for a in ranked if symbol in (a.name or "")]
        if len(partial) == 1:
            return format_fund_deepdive_brand(partial[0])
        if self.provider:
            try:
                q = self.provider.get_symbol(symbol)
                nav = None
                try:
                    nav = self.provider.get_nav(symbol)
                except ProviderError:
                    pass
                assessment = self.engine.assess(q, nav=nav)
                return format_fund_deepdive_brand(assessment)
            except Exception as exc:  # noqa: BLE001
                return f"خطا: {exc}"
        return f"نماد {symbol} پیدا نشد"

    def _cmd_fund_history(self, symbol: str) -> str:
        """تاریخچه تحلیلی صندوق."""
        ranked = self._get_ranked()
        for a in ranked:
            if a.symbol == symbol or symbol in a.symbol or symbol in (a.name or ""):
                if a.advanced_metrics:
                    history = a.advanced_metrics.get("history_summary", {})
                    if history:
                        lines = [f"📜 تاریخچه تحلیلی {symbol}"]
                        for k, v in history.items():
                            lines.append(f"• {k}: {v}")
                        return "\n".join(lines)
                return f"تاریخچه تحلیلی برای {symbol} موجود نیست (حداقل ۳۰ روز داده لازم است)"
        return f"نماد {symbol} پیدا نشد"

    def _cmd_fund_compare(self, symbol: str) -> str:
        """مقایسه با هم‌گروه‌ها."""
        ranked = self._get_ranked()
        target = None
        for a in ranked:
            if a.symbol == symbol or symbol in a.symbol or symbol in (a.name or ""):
                target = a
                break
        if not target:
            return f"نماد {symbol} پیدا نشد"
        cat_ranked = [a for a in ranked if target.fund_type and target.fund_type in (a.fund_type or "")]
        if len(cat_ranked) < 2:
            return "هم‌گروه کافی برای مقایسه وجود ندارد"
        lines = [f"⚖️ مقایسه {target.symbol} با هم‌گروه ({target.fund_type})"]
        for a in cat_ranked[:5]:
            diff = a.final_score - target.final_score
            lines.append(f"{a.symbol}: {a.final_score:.1f} ({diff:+.1f}) | {a.recommendation_label}")
        return "\n".join(lines)

    def _cmd_fund_backtest(self, symbol: str) -> str:
        """بک‌تست استراتژی برای صندوق."""
        ranked = self._get_ranked()
        for a in ranked:
            if a.symbol == symbol or symbol in a.symbol or symbol in (a.name or ""):
                if a.advanced_metrics:
                    bt = a.advanced_metrics.get("backtest", {})
                    if bt:
                        lines = [f"📈 بک‌تست استراتژی {symbol}"]
                        for k, v in bt.items():
                            lines.append(f"• {k}: {v}")
                        return "\n".join(lines)
                return f"بک‌تست برای {symbol} موجود نیست (حداقل ۳۰ روز داده لازم است)"
        return f"نماد {symbol} پیدا نشد"

    def _cmd_profile(self, chat_id: str, uid: str) -> None:
        u = self.portfolio.ensure_user(uid)
        pf = self.portfolio.get_portfolio(uid)
        ranked = self._get_ranked()
        prices = {a.symbol: float(a.last_price or a.close_price or 0) for a in ranked if a.last_price or a.close_price}
        join_days = 1  # placeholder
        text = format_profile_brand(u, pf["items"], prices, join_days)
        self._reply(chat_id, text, reply_markup=profile_keyboard())

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
        text = format_ai_advice_brand(question, ans, u, pf)
        # store chat
        try:
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
        self._reply(chat_id, text, reply_markup=after_report_keyboard())

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

    # ---- onboarding helpers ----
    def _start_onboarding(self, chat_id: str, uid: str) -> None:
        self._onboarding_state[uid] = 0
        self._send_onboarding_step(chat_id, uid, 0)

    def _send_onboarding_step(self, chat_id: str, uid: str, step_index: int) -> None:
        from services.telegram.beta_onboarding import ONBOARDING_STEPS, onboarding_complete_message, onboarding_keyboard, onboarding_question, parse_onboarding_response
        if step_index >= len(ONBOARDING_STEPS):
            if uid in self._onboarding_state:
                del self._onboarding_state[uid]
            u = self.portfolio.ensure_user(uid)
            name = u.get("first_name") or "سرمایه‌گذار"
            self._reply(chat_id, onboarding_complete_message(name), reply_markup=main_menu_keyboard())
            return
        text = onboarding_question(step_index)
        keyboard = onboarding_keyboard(step_index)
        if keyboard:
            self._reply(chat_id, text, reply_markup=keyboard)
        else:
            self._reply(chat_id, text)

    def _handle_onboarding_callback(self, chat_id: str, data: str, uid: str, user: dict) -> None:
        from services.telegram.beta_onboarding import parse_onboarding_response
        parsed = parse_onboarding_response(data)
        if not parsed:
            return
        key, value = parsed
        if key == "experience":
            pass  # informational only for now
        elif key == "risk":
            self.portfolio.update_profile(uid, risk_profile=value)
        elif key == "horizon":
            self.portfolio.update_profile(uid, horizon_months=int(value))
        current = self._onboarding_state.get(uid, 0)
        self._onboarding_state[uid] = current + 1
        self._send_onboarding_step(chat_id, uid, current + 1)


def _parse_number(text: str) -> Optional[float]:
    if not text:
        return None
    t = text.replace(",", "").replace("٬", "").replace("میلیون", "e6").replace("میلیارد", "e9").strip()
    t = re.sub(r"[^0-9eE.+-]", "", t)
    try:
        return float(t)
    except Exception:
        return None