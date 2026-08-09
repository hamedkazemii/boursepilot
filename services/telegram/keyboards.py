"""کیبوردهای برند-سازگار صندوقچی — طراحی مبتنی بر سند هویت برند."""

from __future__ import annotations

from typing import Any


def main_menu_keyboard() -> dict[str, Any]:
    """منوی اصلی ساده و کاربرپسند."""
    return {
        "inline_keyboard": [
            [
                {"text": "🌅 گزارش صبحانه (۰۸:۵۰)", "callback_data": "cmd:morning_brief"},
                {"text": "🏆 برترین‌های امروز", "callback_data": "cmd:today_top"},
            ],
            [
                {"text": "⚠️ ضعیف‌ترین‌های امروز", "callback_data": "cmd:today_worst"},
                {"text": "🔍 تحلیل تک صندوق", "callback_data": "cmd:fund_search"},
            ],
            [
                {"text": "🥇 بهترین هر دسته", "callback_data": "cmd:category_best"},
                {"text": "📁 تحلیل سبد من", "callback_data": "cmd:my_portfolio"},
            ],
            [
                {"text": "👤 پروفایل من", "callback_data": "cmd:my_profile"},
                {"text": "ℹ️ راهنما", "callback_data": "cmd:help"},
            ],
        ]
    }


def after_report_keyboard() -> dict[str, Any]:
    """کیبورد بعد از گزارش‌ها."""
    return {
        "inline_keyboard": [
            [
                {"text": "🏆 برترین‌ها", "callback_data": "cmd:today_top"},
                {"text": "⚠️ ضعیف‌ترین‌ها", "callback_data": "cmd:today_worst"},
            ],
            [
                {"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"},
                {"text": "🏠 منو اصلی", "callback_data": "cmd:menu"},
            ],
        ]
    }


def fund_actions_keyboard(symbol: str) -> dict[str, Any]:
    """دکمه‌های اقدام برای تحلیل تک صندوق."""
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 بروزرسانی تحلیل", "callback_data": f"fund:{symbol}"},
                {"text": "📜 تاریخچه تحلیل", "callback_data": f"fund_history:{symbol}"},
            ],
            [
                {"text": "⭐ اضافه به پیگیری", "callback_data": f"watch:{symbol}"},
                {"text": "➕ اضافه به سبد", "callback_data": f"pfadd:{symbol}"},
            ],
            [
                {"text": "📊 مقایسه با هم‌گروه", "callback_data": f"fund_compare:{symbol}"},
                {"text": "📈 بک‌تست استراتژی", "callback_data": f"fund_backtest:{symbol}"},
            ],
            [
                {"text": "🏠 منو اصلی", "callback_data": "cmd:menu"},
            ],
        ]
    }


def portfolio_actions_keyboard() -> dict[str, Any]:
    """دکمه‌های مدیریت سبد."""
    return {
        "inline_keyboard": [
            [
                {"text": "➕ افزودن صندوق", "callback_data": "cmd:pf_add_prompt"},
                {"text": "➖ حذف صندوق", "callback_data": "cmd:pf_del_prompt"},
            ],
            [
                {"text": "🔄 بروزرسانی سبد", "callback_data": "cmd:my_portfolio"},
                {"text": "📊 تحلیل ریسک سبد", "callback_data": "cmd:pf_risk"},
            ],
            [
                {"text": "🏠 منو اصلی", "callback_data": "cmd:menu"},
            ],
        ]
    }


def category_detail_keyboard(category: str) -> dict[str, Any]:
    """کیبورد جزئیات دسته‌بندی."""
    safe_cat = category.replace(" ", "_")
    return {
        "inline_keyboard": [
            [
                {"text": f"🥇 بهترین {category}", "callback_data": f"cat_best:{safe_cat}"},
                {"text": f"📊 همه {category}", "callback_data": f"cat_all:{safe_cat}"},
            ],
            [
                {"text": f"📈 مقایسه درونی {category}", "callback_data": f"cat_compare:{safe_cat}"},
                {"text": "🏠 منو اصلی", "callback_data": "cmd:menu"},
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


def help_text() -> str:
    return (
        "📘 راهنمای صندوقچی\n\n"
        "📊 گزارش‌ها و رنکینگ:\n"
        "• /morning_brief — گزارش صبحانه بازار (۰۸:۵۰)\n"
        "• /today_top — برترین‌های امروز\n"
        "• /today_worst — ضعیف‌ترین‌های امروز\n"
        "• /category_best — بهترین هر دسته‌بندی\n"
        "• /fund <نماد> — تحلیل عمیق تک صندوق\n\n"
        "📁 پرتفوی و پیگیری:\n"
        "• /portfolio — وضعیت و تحلیل سبد شما\n"
        "• /pf_add <نماد> <تعداد> [قیمت] — افزودن به سبد\n"
        "• /pf_del <نماد> — حذف از سبد\n"
        "• /watch <نماد> — اضافه به پیگیری\n"
        "• /watchlist — لیست پیگیری\n\n"
        "👤 پروفایل:\n"
        "• /profile — نمایش پروفایل\n"
        "• /risk low|medium|high — تنظیم ریسک\n"
        "• /capital <مبلغ> — تنظیم سرمایه\n\n"
        "💡 نکته: دکمه‌های منو همه دستورات را پوشش می‌دهند."
    )