"""انتشار گزارش‌های صندوقچی در کانال تلگرام."""

from __future__ import annotations

import logging
from typing import Any, Optional

from config import settings
from core.scoring.models import FundAssessment
from services.telegram.client import TelegramService
from services.telegram.smart_report import (
    build_smart_morning_messages,
    format_market_summary_telegram,
)

logger = logging.getLogger(__name__)


class TelegramPublisher:
    def __init__(self, telegram: Optional[TelegramService] = None) -> None:
        self.telegram = telegram or TelegramService()

    def publish_text(self, text: str) -> bool:
        return self.telegram.send_message(text)

    def publish_ranking(
        self,
        ranked: list[FundAssessment],
        *,
        meta: Optional[dict[str, Any]] = None,
        top_n: int = 12,
        worst_n: int = 6,
        smart: bool = True,
    ) -> bool:
        """
        smart=True (پیش‌فرض): خلاصه بازار + پیام‌های جدا برای top/worst
        smart=False: یک پیام فشرده قدیمی
        """
        if smart:
            return self.publish_smart_morning(
                ranked,
                meta=meta,
                top_n=min(top_n, 5) if top_n else 5,
                worst_n=min(worst_n, 5) if worst_n else 5,
            )
        text = format_ranking_telegram(ranked, meta=meta, top_n=top_n, worst_n=worst_n)
        logger.info("publish ranking chars=%s funds=%s", len(text), len(ranked))
        return self.publish_text(text)

    def publish_smart_morning(
        self,
        ranked: list[FundAssessment],
        *,
        meta: Optional[dict[str, Any]] = None,
        top_n: int = 5,
        worst_n: int = 5,
        with_menu: bool = True,
    ) -> bool:
        messages = build_smart_morning_messages(
            ranked,
            meta=meta,
            top_n=top_n,
            worst_n=worst_n,
        )
        logger.info(
            "publish smart morning messages=%s funds=%s",
            len(messages),
            len(ranked),
        )
        markup = None
        if with_menu:
            from services.telegram.keyboards import after_report_keyboard

            markup = after_report_keyboard()
        return self.telegram.send_messages(messages, reply_markup_last=markup)

    def publish_preopen(self, signals: list, *, top_n: int = 12) -> bool:
        text = format_preopen_telegram(signals, top_n=top_n)
        logger.info("publish preopen chars=%s signals=%s", len(text), len(signals))
        return self.publish_text(text)

    def publish_fund(self, assessment: FundAssessment) -> bool:
        text = format_fund_telegram(assessment)
        return self.publish_text(text)


def format_ranking_telegram(
    ranked: list[FundAssessment],
    *,
    meta: Optional[dict[str, Any]] = None,
    top_n: int = 12,
    worst_n: int = 6,
) -> str:
    """فرمت فشرده تک‌پیامی (سازگاری عقب‌رو)."""
    meta = meta or {}
    # اگر خواستیم خلاصه بازار را هم در تک‌پیام داشته باشیم:
    head = format_market_summary_telegram(ranked, meta=meta)
    # برای سازگاری تست‌های قدیمی، بخش برتر/ضعیف را هم نگه می‌داریم
    product = settings.PRODUCT_NAME
    lines = [
        f"📊 {product} | رنکینگ روزانه صندوق‌ها",
        f"تعداد بررسی‌شده: {len(ranked)}",
    ]
    generated = meta.get("generated_at") or ""
    if generated:
        lines.append(f"زمان: {generated}")
    if meta.get("fetch_nav"):
        lines.append(f"NAV موفق: {meta.get('nav_success', 0)}")
    lines.append("")
    lines.append("🏆 برترین‌ها")
    for a in ranked[:top_n]:
        chg = f"{a.change_pct:+.2f}%" if a.change_pct is not None else "-"
        lines.append(
            f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label} | {chg}"
        )
        if a.summary_reasons:
            reason = a.summary_reasons[0]
            if reason.startswith("امتیاز نهایی"):
                reason = a.summary_reasons[1] if len(a.summary_reasons) > 1 else reason
            lines.append(f"   • {reason}")

    if ranked:
        lines.append("")
        lines.append("⚠️ ضعیف‌ترین‌ها")
        worst = list(reversed(ranked[-worst_n:])) if worst_n else []
        for a in worst:
            lines.append(
                f"{a.rank}. {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}"
            )

    by_type: dict[str, FundAssessment] = {}
    for a in ranked:
        if a.fund_type not in by_type:
            by_type[a.fund_type] = a
    if by_type:
        lines.append("")
        lines.append("📁 برترین هر نوع")
        for ftype, a in sorted(by_type.items(), key=lambda kv: -kv[1].final_score)[:8]:
            lines.append(f"• {ftype}: {a.symbol} ({a.final_score:.1f})")

    lines.append("")
    lines.append("ℹ️ امتیاز بر اساس نقدشوندگی، پیش‌سفارش، پول هوشمند، مومنتوم، حجم و NAV")
    # head فقط برای استفاده‌های جدید؛ خروجی اصلی همان compact است
    _ = head
    return "\n".join(lines)


def format_preopen_telegram(signals: list, *, top_n: int = 12) -> str:
    lines = [
        f"🔔 {settings.PRODUCT_NAME} | پیش‌گشایش صندوق‌ها",
        f"تعداد: {len(signals)}",
        "",
        "🔥 فشار خرید",
    ]
    buys = [s for s in signals if s.bias in {"buy_pressure", "buy_queue"}][:top_n]
    sells = [s for s in signals if s.bias in {"sell_pressure", "sell_queue"}]
    sells = sorted(sells, key=lambda s: s.score)[:8]

    if not buys:
        lines.append("مورد برجسته‌ای نیست")
    for i, s in enumerate(buys, 1):
        lines.append(f"{i}. {s.symbol} | {s.bias_label} | نسبت {s.ratio:.2f}")

    lines.append("")
    lines.append("📉 فشار فروش / ریسک")
    if not sells:
        lines.append("مورد برجسته‌ای نیست")
    for i, s in enumerate(sells, 1):
        lines.append(f"{i}. {s.symbol} | {s.bias_label} | نسبت {s.ratio:.2f}")

    lines.append("")
    lines.append("⏱ مناسب بازه ۸:۴۵ تا ۹:۰۰")
    return "\n".join(lines)


def format_fund_telegram(a: FundAssessment) -> str:
    chg = f"{a.change_pct:+.2f}%" if a.change_pct is not None else "-"
    lines = [
        f"📌 {settings.PRODUCT_NAME} | {a.symbol}",
        a.name,
        f"نوع: {a.fund_type}",
        f"امتیاز: {a.final_score:.1f} | توصیه: {a.recommendation_label}",
        f"تغییر: {chg}",
    ]
    if a.premium_pct is not None:
        lines.append(f"حباب/تخفیف NAV: {a.premium_pct:.2f}%")
    lines.append("")
    lines.append("دلایل:")
    for r in a.summary_reasons[:5]:
        lines.append(f"• {r}")
    lines.append("")
    lines.append("جزئیات فاکتورها:")
    for f in a.factors:
        lines.append(f"• {f.title}: {f.score:.0f} ({f.label})")
        if f.reasons:
            lines.append(f"  - {f.reasons[0]}")
    return "\n".join(lines)
