"""فرمت گزارش هوشمند چندپیامی تلگرام.

ساختار:
1) یک پیام خلاصه بازار
2) N پیام جدا برای برترین‌ها
3) N پیام جدا برای ضعیف‌ترین‌ها
"""

from __future__ import annotations

from typing import Any, Optional

from config import settings
from core.analytics.explain import explain_fund
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
    return [format_fund_card(a, kind="top") for a in ranked[: max(0, n)]]


def format_worst_fund_messages(
    ranked: list[FundAssessment],
    *,
    n: int = 5,
) -> list[str]:
    if n <= 0 or not ranked:
        return []
    worst = list(reversed(ranked[-n:]))
    return [format_fund_card(a, kind="worst") for a in worst]


def build_smart_morning_messages(
    ranked: list[FundAssessment],
    *,
    meta: Optional[dict[str, Any]] = None,
    top_n: int = 5,
    worst_n: int = 5,
) -> list[str]:
    meta = meta or {}
    summary = build_market_summary(
        ranked,
        generated_at=str(meta.get("generated_at") or ""),
    )
    msgs = [format_market_summary_telegram(ranked, meta=meta, summary=summary)]
    msgs.extend(format_top_fund_messages(ranked, n=top_n))
    msgs.extend(format_worst_fund_messages(ranked, n=worst_n))
    return msgs


def format_fund_card(a: FundAssessment, *, kind: str) -> str:
    product = settings.PRODUCT_NAME
    if kind == "top":
        header = f"🏆 {product} | صندوق برتر #{a.rank or '-'}"
        why = "چرا در برترین‌هاست؟"
    else:
        header = f"⚠️ {product} | صندوق ضعیف #{a.rank or '-'}"
        why = "چرا در ضعیف‌هاست؟"

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
    if a.premium_pct is not None and -25 <= float(a.premium_pct) <= 25:
        lines.append(f"حباب/تخفیف NAV: {a.premium_pct:+.2f}%")

    lines.append("")
    lines.append(why)
    for r in explain_fund(a, kind="top" if kind == "top" else "worst", max_items=6):
        lines.append(f"• {r}")

    # فاکتورها: برای weak از ضعیف به قوی، برای top از قوی به ضعیف
    if a.factors:
        lines.append("")
        lines.append("جزئیات فاکتورها:")
        ordered = sorted(
            a.factors,
            key=lambda f: f.score,
            reverse=(kind == "top"),
        )
        for f in ordered:
            mark = "🟢" if f.score >= 65 else "🔴" if f.score <= 45 else "🟡"
            lines.append(f"{mark} {f.title}: {f.score:.0f} ({f.label})")

    return "\n".join(lines)


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
