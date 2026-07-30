#!/usr/bin/env python3
"""ارسال فوری منوی دکمه‌ای به کانال."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.telegram.client import TelegramService
from services.telegram.keyboards import main_menu_keyboard


def main() -> int:
    tg = TelegramService()
    me = tg.get_me()
    uname = (me.get("result") or {}).get("username")
    tg.api("deleteWebhook", {"drop_pending_updates": False})
    ok = tg.send_message(
        f"✅ @{uname} آنلاین است\n\n"
        "دکمه‌ها را بزنید — الان باید جواب بدهد.\n"
        "اگر در کانال بودید و جواب خصوصی می‌خواهید، یک‌بار به ربات /start بدهید.",
        reply_markup=main_menu_keyboard(),
    )
    print("sent", ok, "bot", uname, "chat_set", bool(tg.chat_id))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
