"""خطاهای لایه provider داده بازار."""

from __future__ import annotations


class ProviderError(Exception):
    """خطای پایه provider."""


class ProviderConfigError(ProviderError):
    """تنظیمات ناقص (مثلاً نبود API key)."""


class ProviderHTTPError(ProviderError):
    """خطای HTTP یا پاسخ نامعتبر."""

    def __init__(self, message: str, status_code: int | None = None, payload: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ProviderAuthError(ProviderHTTPError):
    """کلید نامعتبر یا عدم دسترسی."""


class ProviderNotFoundError(ProviderError):
    """نماد یا منبع پیدا نشد."""
