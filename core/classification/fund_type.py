"""طبقه‌بندی نوع صندوق از روی متن sector/name."""

from __future__ import annotations

from services.providers.models import SymbolQuote
from services.providers.textnorm import normalize_fa


def classify_fund_type(quote: SymbolQuote) -> str:
    text = normalize_fa(
        " ".join(str(x or "") for x in (quote.symbol, quote.name, quote.sector, quote.board))
    )

    rules = [
        ("طلا", ("طلا", "زر")),
        ("اهرم", ("اهرم", "اهرمی")),
        ("درآمد ثابت", ("درآمد ثابت", "درآمدثابت", "ثابت")),
        ("بخشی", ("بخشی",)),
        ("مختلط", ("مختلط",)),
        ("سهامی", ("سهامی", "سهام")),
        ("کالایی", ("کالایی", "کالا", "زعفران", "نقره")),
        ("املاک", ("املاک", "مستغلات")),
    ]
    for label, keys in rules:
        if any(k in text for k in keys):
            return label
    if "صندوق" in text:
        return "سایر صندوق"
    return "نامشخص"
