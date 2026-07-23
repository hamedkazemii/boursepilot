"""
تنظیمات مرکزی صندوقچی / BoursePilot.

مقادیر حساس فقط از محیط خوانده می‌شوند؛ هیچ کلید یا عدد بازار hardcode نمی‌شود.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    """خواندن متغیر محیطی با trim برای حذف newlineهای ناخواسته secret."""
    return os.getenv(name, default).strip()


def _env_float(name: str, default: float) -> float:
    raw = _env(name, "")
    if not raw:
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = _env(name, "")
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    """تنظیمات اجرایی پروژه."""

    # --- برند / محصول ---
    PRODUCT_NAME: str = _env("PRODUCT_NAME", "صندوقچی")

    # --- Telegram (فازهای بعد) ---
    TELEGRAM_BOT_TOKEN: str = _env("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = _env("TELEGRAM_CHAT_ID", "")

    # --- BRS Market Data API ---
    # Base رسمی مستندات: https://Api.BrsApi.ir/Tsetmc
    BRS_API_KEY: str = _env("BRS_API_KEY", "")
    BRS_BASE_URL: str = _env(
        "BRS_BASE_URL",
        "https://Api.BrsApi.ir/Tsetmc",
    )
    # فایروال BrsApi به User-Agent پیش‌فرض Python حساس است.
    BRS_USER_AGENT: str = _env(
        "BRS_USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
    )
    BRS_TIMEOUT_SECONDS: float = _env_float("BRS_TIMEOUT_SECONDS", 30.0)
    BRS_MAX_RETRIES: int = _env_int("BRS_MAX_RETRIES", 2)
    # type در AllSymbols — طبق مستند نمونه‌ها معمولاً 1
    BRS_ALL_SYMBOLS_TYPE: int = _env_int("BRS_ALL_SYMBOLS_TYPE", 1)

    # provider فعال برای لایه داده بازار
    MARKET_DATA_PROVIDER: str = _env("MARKET_DATA_PROVIDER", "brs")

    # --- Snapshot / ranking ---
    SNAPSHOT_DIR: str = _env("SNAPSHOT_DIR", "data/snapshots")
    SCORING_CONFIG_PATH: str = _env("SCORING_CONFIG_PATH", "config/scoring.yaml")
    # برای سرعت توسعه پیش‌فرض false؛ در پروداکشن true کنید
    FETCH_NAV_IN_DAILY_RANK: bool = _env("FETCH_NAV_IN_DAILY_RANK", "false").lower() in {"1", "true", "yes", "on"}
    NAV_FETCH_WORKERS: int = _env_int("NAV_FETCH_WORKERS", 4)

    # --- History Engine / SQLite ---
    DATABASE_PATH: str = _env("DATABASE_PATH", "data/database.db")
    HISTORY_CACHE_TTL_SECONDS: int = _env_int("HISTORY_CACHE_TTL_SECONDS", 300)
    # گزارش تلگرام: smart = خلاصه + پیام‌های جدا
    TELEGRAM_SMART_REPORT: bool = _env("TELEGRAM_SMART_REPORT", "true").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    TELEGRAM_TOP_N: int = _env_int("TELEGRAM_TOP_N", 5)
    TELEGRAM_WORST_N: int = _env_int("TELEGRAM_WORST_N", 5)


settings = Settings()
