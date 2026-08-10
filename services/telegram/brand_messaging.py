"""پیام‌سازی برند-سازگار برای تلگرام — بر اساس سند هویت صندوقچی.

اصل‌ها: User=Hero, AI=Guide, DATA→ANALYSIS→INSIGHT, Trust First, Explainability First, No Hype
"""

from __future__ import annotations

from typing import Any, Optional


# متن‌های ثابت برند
BRAND_NAME = "صندوقچی"
BRAND_TAGLINE = "شما تصمیم می‌گیرید. من فقط آگاهی می‌دهم."
DISCLAIMER_DEFAULT = "این تحلیل برای اطلاع‌رسانی است، پیشنهاد خرید/فروش نیست."
SOURCE_TEMPLATE = "داده: {source}، {time}"


# ---------- ابزار کمکی ----------

def _chg(a) -> float:
    """برداشت تغییر قیمت امن از FundAssessment."""
    v = getattr(a, "change_pct", None)
    return float(v) if v is not None else 0.0


def _nav(a) -> Optional[float]:
    """برداشت NAV امن — اول NAV صدور/ابطال، سپس قیمت پایانی."""
    for attr in ("nav_issue", "nav_redeem", "issue_nav", "redeem_nav", "close_price", "last_price"):
        v = getattr(a, attr, None)
        if v:
            return float(v)
    return None


def _ind(a) -> dict:
    return (getattr(a, "extras", None) or {}).get("indicator") or {}


def _adv(a) -> dict:
    return (getattr(a, "extras", None) or {}).get("advanced_metrics") or {}


def _category_from_label(label: str):
    """نگاشت برچسب فارسی به FundCategory."""
    from core.market.taxonomy import CATEGORY_CONFIGS, FundCategory
    if not label:
        return FundCategory.EQUITY
    label = str(label).strip()
    for cat, cfg in CATEGORY_CONFIGS.items():
        if label == cfg.label or label == cat.value:
            return cat
    for cat, cfg in CATEGORY_CONFIGS.items():
        if label in cfg.examples:
            return cat
    return FundCategory.EQUITY


def get_category_config(cat):
    """دسترسی به پیکربندی دسته."""
    from core.market.taxonomy import get_category_config as _gcc
    return _gcc(cat)


