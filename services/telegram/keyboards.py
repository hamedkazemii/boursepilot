"""کیبوردهای بتا — منوی تعاملی کامل + دکمه‌های اختصاصی."""

from __future__ import annotations

from typing import Any


def main_menu_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "📊 تحلیل امروز", "callback_data": "cmd:today"},
                {"text": "🏆 برترین‌ها", "callback_data": "cmd:top"},
            ],
            [
                {"text": "⚠️ ضعیف‌ترین‌ها", "callback_data": "cmd:worst"},
                {"text": "🌐 وضعیت بازار", "callback_data": "cmd:market"},
            ],
            [
                {"text": "🔍 جستجوی صندوق", "callback_data": "cmd:search_prompt"},
                {"text": "📁 سبد من", "callback_data": "cmd:portfolio"},
            ],
            [
                {"text": "⭐ لیست پیگیری", "callback_data": "cmd:watch"},
                {"text": "🤖 مشاور هوشمند", "callback_data": "cmd:ask"},
            ],
            [
                {"text": "⚖️ مقایسه صندوق‌ها (به‌زودی)", "callback_data": "cmd:coming_soon"},
            ],
            [
                {"text": "ℹ️ راهنما", "callback_data": "cmd:help"},
            ],
        ]
    }


def onboarding_start_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🚀 شروع", "callback_data": "cmd:onboarding_start"},
                {"text": "⏭ بعداً", "callback_data": "cmd:menu"},
            ]
        ]
    }


def risk_profile_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🟢 کم‌ریسک", "callback_data": "profile:risk:low"},
                {"text": "🟡 متوسط", "callback_data": "profile:risk:medium"},
            ],
            [
                {"text": "🔵 پرریسک", "callback_data": "profile:risk:high"},
            ],
        ]
    }


def horizon_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "🟢 کوتاه‌مدت (۳ ماه)", "callback_data": "profile:horizon:3"},
                {"text": "🟡 میان‌مدت (۶ ماه)", "callback_data": "profile:horizon:6"},
            ],
            [
                {"text": "🔵 بلندمدت (+۱۲ ماه)", "callback_data": "profile:horizon:12"},
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
                {"text": "⭐ واچ‌لیست", "callback_data": f"watch:{symbol}"},
            ],
            [
                {"text": "➕ به سبد", "callback_data": f"pfadd:{symbol}"},
                {"text": "⚖️ مقایسه", "callback_data": f"compare:{symbol}"},
            ],
            [
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ],
        ]
    }


def portfolio_actions_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "➕ افزودن صندوق", "callback_data": "cmd:pf_add_prompt"},
                {"text": "➖ حذف صندوق", "callback_data": "cmd:pf_del_prompt"},
            ],
            [
                {"text": "🔄 بروزرسانی سبد", "callback_data": "cmd:portfolio"},
                {"text": "🏠 منو", "callback_data": "cmd:menu"},
            ],
        ]
    }


def help_text() -> str:
    return (
        "📘 راهنمای صندوقچی (نسخه بتا)\n\n"
        "📊 گزارش و رنکینگ:\n"
        "• /today — تحلیل کامل امروز\n"
        "• /top — ۵ صندوق برتر\n"
        "• /worst — ۵ صندوق ضعیف\n"
        "• /market — خلاصه وضعیت بازار\n"
        "• /preopen — پیش‌گشایش\n"
        "• /gold /fixed /stock — فیلتر گروه\n"
        "• /fund <نماد> — تحلیل تک صندوق\n\n"
        "📁 پرتفوی و پیگیری:\n"
        "• /portfolio — وضعیت سبد شما\n"
        "• /pf_add <نماد> <تعداد> [قیمت]\n"
        "• /pf_del <نماد>\n"
        "• /watch <نماد> — اضافه به پیگیری\n"
        "• /watchlist — لیست پیگیری\n\n"
        "👤 پروفایل:\n"
        "• /profile — نمایش پروفایل\n"
        "• /risk low|medium|high\n"
        "• /capital <مبلغ> — سرمایه\n\n"
        "🤖 مشاور:\n"
        "• /ask یا چت آزاد — سوال بپرسید"
    )
