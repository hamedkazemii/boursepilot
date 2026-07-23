"""انتشار گزارش‌های صندوقچی در کانال تلگرام."""

from __future__ import annotations

import logging
from typing import Any, Optional

from config import settings
from reports.formatters.human_report import HumanReportFormatter
from core.preopen.analyzer import PreopenSignal
from core.scoring.models import FundAssessment
from services.telegram import TelegramService

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
    ) -> bool:
        text = format_ranking_telegram(ranked, meta=meta, top_n=top_n, worst_n=worst_n)
        logger.info("publish ranking chars=%s funds=%s", len(text), len(ranked))
        return self.publish_text(text)

    def publish_preopen(self, signals: list[PreopenSignal], *, top_n: int = 12) -> bool:
        text = format_preopen_telegram(signals, top_n=top_n)
        logger.info("publish preopen chars=%s signals=%s", len(text), len(signals))
        return self.publish_text(text)

    def publish_fund(self, assessment: FundAssessment) -> bool:
        text = format_fund_telegram(assessment)
        return self.publish_text(text)



def format_ranking_telegram(ranked, meta=None, top_n=10, worst_n=0):
    funds = []

    for a in ranked[:top_n]:
        funds.append({
            "name": getattr(a, "name", None) or getattr(a, "symbol", ""),
            "symbol": getattr(a, "symbol", ""),
            "score": round(getattr(a, "final_score", 0), 1),
            "return_percent": getattr(a, "change_percent", "-"),
            "nav": getattr(a, "nav", "-"),
        })

    return HumanReportFormatter().build(funds)

def format_preopen_telegram(signals: list[PreopenSignal], *, top_n: int = 12) -> str:
    lines = [
        f"🔔 {settings.PRODUCT_NAME} | پیش‌سفارش صندوق‌ها",
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
    lines.append("⏱️ مناسب بازه ۸:۴۵ تا ۹:۰۰")
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