def _sanitize_ratio(v, max_abs: float = 100.0):
    """بررسی عدد معتبر برای نمایش — مقادیر غیرواقعی (overflow/NaN/inf) را پنهان می‌کند."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f or f in (float("inf"), float("-inf")):  # NaN / inf
        return None
    if abs(f) > max_abs:  # تقسیم بر عدد نزدیک صفر → عدد بی‌معنی
        return None
    return f


def _fmt_ratio(v) -> Optional[str]:
    """فرمت عدد با دقت مناسب."""
    f = _sanitize_ratio(v)
    if f is None:
        return None
    return f"{f:.2f}"


def _fmt_money(amount: float) -> str:
    """فرمت مبلغ با جداکننده هزارگان و واحد ریال."""
    if amount is None:
        return "—"
    return f"{amount:,.0f} ریال"


# ---------- لایه‌های پیام (Progressive Disclosure) ----------

def layer1_result(title: str, score: float, recommendation: str,
                  change_pct: Optional[float] = None) -> str:
    """Layer 1: نتیجه خلاصه — امتیاز، توصیه، تغییر"""
    rec_emoji = {
        "buy": "🟢", "strong_buy": "🟢",
        "hold": "🟡", "neutral": "🟡",
        "reduce": "🟠", "sell": "🔴", "strong_sell": "🔴",
    }.get(str(recommendation).lower(), "⚪")

    change_str = ""
    if change_pct is not None:
        arrow = "▲" if change_pct > 0 else "▼" if change_pct < 0 else "■"
        change_str = f" | {arrow} {abs(change_pct):.1f}%"

    return f"{rec_emoji} {title} — {score:.1f}/۱۰۰{change_str}"


def layer2_analysis(reasons: list[str], metrics: Optional[dict] = None) -> str:
    """Layer 2: دلیل و تحلیل — فاکتورهای کلیدی"""
    if not reasons:
        return ""

    lines = ["🔍 تحلیل:"]
    for i, r in enumerate(reasons[:5], 1):
        lines.append(f"  {i}. {r}")

    if metrics:
        metric_strs = []
        for k, v in metrics.items():
            if v is not None:
                metric_strs.append(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")
        if metric_strs:
            lines.append(f"  متریک‌ها: {', '.join(metric_strs)}")

    return "\n".join(lines)


def layer3_details(details: dict, limitations: Optional[list[str]] = None) -> str:
    """Layer 3: جزئیات و محدودیت‌ها"""
    if not details and not limitations:
        return ""

    lines = ["📋 جزئیات:"]
    for k, v in details.items():
        if v is not None:
            lines.append(f"  • {k}: {v}")

    if limitations:
        lines.append("\n⚠️ محدودیت‌ها و ریسک‌ها:")
        for lim in limitations:
            lines.append(f"  • {lim}")

    return "\n".join(lines)


def build_brand_message(
    title: str,
    layer1: str,
    layer2: str = "",
    layer3: str = "",
    source: str = "",
    timestamp: str = "",
    disclaimer: str = DISCLAIMER_DEFAULT,
) -> str:
    """ساخت پیام کامل برند-سازگار."""
    parts = [f"📊 {BRAND_NAME} — {title}", "━" * 22]

    if source and timestamp:
        parts.append(SOURCE_TEMPLATE.format(source=source, time=timestamp))
    elif source:
        parts.append(f"📡 منبع: {source}")

    parts.append("")
    parts.append(layer1)

    if layer2:
        parts.append("")
        parts.append(layer2)

    if layer3:
        parts.append("")
        parts.append(layer3)

    parts.append("")
    parts.append(f"⚠️ {disclaimer}")
    parts.append("")
    parts.append(BRAND_TAGLINE)

    return "\n".join(parts)


def format_home_brand(ranked, meta: Optional[dict] = None, user_profile: Optional[dict] = None) -> str:
    """فرمت صفحه اصلی (Home) — خلاصه وضعیت بازار و پروفایل."""
    meta = meta or {}
    n = len(ranked)
    if n == 0:
        return build_brand_message("خانه", "هنوز داده‌ای برای نمایش نداریم.", disclaimer="")

    up = sum(1 for a in ranked if _chg(a) > 0)
    down = sum(1 for a in ranked if _chg(a) < 0)
    market_power = ranked[0].final_score if ranked else 0

    # tendance globale
    if market_power >= 70:
        trend_label = "صعودی"
    elif market_power >= 50:
        trend_label = "متعادل"
    else:
        trend_label = "نزولی"

    # top 3 / worst 3
    top3 = ranked[:3]
    worst3 = list(reversed(ranked[-3:])) if len(ranked) >= 3 else list(reversed(ranked))

    l1 = (
        f"📊 وضعیت کلی بازار صندوق‌ها\n"
        f"قدرت بازار: {market_power:.0f}/100\n"
        f"روند کلی: {trend_label}\n"
        f"صندوق‌های صعودی: {up} | نزولی: {down}"
    )

    l2_lines = ["🏆 برترین‌های امروز"]
    for i, a in enumerate(top3, 1):
        l2_lines.append(f"  {i}. {a.symbol} | {a.final_score:.1f}")

    l2_lines.append("\n⚠️ نیازمند بررسی")
    for i, a in enumerate(worst3, 1):
        l2_lines.append(f"  {i}. {a.symbol} | {a.final_score:.1f}")

    l2 = "\n".join(l2_lines)

    l3 = ""
    if user_profile:
        risk = user_profile.get("risk_profile", "نامشخص")
        horizon = user_profile.get("horizon_months", "نامشخص")
        capital = user_profile.get("capital", "نامشخص")
        l3 = f"👤 پروفایل شما\n  • ریسک: {risk}\n  • افق: {horizon} ماه\n  • سرمایه: {capital:,.0f}"

    return build_brand_message(
        "خانه",
        l1,
        l2,
        l3,
        source=meta.get("source", "LocalDB"),
        timestamp=meta.get("timestamp", ""),
    )


# ---------- قالب‌های تخصصی ----------

def format_fund_card_brand(assessment, fund_type: str = "") -> str:
    """فرمت کارت صندوق برای لیست‌ها (Layer 1 + 2 مختصر)."""
    cat = _category_from_label(fund_type or getattr(assessment, "fund_type", ""))
    config = get_category_config(cat)

    # Layer 1
    l1 = layer1_result(
        f"{assessment.symbol} ({assessment.name or ''})",
        assessment.final_score,
        assessment.recommendation,
        _chg(assessment),
    )

    # Layer 2
    l2_parts = []

    nav = _nav(assessment)
    if nav:
        l2_parts.append("💰 قیمت:")
        l2_parts.append(f"  • قیمت/NAV: {nav:,.0f}")
        if assessment.premium_pct is not None:
            l2_parts.append(f"  • پرمیوم/دیسکانت: {assessment.premium_pct:+.1f}%")

    ind = _ind(assessment)
    ind_items = []
    if ind.get("rsi14") is not None:
        ind_items.append(f"RSI: {ind['rsi14']:.0f}")
    if ind.get("macd_signal") is not None:
        ind_items.append(f"MACD: {ind['macd_signal']:.2f}")
    if ind.get("ema20") is not None:
        ema_state = "بالای EMA20" if ind.get("extras", {}).get("above_ema20") else "زیر EMA20"
        ind_items.append(f"EMA20: {ind['ema20']:.0f} ({ema_state})")
    if ind_items:
        l2_parts.append("\n📈 اندیکاتورها (۳۰ روز):")
        l2_parts.append("  " + " | ".join(ind_items))

    adv = _adv(assessment)
    ratios = adv.get("ratios") or {}
    adv_items = []
    for key, label in (
        ("sharpe_ratio", "Sharpe"),
        ("sortino_ratio", "Sortino"),
        ("calmar_ratio", "Calmar"),
        ("omega_ratio", "Omega"),
    ):
        val = _fmt_ratio(ratios.get(key))
        if val is not None:
            adv_items.append(f"{label}: {val}")
    if ratios.get("max_drawdown") is not None:
        adv_items.append(f"MaxDD: {ratios['max_drawdown'] * 100:.1f}%")
    if ratios.get("var_95") is not None:
        adv_items.append(f"VaR 95%: {ratios['var_95'] * 100:.1f}%")
    if ratios.get("cvar_95") is not None:
        adv_items.append(f"CVaR 95%: {ratios['cvar_95'] * 100:.1f}%")
    if adv_items:
        l2_parts.append("\n🔬 متریک‌های پیشرفته:")
        l2_parts.append("  " + " | ".join(adv_items))

    fm = adv.get("factor_models") or {}
    fm_items = []
    if isinstance(fm, dict):
        for key, label in (("fama_french_3", "FF3"), ("carhart_4", "Carhart4")):
            model = fm.get(key) if isinstance(fm.get(key), dict) else None
            if model and model.get("alpha") is not None:
                fm_items.append(f"{label} α: {model['alpha']:+.2f}%")
    if fm_items:
        l2_parts.append("\n📊 فاکتور مدل‌ها:")
        l2_parts.append("  " + " | ".join(fm_items))

    l2 = "\n".join(l2_parts)
    cat_info = f" | دسته: {config.label}"

    return f"{l1}{cat_info}\n{l2}" if l2 else f"{l1}{cat_info}"


def format_market_now_brand(ranked, meta: Optional[dict] = None, session: Any = None) -> str:
    """فرمت تحلیل لحظه‌ای بازار — وضعیت فعلی، روندها، پتانسیل بالا/پایین."""
    meta = meta or {}
    n = len(ranked)
    if n == 0:
        return build_brand_message("تحلیل لحظه‌ای بازار", "هنوز داده‌ای برای تحلیل نداریم.", disclaimer="")

    up = sum(1 for a in ranked if _chg(a) > 0)
    down = sum(1 for a in ranked if _chg(a) < 0)
    avg_change = sum(_chg(a) for a in ranked) / n

    from collections import defaultdict
    group_scores: dict[str, list[float]] = defaultdict(list)
    for a in ranked:
        ft = a.fund_type or "نامشخص"
        group_scores[ft].append(a.final_score)

    group_avg = {k: sum(v) / len(v) for k, v in group_scores.items()}
    best_group = max(group_avg.keys(), key=lambda k: group_avg[k]) if group_avg else "—"
    worst_group = min(group_avg.keys(), key=lambda k: group_avg[k]) if group_avg else "—"

    session_line = ""
    if session is not None:
        label = getattr(session, "label", "")
        if label:
            session_line = f"🕐 جلسه: {label}\n"

    l1 = (
        f"{session_line}📊 وضعیت لحظه‌ای صندوق‌ها\n\n"
        f"الان وضعیت {n} صندوق رو بررسی کردم.\n"
        f"قدرت کلی بازار حدود {ranked[0].final_score:.0f} از ۱۰۰ه.\n\n"
        f"🟢 {up} صندوق در وضعیت صعودی\n"
        f"🔴 {down} صندوق در وضعیت نزولی\n\n"
        f"در مجموع، بازار فعلاً {'به سمت صعود در حال حرکت هست' if up > down else 'به سمت نزول در حال حرکت هست' if down > up else 'در حالت تعادل قرار داره'}.\n\n"
        f"🏆 بهترین گروه: {best_group} ({group_avg.get(best_group, 0):.1f})\n"
        f"⚠️ ضعیف‌ترین گروه: {worst_group} ({group_avg.get(worst_group, 0):.1f})"
    )

    # Layer 2: برترین/ضعیف‌ترین (بدون طلا/درآمد ثابت در رنکینگ کلی)
    from core.market.taxonomy import FundCategory, get_category_config
    general = [a for a in ranked if not get_category_config(_category_from_label(a.fund_type)).exclude_from_general_top5]
    top3 = general[:3] if len(general) >= 3 else ranked[:3]
    worst3 = list(reversed(ranked[-3:])) if len(ranked) >= 3 else list(reversed(ranked))

    l2_lines = ["🏆 صندوق‌هایی که الان وضعیت بهتری دارن:"]
    for i, a in enumerate(top3, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2_lines.append("\n⚠️ و صندوق‌هایی که فعلاً ضعیف‌ترن:")
    for i, a in enumerate(worst3, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2 = "\n".join(l2_lines)

    l3 = "اگر بخوای، هر صندوق رو جداگانه هم برات بررسی می‌کنم."

    source = meta.get("source", "LocalDB")
    timestamp = meta.get("timestamp", "")

    return build_brand_message(
        "تحلیل لحظه‌ای بازار",
        l1, l2, l3,
        source=source,
        timestamp=timestamp,
    )


def format_today_analysis(ranked, meta: Optional[dict] = None, session: Any = None) -> str:
    """فرمت تحلیل امروز بازار — روندها، پتانسیل بالا و ضعیف (برای اقدام امروز)."""
    meta = meta or {}
    n = len(ranked)
    if n == 0:
        return build_brand_message("تحلیل امروز بازار", "هنوز داده‌ای برای تحلیل نداریم.", disclaimer="")

    up = sum(1 for a in ranked if _chg(a) > 0)
    down = sum(1 for a in ranked if _chg(a) < 0)
    avg_change = sum(_chg(a) for a in ranked) / n

    from collections import defaultdict
    group_scores: dict[str, list[float]] = defaultdict(list)
    for a in ranked:
        ft = a.fund_type or "نامشخص"
        group_scores[ft].append(a.final_score)

    group_avg = {k: sum(v) / len(v) for k, v in group_scores.items()}
    best_group = max(group_avg.keys(), key=lambda k: group_avg[k]) if group_avg else "—"
    worst_group = min(group_avg.keys(), key=lambda k: group_avg[k]) if group_avg else "—"

    session_line = ""
    if session is not None:
        label = getattr(session, "label", "")
        if label:
            session_line = f"🕐 جلسه: {label}\n"

    l1 = (
        f"{session_line}☀️ تحلیل امروز صندوق‌ها\n\n"
        f"صبح امروز کل بازار صندوق‌ها رو بررسی کردم.\n\n"
        f"در مجموع {n} صندوق در تحلیل امروز قرار گرفتن.\n\n"
        f"بر اساس روندها، وضعیت گروه‌ها و داده‌های فعلی،\n"
        f"تصویر امروز بازار اینطوریه:\n\n"
        f"🟢 {up} صندوق صعودی | 🔴 {down} صندوق نزولی\n"
        f"میانگین تغییر: {avg_change:+.2f}%\n\n"
        f"🏆 گروه قوی: {best_group} ({group_avg.get(best_group, 0):.1f})\n"
        f"⚠️ گروه ضعیف: {worst_group} ({group_avg.get(worst_group, 0):.1f})"
    )

    from core.market.taxonomy import FundCategory, get_category_config
    general = [a for a in ranked if not get_category_config(_category_from_label(a.fund_type)).exclude_from_general_top5]
    top5 = general[:5] if len(general) >= 5 else ranked[:5]
    worst5 = list(reversed(ranked[-5:])) if len(ranked) >= 5 else list(reversed(ranked))

    l2_lines = ["🏆 ۵ صندوق برتر (پتانسیل ورود امروز):"]
    for i, a in enumerate(top5, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2_lines.append("\n⚠️ ۵ صندوق ضعیف (خطرناک‌ترین):")
    for i, a in enumerate(worst5, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2 = "\n".join(l2_lines)

    l3_lines = ["📌 نکات کلیدی:"]
    if up > down:
        l3_lines.append(f"  • بازار در حالت {'صعودی' if avg_change > 0 else 'متعادل'} است — {up} صندوق مثبت از {n}")
    else:
        l3_lines.append(f"  • بازار در حالت {'نزولی' if avg_change < 0 else 'متعادل'} است — {down} صندوق منفی از {n}")
    l3_lines.append(f"  • بهترین گروه امروز: {best_group} با میانگین {group_avg.get(best_group, 0):.1f}")
    l3_lines.append(f"  • ضعیف‌ترین گروه: {worst_group} با میانگین {group_avg.get(worst_group, 0):.1f}")
    l3_lines.append("  • این تحلیل مربوط به ابتدای امروز بازاره و با تحلیل لحظه‌ای که در طول روز به‌روزرسانی می‌شه فرق داره.")
    l3 = "\n".join(l3_lines)

    source = meta.get("source", "LocalDB")
    timestamp = meta.get("timestamp", "")

    return build_brand_message(
        "تحلیل امروز بازار",
        l1, l2, l3,
        source=source,
        timestamp=timestamp,
    )


def format_category_report_brand(category_key: str, ranked, meta: Optional[dict] = None) -> str:
    """فرمت گزارش دسته‌ای (طلا، درآمد ثابت، سهامی، اهرمی، مختلط)."""
    meta = meta or {}
    cat = _category_from_label(category_key)
    config = get_category_config(cat)

    if not ranked:
        return build_brand_message(
            f"{config.emoji} {config.label}",
            "صندوقی در این دسته یافت نشد.",
            disclaimer="",
        )

    l1 = f"{len(ranked)} صندوق در دسته {config.label} | بهترین: {ranked[0].symbol} ({ranked[0].final_score:.1f})"

    l2_lines = [f"🏆 برترین {config.label}:"]
    for i, a in enumerate(ranked[:5], 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label}")

    l2_lines.append(f"\n⚠️ وضعیت نیازمند بررسی در {config.label}:")
    for i, a in enumerate(list(reversed(ranked[-3:])), 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label}")

    l2 = "\n".join(l2_lines)

    from core.market.taxonomy import FundCategory
    l3_notes = {
        FundCategory.GOLD: "طلا/کالایی: پرمیوم NAV >۳٪ = ریسک اصلاح. همبستگی با طلا جهانی ردیابی شود.",
        FundCategory.FIXED_INCOME: "درآمد ثابت: فقط صندوق‌های اعتبار AA+ و مدت <۱ سال برای ریسک کم. بازده توزیعی ≠ بازده به سررسید.",
        FundCategory.LEVERAGE: "اهرمی: بتا >۱.۵ در بازار نوسانی خطرناک. فقط برای ریسک بالا و افق کوتاه.",
        FundCategory.EQUITY: "سهامی: مومنتوم + کیفیت + ارزش. تنوع بخش‌ها کاهش ریسک تمرکز می‌دهد.",
        FundCategory.MIXED: "مختلط: تخصیص دارایی کلید است. شارپ و تنوع معیار اصلی.",
    }
    l3 = l3_notes.get(cat, "")

    return build_brand_message(
        f"{config.emoji} {config.label}",
        l1, l2, l3,
        source=meta.get("source", "LocalDB"),
        timestamp=meta.get("timestamp", ""),
    )


def format_fund_deepdive_brand(assessment, fund_type: str = "") -> str:
    """فرمت تحلیل عمیق تک صندوق (Fund Deep Dive) — Layer 1/2/3."""
    cat = _category_from_label(fund_type or getattr(assessment, "fund_type", ""))
    config = get_category_config(cat)

    l1 = layer1_result(
        f"{assessment.symbol} ({assessment.name or ''})",
        assessment.final_score,
        assessment.recommendation,
        _chg(assessment),
    )

    # Layer 2: تحلیل دلایل
    reasons = []
    adv = _adv(assessment)
    ratios = adv.get("ratios") or {}

    # جمع‌آوری دلایل بر اساس متریک‌ها
    if _sanitize_ratio(ratios.get("sharpe_ratio")) and _sanitize_ratio(ratios.get("sharpe_ratio")) > 1:
        reasons.append("شارپ بالا — بازده خوب نسبت به ریسک")
    if _sanitize_ratio(ratios.get("sortino_ratio")) and _sanitize_ratio(ratios.get("sortino_ratio")) > 1:
        reasons.append("سورتینوی بالا — بازده خوب نسبت به ریسک نزولی")
    if _sanitize_ratio(ratios.get("calmar_ratio")) and _sanitize_ratio(ratios.get("calmar_ratio")) > 0.5:
        reasons.append("کلمار معتبر — مدیریت ریسک مناسب")

    ind = _ind(assessment)
    if ind.get("rsi14") is not None:
        if ind["rsi14"] < 30:
            reasons.append("RSI پایین — احتمال اصلاح صعودی")
        elif ind["rsi14"] > 70:
            reasons.append("RSI بالا — احتمال اصلاح نزولی")

    if assessment.premium_pct is not None:
        if assessment.premium_pct > 3:
            reasons.append("پرمیم NAV بالا — ریسک اصلاح")
        elif assessment.premium_pct < -3:
            reasons.append("دیسکانت NAV — پتانسیل رشد")

    if not reasons:
        reasons.append("تحلیل بر اساس ترکیب متریک‌های ریسک، بازده، مومنتوم و نقدشوندگی انجام شده")

    l2 = layer2_analysis(reasons)

    # Layer 3: جزئیات کامل
    details = {}

    nav = _nav(assessment)
    if nav:
        details["قیمت/NAV"] = f"{nav:,.0f} ریال"
        if assessment.premium_pct is not None:
            details["پرمیم/دیسکانت NAV"] = f"{assessment.premium_pct:+.1f}%"

    if ind.get("rsi14") is not None:
        details["RSI (۱۴ روزه)"] = f"{ind['rsi14']:.0f}"
    if ind.get("macd_signal") is not None:
        details["MACD سیگنال"] = f"{ind['macd_signal']:.2f}"
    if ind.get("ema20") is not None:
        details["EMA ۲۰"] = f"{ind['ema20']:.0f}"

    for key, label in (
        ("sharpe_ratio", "شارپ"),
        ("sortino_ratio", "سورتینو"),
        ("calmar_ratio", "کلمار"),
        ("omega_ratio", "اُمة"),
    ):
        val = _fmt_ratio(ratios.get(key))
        if val is not None:
            details[label] = val

    if ratios.get("max_drawdown") is not None:
        details["ماکزیمم دراداون"] = f"{ratios['max_drawdown'] * 100:.1f}%"
    if ratios.get("var_95") is not None:
        details["VaR ۹۵٪"] = f"{ratios['var_95'] * 100:.1f}%"
    if ratios.get("cvar_95") is not None:
        details["CVaR ۹۵٪"] = f"{ratios['cvar_95'] * 100:.1f}%"

    details["نوع صندوق"] = config.label
    details["رتبه"] = f"{getattr(assessment, 'rank', '—')}"

    limitations = [
        "این تحلیل بر اساس داده‌های تاریخی و لحظه‌ای است، تضمین عملکرد آینده نیست",
        "متریک‌های پیشرفته نیازمند حداقل ۳۰ روز داده معتبر هستند",
        "تصمیم نهایی سرمایه‌گذاری با شماست",
    ]

    l3 = layer3_details(details, limitations)

    return build_brand_message(
        f"تحلیل {assessment.symbol}",
        l1, l2, l3,
        source="LocalDB + Technical Analysis",
        timestamp="",
    )


def format_portfolio_brand(portfolio_items: list[dict], prices: dict[str, float],
                           user_profile: dict, ranked) -> str:
    """فرمت تحلیل سبد کاربر."""
    if not portfolio_items:
        return build_brand_message(
            "سبد من",
            "سبد تو خالیه.\nاگه بخوای با دکمه ➕ افزودن صندوق، اولین صندوق رو اضافه کن.",
            disclaimer="",
        )

    total_value = 0.0
    total_cost = 0.0
    l2_lines = ["📁 جزئیات سبد:"]

    for item in portfolio_items:
        sym = item["symbol"]
        qty = float(item.get("quantity") or 0)
        cost = float(item.get("avg_cost") or 0)
        price = prices.get(sym)
        
        # Sanity check: flag suspicious prices (e.g., gold funds < 10k, or >100x diff)
        use_cost = False
        if price is not None and price > 0:
            # Gold funds should be high price
            fund_name = item.get("name", "").lower()
            is_gold = "طلا" in fund_name or "gold" in fund_name.lower()
            if is_gold and price < 10000:
                use_cost = True  # likely corrupted data
            elif cost > 0 and price > cost * 100:
                use_cost = True  # unrealistic 100x jump
            elif cost > 0 and cost > price * 100:
                use_cost = True  # unrealistic 100x drop (data corruption)
        
        if use_cost or price is None or price <= 0:
            price = cost
            val = qty * price
            cval = val
            pnl_pct = 0.0
            l2_lines.append(f"  ⚠️ {sym}: قیمت بازار مشکوک — از بهای تمام‌شده استفاده شد ({_fmt_money(val)})")
        else:
            val = qty * price
            cval = qty * cost
            total_value += val
            total_cost += cval
            pnl = val - cval
            pnl_pct = (pnl / cval * 100) if cval else 0.0
            weight = (val / total_value * 100) if total_value > 0 else 0

            pnl_emoji = "🟢" if pnl_pct > 2 else "🟡" if pnl_pct > -2 else "🔴"
            l2_lines.append(f"  {pnl_emoji} {sym}: {weight:.0f}% | {pnl_pct:+.1f}% | {qty:g} واحد | ارزش: {_fmt_money(val)}")

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost else 0

    l1 = (
        f"📁 سبد شما\n\n"
        f"ارزش لحظه‌ای: {_fmt_money(total_value)}\n"
        f"بهای تمام‌شده: {_fmt_money(total_cost)}\n"
        f"سود/زیان: {_fmt_money(total_pnl)} ({total_pnl_pct:+.2f}%)\n"
        f"تعداد صندوق‌ها: {len(portfolio_items)}"
    )

    # تحلیل تنوع
    from core.market.taxonomy import classify_fund_category
    categories = {}
    for item in portfolio_items:
        cat = classify_fund_category(item.get("name", ""), item["symbol"])
        val = item["quantity"] * prices.get(item["symbol"], 0)
        categories[cat] = categories.get(cat, 0) + val

    l3_lines = ["🔍 تحلیل سبد:"]
    max_weight = max((item["quantity"] * prices.get(item["symbol"], 0) / total_value * 100) for item in portfolio_items) if total_value > 0 else 0
    if max_weight > 40:
        l3_lines.append(f"  ⚠️ تمرکز بالا: بیش از {max_weight:.0f}% در یک صندوق")
    if len(categories) < 3:
        l3_lines.append(f"  ⚠️ تنوع محدود: فقط {len(categories)} دسته")

    risk = user_profile.get("risk_profile", "medium")
    if risk == "low":
        leverage_val = categories.get("leverage", 0)
        if leverage_val > total_value * 0.1:
            l3_lines.append("  • ریسک کم: کاهش صندوق‌های اهرمی به <۱۰٪ پیشنهاد می‌شه")
    elif risk == "high":
        fixed_val = categories.get("fixed_income", 0)
        if fixed_val > total_value * 0.4:
            l3_lines.append("  • ریسک بالا: کاهش درآمد ثابت به <۴۰٪ برای رشد بیشتر")

    l3 = "\n".join(l3_lines)

    return build_brand_message(
        "تحلیل سبد",
        l1, "\n".join(l2_lines), l3,
        source="LocalDB + User Portfolio",
        timestamp="",
    )


def format_ai_advice_brand(question: str, answer: str, user_profile: dict, portfolio_summary: str = "") -> str:
    """فرمت پاسخ مشاور AI."""
    l1 = f"❓ سوال: {question}"
    l2 = f"🤖 پاسخ:\n{answer}"

    l3_parts = []
    if user_profile:
        l3_parts.append("📋 پروفایل شما:")
        l3_parts.append(f"  • ریسک: {user_profile.get('risk_profile', 'نامشخص')}")
        l3_parts.append(f"  • افق: {user_profile.get('horizon_months', 'نامشخص')} ماه")
        l3_parts.append(f"  • سرمایه: {float(user_profile.get('capital') or 0):,.0f}")

    if portfolio_summary:
        l3_parts.append(f"\n📁 پرتفوی:\n{portfolio_summary}")

    l3 = "\n".join(l3_parts)

    return build_brand_message(
        "مشاوره هوشمند",
        l1, l2, l3,
        source="AI Advisor + User Profile",
        timestamp="",
    )


def format_welcome_brand() -> str:
    """پیام خوش‌آمد."""
    return (
        f"سلام 👋\n"
        f"من {BRAND_NAME}‌ام.\n\n"
        f"اینجام تا کمک کنم صندوق‌های سرمایه‌گذاری ایران رو بهتر بشناسی\n"
        f"و قبل از تصمیم، تصویر روشن‌تری داشته باشی.\n\n"
        f"می‌تونی از همین‌جا وضعیت بازار رو ببینی،\n"
        f"یک صندوق رو بررسی کنی یا سبدت رو مدیریت کنی.\n\n"
        f"«هر تصمیم، شایسته آگاهی است.»"
    )


def format_help_brand() -> str:
    """راهنما."""
    return (
        f"سلام 👋\n"
        f"من {BRAND_NAME}‌ام.\n\n"
        f"اینجام تا کمک کنم صندوق‌های سرمایه‌گذاری ایران رو بهتر بشناسی،\n"
        f"با هم مقایسه‌شون کنی و آگاهانه‌تر تصمیم بگیری.\n\n"
        f"می‌تونی از من بخوای:\n\n"
        f"📊 وضعیت لحظه‌ای صندوق‌ها رو بررسی کنم\n"
        f"📅 تحلیل امروز بازار رو ببینی\n"
        f"🏆 برترین‌های امروز رو ببینی\n"
        f"⚠️ ضعیف‌ترین‌های امروز رو ببینی\n"
        f"🔎 یک صندوق رو تحلیل کنم\n"
        f"📁 سبدت رو مدیریت و تحلیل کنم\n"
        f"⭐ بهترین صندوق هر دسته رو ببینی\n"
        f"👤 پروفایلت رو بررسی کنی\n\n"
        f"من تصمیم رو به جای تو نمی‌گیرم.\n"
        f"کمکت می‌کنم اطلاعات رو بهتر ببینی.\n\n"
        f"«هر تصمیم، شایسته آگاهی است.»"
    )


def format_profile_brand(user: dict, portfolio_items: list[dict], prices: dict[str, float], join_days: int) -> str:
    """پروفایل کاربر."""
    total_value = sum(
        float(item.get("quantity") or 0) * prices.get(item["symbol"], 0)
        for item in portfolio_items
    )

    return build_brand_message(
        "پروفایل من",
        f"👤 پروفایل شما\n\n"
        f"خوشحالم که همراه {BRAND_NAME} هستی.\n\n"
        f"📁 ارزش فعلی سبد: {_fmt_money(total_value)}\n"
        f"🧺 تعداد صندوق‌ها: {len(portfolio_items)}\n"
        f"📊 تنوع سبد: {len(set(item.get('fund_type', '') for item in portfolio_items))} دسته\n"
        f"📅 مدت عضویت: {join_days} روز\n"
        f"🎯 افق سرمایه‌گذاری: {user.get('horizon_months', 'نامشخص')} ماه\n"
        f"⚖️ سطح ریسک: {user.get('risk_profile', 'نامشخص')}",
        "هر زمان بخوای می‌تونیم اطلاعات پروفایلت رو هم تغییر بدیم.",
        "",
        source="LocalDB",
        timestamp="",
    )