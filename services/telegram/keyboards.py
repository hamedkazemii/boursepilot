"""کیبوردهای اینلاین ربات صندوقچی."""

from __future__ import annotations

from typing import Any


def main_menu_keyboard() -> dict[str, Any]:
    """منوی اصلی با دکمه‌های اینلاین."""
    return {
        "inline_keyboard": [
            [
                {"text": "📊 امروز", "callback_data": "cmd:today"},
                {"text": "🏆 برترین‌ها", "callback_data": "cmd:top"},
            ],
            [
                {"text": "⚠️ ضعیف‌ها", "callback_data": "cmd:worst"},
                {"text": "🔔 پیش‌گشایش", "callback_data": "cmd:preopen"},
            ],
            [
                {"text": "🥇 طلا", "callback_data": "cmd:gold"},
                {"text": "💵 درآمد ثابت", "callback_data": "cmd:fixed"},
            ],
            [
                {"text": "📈 سهامی", "callback_data": "cmd:stock"},
                {"text": "⚡ اهرمی", "callback_data": "cmd:leverage"},
            ],
            [
                {"text": "🌐 وضعیت بازار", "callback_data": "cmd:market"},
                {"text": "🔄 بروزرسانی", "callback_data": "cmd:refresh"},
            ],
            [
                {"text": "ℹ️ راهنما", "callback_data": "cmd:help"},
            ],
        ]
    }


def after_report_keyboard() -> dict[str, Any]:
    """دکمه‌های میانبر بعد از هر گزارش."""
    return {
        "inline_keyboard": [
            [
                {"text": "🏆 برتر", "callback_data": "cmd:top"},
                {"text": "⚠️ ضعیف", "callback_data": "cmd:worst"},
                {"text": "🌐 بازار", "callback_data": "cmd:market"},
            ],
            [
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ],
        ]
    }


def fund_actions_keyboard(symbol: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 بروزرسانی صندوق", "callback_data": f"fund:{symbol}"},
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ]
        ]
    }


def help_text() -> str:
    return (
        "📘 راهنمای صندوقچی\n"
        "\n"
        "دکمه‌ها یا دستورها:\n"
        "• /today — گزارش هوشمند امروز\n"
        "• /top — ۵ صندوق برتر\n"
        "• /worst — ۵ صندوق ضعیف\n"
        "• /market — وضعیت بازار\n"
        "• /preopen — پیش‌گشایش\n"
        "• /gold /fixed /stock — فیلتر گروه\n"
        "• /fund عیار — جزئیات یک صندوق\n"
        "• /rank — رنکینگ فشرده\n"
        "• /menu — نمایش دکمه‌ها\n"
        "\n"
        "از دکمه‌های زیر پیام هم می‌توانید استفاده کنید."
    )
