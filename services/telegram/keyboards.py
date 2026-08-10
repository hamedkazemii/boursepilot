"""دکمه‌های اینلاین تلگرام — فقط دکمه‌های Contextual و مرتبط."""

from __future__ import annotations


# ---------- منوی اصلی (فقط ۹ دکمه) ----------
def main_menu_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📊 تحلیل لحظه‌ای بازار", "callback_data": "cmd:market_now"}],
            [{"text": "📅 تحلیل امروز بازار", "callback_data": "cmd:today_analysis"}],
            [{"text": "🏆 برترین‌های امروز", "callback_data": "cmd:today_top"}],
            [{"text": "⚠️ ضعیف‌ترین‌های امروز", "callback_data": "cmd:today_worst"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
            [{"text": "⭐ بهترین‌های هر دسته", "callback_data": "cmd:category_best"}],
            [{"text": "🔎 تحلیل صندوق", "callback_data": "cmd:fund_search"}],
            [{"text": "👤 پروفایل من", "callback_data": "cmd:my_profile"}],
            [{"text": "📖 راهنما", "callback_data": "cmd:help"}],
        ]
    }


# ---------- دکمه‌های Contextual برای هر Flow ----------

def after_report_keyboard() -> dict:
    """دکمه‌های پس از گزارش‌های بازار — فقط دو گزینه"""
    return {
        "inline_keyboard": [
            [{"text": "🔎 تحلیل یک صندوق", "callback_data": "cmd:fund_search"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def fund_actions_keyboard(symbol: str) -> dict:
    """دکمه‌های بعد از تحلیل تک صندوق"""
    return {
        "inline_keyboard": [
            [{"text": "🔎 تحلیل صندوق دیگر", "callback_data": "cmd:fund_search"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def category_selector_keyboard() -> dict:
    """انتخاب دسته برای 'بهترین‌های هر دسته'"""
    return {
        "inline_keyboard": [
            [{"text": "💰 سهامی", "callback_data": "cat_best:سهامی"}],
            [{"text": "📈 درآمد ثابت", "callback_data": "cat_best:درآمد ثابت"}],
            [{"text": "🥇 طلا و کالایی", "callback_data": "cat_best:طلا"}],
            [{"text": "⚖️ مختلط", "callback_data": "cat_best:مختلط"}],
            [{"text": "🚀 اهرمی", "callback_data": "cat_best:اهرم"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def portfolio_actions_keyboard() -> dict:
    """دکمه‌های سبد من"""
    return {
        "inline_keyboard": [
            [{"text": "➕ افزودن صندوق", "callback_data": "cmd:pf_add_prompt"}],
            [{"text": "✏️ ویرایش سبد", "callback_data": "cmd:pf_edit_prompt"}],
            [{"text": "🗑 حذف صندوق", "callback_data": "cmd:pf_del_prompt"}],
            [{"text": "🔎 تحلیل سبد", "callback_data": "cmd:pf_risk"}],
        ]
    }


def pf_add_prompt_keyboard() -> dict:
    """انتخاب صندوق برای افزودن — نمایش برترین‌های امروز"""
    # این تابع فقط کیبورد را برمی‌گرداند؛ نمادها در هندلر پر می‌شوند
    return {
        "inline_keyboard": [
            [{"text": "🔍 جستجوی دستی", "callback_data": "cmd:fund_search"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def pf_add_select_keyboard(symbols: list[str]) -> dict:
    """کیبورد انتخاب صندوق برای افزودن (5 صندوق برتر)"""
    rows = []
    for sym in symbols[:5]:
        rows.append([{"text": f"➕ {sym}", "callback_data": f"pfadd:{sym}"}])
    rows.append([{"text": "🔍 جستجوی دستی", "callback_data": "cmd:fund_search"}])
    rows.append([{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}])
    return {"inline_keyboard": rows}


def pf_del_prompt_keyboard(symbols: list[str]) -> dict:
    """انتخاب صندوق برای حذف"""
    rows = []
    for sym in symbols:
        rows.append([{"text": f"🗑 {sym}", "callback_data": f"pfdel:{sym}"}])
    rows.append([{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}])
    return {"inline_keyboard": rows}


def pf_edit_prompt_keyboard(symbols: list[str]) -> dict:
    """انتخاب صندوق برای ویرایش"""
    rows = []
    for sym in symbols:
        rows.append([{"text": f"✏️ {sym}", "callback_data": f"pfedit:{sym}"}])
    rows.append([{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}])
    return {"inline_keyboard": rows}


def pf_edit_action_keyboard(symbol: str) -> dict:
    """گزینه‌های ویرایش برای یک صندوق خاص"""
    return {
        "inline_keyboard": [
            [{"text": "➕ خرید جدید", "callback_data": f"pfedit_buy:{symbol}"}],
            [{"text": "➖ فروش بخشی", "callback_data": f"pfedit_sell:{symbol}"}],
            [{"text": "✏️ اصلاح اطلاعات", "callback_data": f"pfedit_fix:{symbol}"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def cancel_only_keyboard() -> dict:
    """فقط دکمه لغو (برای مراحل wizard)"""
    return {
        "inline_keyboard": [
            [{"text": "❌ لغو", "callback_data": "cmd:menu"}],
        ]
    }


def confirm_cancel_keyboard(confirm_data: str, cancel_data: str = "cmd:menu") -> dict:
    """تأیید/لغو عمومی"""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ درسته", "callback_data": confirm_data},
                {"text": "✏️ اصلاح", "callback_data": cancel_data},  # اصلاح به منوی اصلی برمی‌گرداند
            ],
            [{"text": "❌ بی‌خیال", "callback_data": "cmd:menu"}],
        ]
    }


def confirm_delete_keyboard(symbol: str) -> dict:
    """تأیید حذف صندوق"""
    return {
        "inline_keyboard": [
            [
                {"text": "🗑 حذف", "callback_data": f"pfdel_confirm:{symbol}"},
                {"text": "❌ بی‌خیال", "callback_data": "cmd:my_portfolio"},
            ],
        ]
    }


def profile_keyboard() -> dict:
    """دکمه‌های پروفایل — فقط مرتبط"""
    return {
        "inline_keyboard": [
            [{"text": "✏️ تنظیمات پروفایل", "callback_data": "cmd:profile_settings"}],
            [{"text": "📁 سبد من", "callback_data": "cmd:my_portfolio"}],
        ]
    }


def help_text() -> str:
    """متن راهنما — برای /help"""
    return (
        "سلام 👋\n"
        "من صندوقچی‌ام.\n\n"
        "اینجام تا کمک کنم صندوق‌های سرمایه‌گذاری ایران رو بهتر بشناسی،\n"
        "با هم مقایسه‌شون کنی و آگاهانه‌تر تصمیم بگیری.\n\n"
        "می‌تونی از من بخوای:\n\n"
        "📊 وضعیت لحظه‌ای صندوق‌ها رو بررسی کنم\n"
        "📅 تحلیل امروز بازار رو ببینی\n"
        "🏆 برترین‌های امروز رو ببینی\n"
        "⚠️ ضعیف‌ترین‌های امروز رو ببینی\n"
        "🔎 یک صندوق رو تحلیل کنم\n"
        "📁 سبدت رو مدیریت و تحلیل کنم\n"
        "⭐ بهترین صندوق هر دسته رو ببینی\n"
        "👤 پروفایلت رو بررسی کنی\n\n"
        "من تصمیم رو به جای تو نمی‌گیرم.\n"
        "کمکت می‌کنم اطلاعات رو بهتر ببینی.\n\n"
        "«هر تصمیم، شایسته آگاهی است.»"
    )