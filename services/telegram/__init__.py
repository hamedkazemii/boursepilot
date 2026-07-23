"""بسته تلگرام صندوقچی."""

from services.telegram.client import TelegramService, chunk_text

__all__ = [
    "TelegramService",
    "chunk_text",
]


def __getattr__(name: str):
    # lazy exports برای جلوگیری از import دایره‌ای سنگین
    if name == "TelegramPublisher":
        from services.telegram.publisher import TelegramPublisher

        return TelegramPublisher
    if name in {
        "build_smart_morning_messages",
        "format_market_summary_telegram",
        "format_top_fund_messages",
        "format_worst_fund_messages",
    }:
        from services.telegram import smart_report

        return getattr(smart_report, name)
    if name == "SandoghchiBot":
        from services.telegram_bot import SandoghchiBot

        return SandoghchiBot
    raise AttributeError(name)
