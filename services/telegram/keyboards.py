"""کیبوردهای اینلاین ربات صندوقچی."""

from __future__ import annotations

from typing import Any


def main_menu_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "📊 امروز", "callback_data": "cmd:today"},
                {"text": "🏆 برترین‌ها", "callback_data": "cmd:top"},
            ],
            [
                {"text": "⚠️ ضعیف‌ها", "callback_data": "cmd:worst"},
                {"text": "🌐 بازار", "callback_data": "cmd:market"},
            ],
            [
                {"text": "🥇 طلا", "callback_data": "cmd:gold"},
                {"text": "💵 درآمد ثابت", "callback_data": "cmd:fixed"},
                {"text": "📈 سهامی", "callback_data": "cmd:stock"},
            ],
            [
                {"text": "📁 پرتفوی من", "callback_data": "cmd:portfolio"},
                {"text": "👤 پروفایل", "callback_data": "cmd:profile"},
            ],
            [
                {"text": "🤖 سوال از مشاور", "callback_data": "cmd:ask"},
                {"text": "⭐ واچ‌لیست", "callback_data": "cmd:watch"},
            ],
            [
                {"text": "🔄 بروزرسانی", "callback_data": "cmd:refresh"},
                {"text": "ℹ️ راهنما", "callback_data": "cmd:help"},
            ],
        ]
    }


def after_report_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🏆 برتر", "callback_data": "cmd:top"},
                {"text": "⚠️ ضعیف", "callback_data": "cmd:worst"},
                {"text": "🌐 بازار", "callback_data": "cmd:market"},
            ],
            [
                {"text": "📁 پرتفوی", "callback_data": "cmd:portfolio"},
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ],
        ]
    }


def fund_actions_keyboard(symbol: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 بروزرسانی", "callback_data": f"fund:{symbol}"},
                {"text": "⭐ واچ", "callback_data": f"watch:{symbol}"},
            ],
            [
                {"text": "➕ به پرتفو", "callback_data": f"pfadd:{symbol}"},
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ],
        ]
    }


def help_text() -> str:
    return (
        "📘 راهنمای صندوقچی\n\n"
        "گزارش و رنکینگ:\n"
        "• /today — گزارش هوشمند (۵ برتر + ۵ ضعیف واقعی)\n"
        "• /top /worst /market /preopen\n"
        "• /gold /fixed /stock\n"
        "• /fund عیار\n\n"
        "پروفایل و پرتفو:\n"
        "• /profile — ساخت/نمایش پروفایل\n"
        "• /risk low|medium|high\n"
        "• /capital 50000000\n"
        "• /portfolio\n"
        "• /pf_add عیار 100 25000\n"
        "• /pf_del عیار\n"
        "• /watch عیار | /watchlist\n\n"
        "مشاور هوشمند:\n"
        "• /ask ۵۰ میلیون ریسک کم یک‌ساله\n"
        "• یا هر سوال متنی در چت خصوصی\n\n"
        "رتبه‌بندی بر اساس روند تاریخی + جایگاه نسبی بین همه صندوق‌هاست؛ نه فقط لحظه."
    )
