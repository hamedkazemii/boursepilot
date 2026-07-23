"""سرویس ارسال پیام تلگرام برای صندوقچی (کانال/چت)."""

from __future__ import annotations

import logging
import time
from typing import Any, Iterable, Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# محدودیت تلگرام برای sendMessage
TELEGRAM_MAX_LEN = 4096


class TelegramService:
    """ارسال پیام با chunk، reply_markup و خطایابی."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        timeout: float = 20.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.bot_token = (bot_token if bot_token is not None else settings.TELEGRAM_BOT_TOKEN).strip()
        self.chat_id = (chat_id if chat_id is not None else settings.TELEGRAM_CHAT_ID).strip()
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    @property
    def api_base(self) -> str:
        return f"https://api.telegram.org/bot{self.bot_token}"

    def api(
        self,
        method: str,
        payload: Optional[dict[str, Any]] = None,
        *,
        http: str = "post",
    ) -> dict[str, Any]:
        """فراخوانی خام Bot API — برای getUpdates / answerCallbackQuery و ..."""
        if not self.bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN تنظیم نشده است")
        url = f"{self.api_base}/{method}"
        try:
            if http.lower() == "get":
                response = self.session.get(url, params=payload or {}, timeout=self.timeout)
            else:
                response = self.session.post(url, json=payload or {}, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.error("telegram api %s failed: %s", method, exc)
            return {"ok": False, "description": str(exc)}
        try:
            data = response.json()
        except Exception:
            return {"ok": False, "description": response.text[:300], "status_code": response.status_code}
        if not response.ok and not data.get("ok"):
            logger.error("telegram api %s status=%s body=%s", method, response.status_code, str(data)[:300])
        return data

    def get_me(self) -> dict[str, Any]:
        return self.api("getMe", http="get")

    def send_message(
        self,
        message: str,
        *,
        parse_mode: Optional[str] = None,
        disable_preview: bool = True,
        chat_id: Optional[str] = None,
        reply_markup: Optional[dict[str, Any]] = None,
    ) -> bool:
        """ارسال یک پیام (در صورت بلندی، چند تکه). reply_markup فقط روی آخرین تکه."""
        if not message or not str(message).strip():
            logger.warning("empty telegram message skipped")
            return False

        if not self.bot_token:
            logger.warning("Telegram bot token missing; printing message instead")
            print(message)
            return False

        target = (chat_id or self.chat_id or "").strip()
        if not target:
            logger.warning("Telegram chat_id missing; printing message instead")
            print(message)
            return False

        chunks = chunk_text(str(message), TELEGRAM_MAX_LEN)
        ok_all = True
        for i, chunk in enumerate(chunks):
            is_last = i == len(chunks) - 1
            ok = self._send_one(
                chunk,
                chat_id=target,
                parse_mode=parse_mode,
                disable_preview=disable_preview,
                reply_markup=reply_markup if is_last else None,
            )
            ok_all = ok_all and ok
            time.sleep(0.35)
        return ok_all

    def send_messages(
        self,
        messages: Iterable[str],
        *,
        reply_markup_last: Optional[dict[str, Any]] = None,
        chat_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        disable_preview: bool = True,
    ) -> bool:
        msgs = [m for m in messages if m and str(m).strip()]
        if not msgs:
            return False
        ok_all = True
        for i, msg in enumerate(msgs):
            is_last = i == len(msgs) - 1
            ok_all = (
                self.send_message(
                    msg,
                    chat_id=chat_id,
                    parse_mode=parse_mode,
                    disable_preview=disable_preview,
                    reply_markup=reply_markup_last if is_last else None,
                )
                and ok_all
            )
        return ok_all

    def answer_callback_query(
        self,
        callback_query_id: str,
        text: str = "",
        show_alert: bool = False,
    ) -> bool:
        data = self.api(
            "answerCallbackQuery",
            {
                "callback_query_id": callback_query_id,
                "text": text[:200] if text else "",
                "show_alert": show_alert,
            },
        )
        if data.get("ok"):
            return True
        desc = str(data.get("description") or "")
        # queryهای منقضی‌شده هنگام downtime طبیعی‌اند
        if "query is too old" in desc or "query ID is invalid" in desc:
            logger.info("stale callback ignored: %s", desc)
            return False
        logger.error("answerCallbackQuery failed: %s", desc[:200])
        return False

    def _send_one(
        self,
        text: str,
        *,
        chat_id: str,
        parse_mode: Optional[str],
        disable_preview: bool,
        reply_markup: Optional[dict[str, Any]] = None,
    ) -> bool:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup

        data = self.api("sendMessage", payload)
        if data.get("ok"):
            return True

        # اگر Markdown خراب بود، بدون parse_mode دوباره بفرست
        if parse_mode and data.get("error_code") == 400:
            logger.warning("telegram parse_mode failed; retry plain text")
            payload.pop("parse_mode", None)
            data = self.api("sendMessage", payload)
            if data.get("ok"):
                return True

        logger.error("telegram send failed body=%s", str(data)[:300])
        return False


def chunk_text(text: str, max_len: int = TELEGRAM_MAX_LEN) -> list[str]:
    """تقسیم متن بلند روی مرز خط‌ها."""
    text = text.strip("\n")
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.split("\n"):
        add_len = len(line) + (1 if current else 0)
        if current and current_len + add_len > max_len:
            chunks.append("\n".join(current))
            current = [line]
            current_len = len(line)
        else:
            if current:
                current_len += 1 + len(line)
            else:
                current_len = len(line)
            current.append(line)

        while current and current_len > max_len and len(current) == 1:
            long_line = current[0]
            chunks.append(long_line[:max_len])
            rest = long_line[max_len:]
            current = [rest] if rest else []
            current_len = len(rest)

    if current:
        chunks.append("\n".join(current))
    return chunks or [text[:max_len]]
