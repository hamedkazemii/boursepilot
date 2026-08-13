"""گزارش‌های سرمایه‌گذارپسند — ساده، انسانی، عملی."""

from __future__ import annotations

from typing import Any, Optional

from config import settings
from core.scoring.models import FundAssessment


def humanized_market_summary(
    ranked: list[FundAssessment],
    *,
    up_count: int = 0,
    down_count: int = 0,
    avg_change: float = 0.0,
) -> str:
    """خلاصه بازار به زبان ساده برای سرمایه‌گذار معمولی."""
    mood = "مثبت 🟢" if avg_change > 0.5 else "نزولی 🔴" if avg_change < -0.5 else "خنثی ⚪"
    momentum = "شاخص‌ها در حال بالا رفتن هستند" if avg_change > 0.5 else "فشار فروش در بازار حس می‌شود" if avg_change < -0.5 else "بازار آرام است"

    lines = [
        f"📊 وضعیت امروز بازار صندوق‌ها",
        "",
        f"خلاصه: بازار امروز {mood}",
        f"{momentum}",
        "",
        f"• 📈 صندوق‌های مثبت: {up_count} مورد",
        f"• 📉 صندوق‌های منفی: {down_count} مورد",
        f"• میانگین تغییر: {avg_change:+.2f}%",
        "",
        "در ادامه برترین‌ها و وضعیت پرتفوی شما ارسال می‌شه.",
    ]
    return "\n".join(lines)


def humanized_fund_card(a: FundAssessment, *, kind: str = "neutral") -> str:
    """کارت صندوق برای سرمایه‌گذار معمولی — بدون اعداد خام زیاد."""
    score_label = _score_label_fa(a.final_score)
    action_label = _action_label_fa(a.final_score)
    risk_level = _risk_from_score(a.final_score)

    lines = [
        f"{'🏆' if kind == 'top' else '⚠️' if kind == 'worst' else '📌'} {a.symbol}",
        f"📝 {a.name}",
        f"📁 نوع: {a.fund_type}",
        "",
        f"وضعیت کلی: {score_label}",
        f"توصیه: {action_label}",
        f"سطح ریسک: {risk_level}",
    ]

    # دلایل ساده
    if a.summary_reasons:
        lines.append("")
        lines.append("💡 چرا این نتیجه؟")
        for r in a.summary_reasons[:3]:
            lines.append(f"• {r}")

    # فرصت/ریسک
    lines.append("")
    if kind == "top":
        lines.append("✅ فرصت: روند خوب + نقدشوندگی بالا")
        if a.premium_pct is not None and a.premium_pct < 0:
            lines.append(f"✅ اضافه: با تخفیف نسبت به NAV معامله می‌شه ({a.premium_pct:+.1f}%)")
    elif kind == "worst":
        lines.append("⚠️ ریسک: مومنتوم ضعیف‌تر از بازار")
        if a.premium_pct is not None and a.premium_pct > 1:
            lines.append(f"⚠️ اضافه: حباب NAV داره ({a.premium_pct:+.1f}%)")

    return "\n".join(lines)


def humanized_portfolio_report(
    items: list[dict[str, Any]],
    prices: dict[str, float],
    user_profile: dict[str, Any],
) -> str:
    """گزارش پرتفوی برای سرمایه‌گذار معمولی."""
    lines = [
        "📁 وضعیت پرتفوی شما",
        "",
    ]

    if not items:
        lines.append("هنوز صندوقی ثبت نکردید.")
        lines.append("برای شروع: /pf_add <نماد> <تعداد> [قیمت خرید]")
        return "\n".join(lines)

    total_cost = 0.0
    total_value = 0.0
    best_sym = ""
    best_pnl = -1e9
    worst_sym = ""
    worst_pnl = 1e9

    for it in items:
        sym = it["symbol"]
        qty = float(it.get("quantity", 0))
        cost = float(it.get("avg_cost", 0))
        px = prices.get(sym, cost)
        val = qty * px
        cval = qty * cost
        pnl = val - cval
        pnl_pct = (pnl / cval * 100) if cval else 0

        total_cost += cval
        total_value += val

        status_emoji = "🟢" if pnl_pct >= 0 else "🔴"
        lines.append(
            f"{status_emoji} {sym}: {pnl_pct:+.1f}% | "
            f"ارزش فعلی {val:,.0f} تومان"
        )

        if pnl > best_pnl:
            best_pnl = pnl
            best_sym = sym
        if pnl < worst_pnl:
            worst_pnl = pnl
            worst_sym = sym

    total_pnl_pct = ((total_value / total_cost - 1) * 100) if total_cost else 0

    lines.append("")
    lines.append(f"💰 ارزش کل پرتفو: {total_value:,.0f} تومان")
    lines.append(f"📊 بازده کل: {total_pnl_pct:+.1f}%")

    if best_sym:
        lines.append(f"🏆 بهترین: {best_sym} ({best_pnl:,.0f} تومان)")
    if worst_sym and worst_sym != best_sym:
        lines.append(f"⚠️ ضعیف‌ترین: {worst_sym} ({worst_pnl:,.0f} تومان)")

    # ریسک پرتفو
    risk = user_profile.get("risk_profile", "medium")
    if risk == "low" and total_pnl_pct < -3:
        lines.append("")
        lines.append("💡 توصیه: شما پروفایل کم‌ریسک دارید. توصیه می‌شه روی صندوق‌های با ریسک پایین تمرکز کنید.")
    elif risk == "high" and total_pnl_pct > 5:
        lines.append("")
        lines.append("💡 توصیه: روند پرتفوی شما خوبه. می‌تونید بخشی از سود رو قفل کنید.")

    return "\n".join(lines)


def _score_label_fa(score: float) -> str:
    if score >= 80:
        return "بسیار خوب ⭐⭐⭐"
    if score >= 65:
        return "خوب ⭐⭐"
    if score >= 50:
        return "متوسط ⭐"
    if score >= 35:
        return "ضعیف ⚠️"
    return "بسیار ضعیف ❌"


def _action_label_fa(score: float) -> str:
    if score >= 80:
        return "خرید (قوی)"
    if score >= 65:
        return "خرید"
    if score >= 50:
        return "نگهداری"
    if score >= 35:
        return "فروش"
    return "فروش (قوی)"


def _risk_from_score(score: float) -> str:
    if score >= 70:
        return "کم 🟢"
    if score >= 45:
        return "متوسط 🟡"
    return "زیاد 🔴"
