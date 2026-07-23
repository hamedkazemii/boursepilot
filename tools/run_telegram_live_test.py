#!/usr/bin/env python3
"""تست زنده تلگرام: منو + دکمه‌ها + گزارش هوشمند محدود."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# اگر chat_id خالی بود از کانال کشف‌شده استفاده کن
if not os.getenv("TELEGRAM_CHAT_ID", "").strip():
    os.environ["TELEGRAM_CHAT_ID"] = "-1004428894487"

from config import settings
from core.pipeline.daily_rank import DailyRankPipeline
from core.scoring.models import FactorScore, FundAssessment
from services.telegram.client import TelegramService
from services.telegram.keyboards import after_report_keyboard, help_text, main_menu_keyboard
from services.telegram.smart_report import build_smart_morning_messages
from services.telegram_publisher import TelegramPublisher


def assessments_from_payload(payload: dict) -> list[FundAssessment]:
    out: list[FundAssessment] = []
    for row in payload.get("rankings") or []:
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
    return out


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    tg = TelegramService()
    me = tg.get_me()
    if not me.get("ok"):
        print("BOT_FAIL", me)
        return 1
    bot_user = me["result"]
    print("bot", bot_user.get("username"), bot_user.get("id"))
    print("chat_id", tg.chat_id)
    print("brs", "yes" if settings.BRS_API_KEY else "no")

    # 1) منو با دکمه‌ها
    ok1 = tg.send_message(
        f"🧪 تست زنده {settings.PRODUCT_NAME}\nربات: @{bot_user.get('username')}\nمنوی دکمه‌ای:",
        reply_markup=main_menu_keyboard(),
    )
    print("menu_sent", ok1)
    time.sleep(0.5)

    ok_help = tg.send_message(help_text(), reply_markup=main_menu_keyboard())
    print("help_sent", ok_help)

    # 2) رنکینگ واقعی (limit برای سرعت)
    limit = int(os.getenv("LIVE_TEST_LIMIT", "40"))
    print("running pipeline limit=", limit)
    pipe = DailyRankPipeline(fetch_nav=False)
    result = pipe.run(limit=limit)
    ranked = assessments_from_payload(result["payload"])
    print("ranked", len(ranked), "top", ranked[0].symbol if ranked else None)

    # 3) گزارش هوشمند فشرده‌تر برای کانال (۳ برتر + ۲ ضعیف)
    msgs = build_smart_morning_messages(
        ranked,
        meta=result["payload"],
        top_n=3,
        worst_n=2,
    )
    # پیشوند تست
    msgs[0] = "🧪 " + msgs[0]
    ok_smart = tg.send_messages(msgs, reply_markup_last=after_report_keyboard())
    print("smart_sent", ok_smart, "messages", len(msgs))

    # 4) یک کارت صندوق نمونه
    if ranked:
        from services.telegram_publisher import format_fund_telegram
        from services.telegram.keyboards import fund_actions_keyboard

        card = format_fund_telegram(ranked[0])
        ok_card = tg.send_message(card, reply_markup=fund_actions_keyboard(ranked[0].symbol))
        print("fund_card_sent", ok_card, ranked[0].symbol)

    print("DONE", "all_ok" if (ok1 and ok_smart) else "partial")
    return 0 if (ok1 and ok_smart) else 1


if __name__ == "__main__":
    raise SystemExit(main())
