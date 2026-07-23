"""
نرمال‌سازی متن/نماد فارسی برای match پایدار با BRS.

مشکل رایج: «ي/ك» عربی در رجیستری قدیمی در برابر «ی/ک» فارسی در BRS.
"""

from __future__ import annotations

_ARABIC_YE = "\u064a"  # ي
_PERSIAN_YE = "\u06cc"  # ی
_ARABIC_KAF = "\u0643"  # ك
_PERSIAN_KAF = "\u06a9"  # ک
_ALEF_MADDA = "\u0622"
_ALEF = "\u0627"


def normalize_fa(text: str) -> str:
    """یکسان‌سازی حروف عربی/فارسی و حذف فاصله‌های زائد و ZWNJ برای مقایسه."""
    if text is None:
        return ""
    value = str(text).strip()
    value = value.replace(_ARABIC_YE, _PERSIAN_YE)
    value = value.replace(_ARABIC_KAF, _PERSIAN_KAF)
    # ZWNJ و فاصله‌های خاص
    value = value.replace("\u200c", " ")
    value = value.replace("\u200f", "")
    value = value.replace("\u200e", "")
    while "  " in value:
        value = value.replace("  ", " ")
    return value.strip()


def normalize_symbol(symbol: str) -> str:
    """نرمال‌سازی نماد (l18)."""
    return normalize_fa(symbol)
