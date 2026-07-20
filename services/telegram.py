import requests

from config import settings


class TelegramService:

    def send_message(self, message: str) -> bool:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            print("Telegram is not configured.")
            print(message)
            return False

        url = (
            f"https://api.telegram.org/bot"
            f"{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        )

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.post(url, json=payload, timeout=10)

        return response.ok
