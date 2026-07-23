from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📊 تحلیل امروز",
                callback_data="today_analysis"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 برترین صندوق‌ها",
                callback_data="top_funds"
            )
        ],

        [
            InlineKeyboardButton(
                "📈 وضعیت بازار",
                callback_data="market_status"
            )
        ],

        [
            InlineKeyboardButton(
                "💼 پرتفوی من",
                callback_data="portfolio"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data="settings"
            ),
            InlineKeyboardButton(
                "❓ راهنما",
                callback_data="help"
            )
        ]

    ]

    return InlineKeyboardMarkup(keyboard)
