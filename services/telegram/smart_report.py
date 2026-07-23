"""فرمت گزارش هوشمند چندپیامی تلگرام (فاز ۴).

ساختار:
1) یک پیام خلاصه بازار
2) N پیام جدا برای برترین‌ها
3) N پیام جدا برای ضعیف‌ترین‌ها
"""

from __future__ import annotations

from typing import Any, Optional

from config import settings
from core.analytics.market_summary import MarketSummary, build_market_summary
from core.scoring.models import FundAssessment


def format_market_summary_telegram(
    ranked: list[FundAssessment],
    *,
    meta: Optional[dict[str, Any]] = None,
    summary: Optional[MarketSummary] = None,
) -> str:
    meta = meta or {}
    summary = summary or build_market_summary(
        ranked,
        generated_at=str(meta.get("generated_at") or ""),
    )
    product = settings.PRODUCT_NAME
    lines = [
        f"📊 {product} | گزارش هوشمند بازار",
        "",
        f"امروز {summary.funds_count} صندوق بررسی شد",
        "",
        f"وضعیت بازار: {summary.market_status}",
        f"قدرت بازار: {_fmt_num(summary.market_power)} از ۱۰۰",
    ]
    if summary.avg_change_pct is not None:
        lines.append(f"میانگین تغییر: {summary.avg_change_pct:+.2f}%")
    lines.append(
        f"مثبت/منفی/خنثی: {summary.up_count} / {summary.down_count} / {summary.flat_count}"
    )
    lines.append("")
    lines.append(f"بهترین گروه: {summary.best_group}")
    lines.append(f"ضعیف‌ترین گروه: {summary.worst_group}")

    # top groups by strength
    groups = sorted(
        summary.group_stats.items(),
        key=lambda kv: kv[1].get("strength") or 0,
        reverse=True,
    )
    if groups:
        lines.append("")
        lines.append("📁 قدرت گروه‌ها")
        for name, st in groups[:6]:
            ch = st.get("avg_change_pct")
            ch_s = f"{ch:+.2f}%" if ch is not None else "-"
            lines.append(
                f"• {name}: {_fmt_num(st.get('strength'))} | {ch_s} | n={st.get('count')}"
            )

    if meta.get("generated_at"):
        lines.append("")
        lines.append(f"⏱ {meta['generated_at']}")
    if meta.get("fetch_nav"):
        lines.append(f"NAV موفق: {meta.get('nav_success', 0)}")

    lines.append("")
    lines.append("در ادامه ۵ صندوق برتر و ۵ صندوق ضعیف‌تر ارسال می‌شود.")
    return "\n".join(lines)


def format_top_fund_messages(
    ranked: list[FundAssessment],
    *,
    n: int = 5,
) -> list[str]:
    messages: list[str] = []
    for a in ranked[: max(0, n)]:
        messages.append(_format_fund_card(a, kind="top"))
    return messages


def format_worst_fund_messages(
    ranked: list[FundAssessment],
    *,
    n: int = 5,
) -> list[str]:
    if n <= 0 or not ranked:
        return []
    worst = list(reversed(ranked[-n:]))
    return [_format_fund_card(a, kind="worst") for a in worst]


def build_smart_morning_messages(
    ranked: list[FundAssessment],
    *,
    meta: Optional[dict[str, Any]] = None,
    top_n: int = 5,
    worst_n: int = 5,
) -> list[str]:
    """لیست کامل پیام‌های صبحگاهی هوشمند."""
    meta = meta or {}
    summary = build_market_summary(
        ranked,
        generated_at=str(meta.get("generated_at") or ""),
    )
    msgs = [format_market_summary_telegram(ranked, meta=meta, summary=summary)]
    msgs.extend(format_top_fund_messages(ranked, n=top_n))
    msgs.extend(format_worst_fund_messages(ranked, n=worst_n))
    return msgs


def _format_fund_card(a: FundAssessment, *, kind: str) -> str:
    product = settings.PRODUCT_NAME
    if kind == "top":
        header = f"🏆 {product} | صندوق برتر #{a.rank or '-'}"
    else:
        header = f"⚠️ {product} | صندوق ضعیف #{a.rank or '-'}"

    chg = f"{a.change_pct:+.2f}%" if a.change_pct is not None else "-"
    lines = [
        header,
        "",
        f"📌 {a.symbol} — {a.name}",
        f"نوع: {a.fund_type}",
        f"امتیاز نهایی: {a.final_score:.1f} / 100",
        f"توصیه: {a.recommendation_label}",
        f"تغییر روز: {chg}",
    ]
    if a.volume is not None:
        lines.append(f"حجم: {_fmt_int(a.volume)}")
    if a.value is not None:
        lines.append(f"ارزش معاملات: {_fmt_int(a.value)}")
    if a.premium_pct is not None:
        lines.append(f"حباب/تخفیف NAV: {a.premium_pct:+.2f}%")

    lines.append("")
    lines.append("چرا این رتبه؟")
    reasons = _smart_reasons(a)
    for r in reasons[:6]:
        lines.append(f"• {r}")

    # factor breakdown compact
    if a.factors:
        lines.append("")
        lines.append("جزئیات فاکتورها:")
        for f in a.factors:
            lines.append(f"• {f.title}: {f.score:.0f} ({f.label})")

    return "\n".join(lines)


def _smart_reasons(a: FundAssessment) -> list[str]:
    """ترکیب summary_reasons و reasons فاکتورها — بدون تکرار عنوان امتیاز نهایی."""
    out: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        t = (text or "").strip()
        if not t or t in seen:
            return
        if t.startswith("امتیاز نهایی"):
            return
        seen.add(t)
        out.append(t)

    for r in a.summary_reasons:
        add(r)
    for f in a.factors:
        for r in f.reasons:
            add(f"{f.title}: {r}")
        if not f.reasons and f.label:
            add(f"{f.title}: {f.label} ({f.score:.0f})")

    if a.change_pct is not None and a.change_pct >= 1.5:
        add(f"بازده امروز قوی بوده است ({a.change_pct:+.2f}%).")
    if a.change_pct is not None and a.change_pct <= -1.5:
        add(f"فشار فروش امروز قابل توجه است ({a.change_pct:+.2f}%).")
    if a.premium_pct is not None and a.premium_pct <= -0.5:
        add(f"با تخفیف نسبت به NAV معامله می‌شود ({a.premium_pct:.2f}%).")
    if a.premium_pct is not None and a.premium_pct >= 1.0:
        add(f"حباب NAV نسبتاً بالاست ({a.premium_pct:.2f}%).")

    if not out:
        out.append("بر اساس ترکیب نقدشوندگی، جریان پول و مومنتوم امتیازدهی شده است.")
    return out


def _fmt_num(v: Any) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):.1f}"
    except Exception:
        return str(v)


def _fmt_int(v: Any) -> str:
    if v is None:
        return "-"
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return str(v)
