"""طبقه‌بندی نوع صندوق.

سازگاری:
- تابع classify(text) مثل قبل
- کلاس FundClassifier برای RealMarketScanner و tools قدیمی
"""

from __future__ import annotations

from typing import Any, Mapping, Union

from services.providers.textnorm import normalize_fa


def classify(text: Union[str, Mapping[str, Any], None]) -> str:
    """تشخیص نوع صندوق از متن یا dict صندوق."""
    if text is None:
        return "UNKNOWN"

    if isinstance(text, Mapping):
        parts = [
            str(text.get("symbol") or ""),
            str(text.get("name") or ""),
            str(text.get("title") or ""),
            str(text.get("type") or ""),
            str(text.get("description") or ""),
            str(text.get("sector") or ""),
        ]
        blob = " ".join(parts)
    else:
        blob = str(text)

    blob = normalize_fa(blob.replace("\u200c", " "))

    if "طلا" in blob or "پشتوانه طلا" in blob or "کالای" in blob and "طلا" in blob:
        return "طلا"

    if "اهرمی" in blob or "اهرم" in blob:
        return "اهرم"

    if "درآمد ثابت" in blob or "درآمدثابت" in blob or ("ثابت" in blob and "درآمد" in blob):
        return "درآمد ثابت"

    if "مختلط" in blob:
        return "مختلط"

    if "بخشی" in blob:
        return "بخشی"

    if "سهام" in blob or "سهامی" in blob:
        return "سهامی"

    if "صندوق" in blob:
        return "سایر صندوق"

    return "UNKNOWN"


class FundClassifier:
    """API کلاسی برای اسکنر/ابزارهای قدیمی."""

    def classify(self, text: Union[str, Mapping[str, Any], None]) -> str:
        return classify(text)
