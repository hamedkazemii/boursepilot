"""سرویس ارسال پیام تلگرام برای صندوقچی (کانال/چت)."""

from __future__ import annotations

import logging
import time
from typing import Iterable, Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# محدودیت تلگرام برای sendMessage
TELEGRAM_MAX_LEN = 4096


class TelegramService:
    """ارسال پیام با chunk و خطایابی."""

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

    def send_message(
        self,
        message: str,
        *,
        parse_mode: Optional[str] = None,
        disable_preview: bool = True,
        chat_id: Optional[str] = None,
    ) -> bool:
        """ارسال یک پیام (در صورت بلندی، چند تکه)."""
        if not message or not str(message).strip():
            logger.warning("empty telegram message skipped")
            return False

        if not self.configured and not (chat_id and self.bot_token):
            logger.warning("Telegram is not configured; printing message instead")
            print(message)
            return False

        target = (chat_id or self.chat_id).strip()
        ok_all = True
        for chunk in chunk_text(str(message), TELEGRAM_MAX_LEN):
            ok = self._send_one(
                chunk,
                chat_id=target,
                parse_mode=parse_mode,
                disable_preview=disable_preview,
            )
            ok_all = ok_all and ok
            # فاصله کوتاه برای rate limit کانال
            time.sleep(0.35)
        return ok_all

    def send_messages(self, messages: Iterable[str], **kwargs) -> bool:
        ok_all = True
        for msg in messages:
            ok_all = self.send_message(msg, **kwargs) and ok_all
        return ok_all

    def _send_one(
        self,
        text: str,
        *,
        chat_id: str,
        parse_mode: Optional[str],
        disable_preview: bool,
    ) -> bool:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload: dict = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.error("telegram request failed: %s", exc)
            return False

        if response.ok:
            return True

        # اگر Markdown خراب بود، بدون parse_mode دوباره بفرست
        if parse_mode and response.status_code == 400:
            logger.warning("telegram parse_mode failed; retry plain text")
            payload.pop("parse_mode", None)
            try:
                response = self.session.post(url, json=payload, timeout=self.timeout)
                if response.ok:
                    return True
            except requests.RequestException as exc:
                logger.error("telegram retry failed: %s", exc)
                return False

        logger.error(
            "telegram send failed status=%s body=%s",
            response.status_code,
            (response.text or "")[:300],
        )
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
        # +1 for newline when joined
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

        # اگر یک خط خودش خیلی بلند بود
        while current and current_len > max_len and len(current) == 1:
            long_line = current[0]
            chunks.append(long_line[:max_len])
            rest = long_line[max_len:]
            current = [rest] if rest else []
            current_len = len(rest)

    if current:
        chunks.append("\n".join(current))
    return chunks or [text[:max_len]]
