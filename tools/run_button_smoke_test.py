#!/usr/bin/env python3
"""تست دکمه‌ها: منو + شبیه‌سازی callback + ارسال واقعی به کانال."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.telegram.client import TelegramService
from services.telegram.keyboards import main_menu_keyboard
from services.telegram_bot import SandoghchiBot


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    tg = TelegramService()
    chat_id = tg.chat_id
    print("chat_id_set", bool(chat_id))
    me = tg.get_me()
    print("bot", (me.get("result") or {}).get("username"))
    print("deleteWebhook", tg.api("deleteWebhook", {"drop_pending_updates": False}).get("ok"))

    bot = SandoghchiBot(telegram=tg, warm_cache=True)
    info = bot.setup()
    print("setup", info.get("delete_webhook"), "source", bot._ranked_source, "n", len(bot._ranked_cache))

    ok = tg.send_message(
        "✅ ربات دکمه‌ای آماده است\n"
        f"منبع داده: {bot._ranked_source or '-'}\n\n"
        "الان دکمه‌ها را بزنید.\n"
        "برای تجربه بهتر به @boursepilotbot پیام /start بدهید.",
        reply_markup=main_menu_keyboard(),
    )
    print("menu_sent", ok)

    for cmd in ("market", "top", "gold", "worst"):
        print("sim", cmd)
        bot._run_command(chat_id, cmd)
        time.sleep(0.4)

    print("SMOKE_DONE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
