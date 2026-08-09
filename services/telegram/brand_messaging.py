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
        return build_brand_message("خانه", "داده‌ای برای نمایش وجود ندارد.", disclaimer="")

    up = sum(1 for a in ranked if _chg(a) > 0)
    down = sum(1 for a in ranked if _chg(a) < 0)
    market_power = ranked[0].final_score if ranked else 0

    # tendencia globale
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
        f"📊 وضعیت بازار\n"
        f"قدرت بازار: {market_power:.0f}/100\n"
        f"روند کلی: {trend_label}\n"
        f"صندوق‌های صعودی: {up} | نزولی: {down}"
    )

    l2_lines = ["🏆 امروز"]
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


def format_market_brief_brand(ranked, meta: Optional[dict] = None, session: Any = None) -> str:
    """فرمت گزارش صبحانه بازار."""
    meta = meta or {}
    n = len(ranked)
    if n == 0:
        return build_brand_message("صبحانه بازار", "داده‌ای برای تحلیل موجود نیست.", disclaimer="")

    up = sum(1 for a in ranked if _chg(a) > 0)
    down = sum(1 for a in ranked if _chg(a) < 0)
    avg_change = sum(_chg(a) for a in ranked) / n

    from collections import defaultdict
    group_scores: dict[str, list[float]] = defaultdict(list)
    for a in ranked:
        ft = a.fund_type or "نامشخص"
        group_scores[ft].append(a.final_score)

    group_avg = {k: sum(v) / len(v) for k, v in group_scores.items()}
    best_group = max(group_avg, key=group_avg.get) if group_avg else "—"
    worst_group = min(group_avg, key=group_avg.get) if group_avg else "—"

    # جلسه بازار
    session_line = ""
    if session is not None:
        label = getattr(session, "label", "")
        if label:
            session_line = f"🕐 جلسه: {label}\n"

    l1 = (
        f"{session_line}📈 {n} صندوق تحلیل‌شده | قدرت بازار: {ranked[0].final_score:.0f}/۱۰۰\n"
        f"🟢 {up} صعود | 🔴 {down} نزول | میانگین تغییر: {avg_change:+.2f}%\n"
        f"🏆 بهترین گروه: {best_group} ({group_avg.get(best_group, 0):.1f}) | "
        f"⚠️ ضعیف‌ترین: {worst_group} ({group_avg.get(worst_group, 0):.1f})"
    )

    # Layer 2: برترین/ضعیف‌ترین (بدون طلا/درآمد ثابت در رنکینگ کلی)
    from core.market.taxonomy import FundCategory, get_category_config
    general = [a for a in ranked if not get_category_config(_category_from_label(a.fund_type)).exclude_from_general_top5]
    top3 = general[:3] if len(general) >= 3 else ranked[:3]
    worst3 = list(reversed(ranked[-3:])) if len(ranked) >= 3 else list(reversed(ranked))

    l2_lines = ["🏆 پتانسیل بالا (امروز):"]
    for i, a in enumerate(top3, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2_lines.append("\n⚠️ وضعیت نیازمند بررسی:")
    for i, a in enumerate(worst3, 1):
        l2_lines.append(f"  {i}. {a.symbol} — {a.final_score:.1f} | {a.recommendation_label} | {a.fund_type}")

    l2 = "\n".join(l2_lines)

    l3 = ""
    portfolio_summary = meta.get("user_profile") or meta.get("portfolio_summary") or ""
    if portfolio_summary:
        l3 = f"📁 پرتفوی شما:\n{portfolio_summary}"

    source = meta.get("source", "LocalDB")
    timestamp = meta.get("timestamp", "")

    return build_brand_message(
        "صبحانه بازار",
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
        f"{assessment.symbol} — {assessment.name or ''}",
        assessment.final_score,
        assessment.recommendation,
        _chg(assessment),
    )

    l2_parts = []

    nav = _nav(assessment)
    if nav:
        l2_parts.append("💰 قیمت و NAV:")
        price = assessment.close_price or assessment.last_price
        if price:
            l2_parts.append(f"  • قیمت بازار: {price:,.0f}")
        l2_parts.append(f"  • NAV: {nav:,.0f}")
        if assessment.premium_pct is not None:
            l2_parts.append(f"  • پرمیوم/دیسکانت: {assessment.premium_pct:+.1f}%")
        else:
            l2_parts.append("  • پرمیوم/دیسکانت: نامشخص (NAV ابطال در دسترس نیست)")

    ind = _ind(assessment)
    ind_items = []
    if ind.get("rsi14") is not None:
        ind_items.append(f"RSI: {ind['rsi14']:.0f}")
    if ind.get("macd_signal") is not None:
        ind_items.append(f"MACD: {ind['macd_signal']:.2f}")
    if ind.get("ema20") is not None:
        ema_state = "بالای EMA20" if ind.get("extras", {}).get("above_ema20") else "زیر EMA20"
        ind_items.append(f"EMA20: {ind['ema20']:.0f} ({ema_state})")
    if ind.get("volatility_20") is not None:
        ind_items.append(f"Vol20: {ind['volatility_20']:.1f}%")
    if ind.get("volume_ratio") is not None:
        ind_items.append(f"Vol Ratio: {ind['volume_ratio']:.2f}")
    if ind_items:
        l2_parts.append("\n📈 اندیکاتورها:")
        l2_parts.append("  " + " | ".join(ind_items))

    adv = _adv(assessment)
    ratios = adv.get("ratios") or {}
    adv_items = []
    for key, label in (
        ("sharpe_ratio", "Sharpe"),
        ("sortino_ratio", "Sortino"),
        ("calmar_ratio", "Calmar"),
        ("omega_ratio", "Omega"),
        ("information_ratio", "Info Ratio"),
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
    if ratios.get("tail_ratio") is not None:
        tail = _sanitize_ratio(ratios.get("tail_ratio"), max_abs=20.0)
        if tail is not None:
            adv_items.append(f"Tail Ratio: {tail:.2f}")
    if ratios.get("upside_capture") is not None:
        up_cap = _sanitize_ratio(ratios.get("upside_capture"), max_abs=500.0)
        if up_cap is not None:
            adv_items.append(f"Upside: {up_cap:.1f}%")
    if ratios.get("downside_capture") is not None:
        dn_cap = _sanitize_ratio(ratios.get("downside_capture"), max_abs=500.0)
        if dn_cap is not None:
            adv_items.append(f"Downside: {dn_cap:.1f}%")
    if adv_items:
        l2_parts.append("\n🔬 متریک‌های پیشرفته:")
        l2_parts.append("  " + " | ".join(adv_items))

    fm = adv.get("factor_models") or {}
    fm_items = []
    if isinstance(fm, dict):
        for key, label in (("fama_french_3", "Fama-French 3F"), ("carhart_4", "Carhart 4F")):
            model = fm.get(key) if isinstance(fm.get(key), dict) else None
            if model and model.get("alpha") is not None:
                fm_items.append(f"{label} α: {model['alpha']:+.2f}%")
    if fm_items:
        l2_parts.append("\n📊 فاکتور مدل‌ها:")
        l2_parts.append("  " + " | ".join(fm_items))

    l2 = "\n".join(l2_parts)

    l3_parts = []

    l3_parts.append(f"📊 مقایسه دسته ({config.label}):")
    l3_parts.append(f"  • رتبه: {assessment.rank or '—'}")

    l3_parts.append("\n🧠 توضیح ساده:")
    l3_parts.append(f"  {_generate_explanation(assessment, config)}")

    limitations = _generate_limitations(assessment, config)
    if limitations:
        l3_parts.append("\n⚠️ محدودیت‌ها:")
        for lim in limitations:
            l3_parts.append(f"  • {lim}")

    l3 = "\n".join(l3_parts)

    source = "BRS Gateway → LocalDB"
    _ext = getattr(assessment, "extras", None)
    timestamp = str(_ext.get("time", "")) if isinstance(_ext, dict) else ""

    return build_brand_message(
        f"تحلیل عمیق: {assessment.symbol}",
        l1, l2, l3,
        source=source,
        timestamp=timestamp,
    )


def _generate_explanation(assessment, config) -> str:
    """تولید توضیح ساده بر اساس امتیاز و فاکتورها (Iran Market First)."""
    parts = []

    chg = _chg(assessment)
    if chg > 1:
        parts.append("روند صعودی قوی در روز.")
    elif chg > 0:
        parts.append("روند صعودی ملایم.")
    elif chg < -1:
        parts.append("روند نزولی قابل‌توجه.")
    else:
        parts.append("روند خنثی/نوسانی.")

    ind = _ind(assessment)
    if ind.get("rsi14") is not None:
        rsi = ind["rsi14"]
        if rsi > 70:
            parts.append("اشباع خرید (RSI بالا) — احتمال اصلاح.")
        elif rsi < 30:
            parts.append("اشباع فروش (RSI پایین) — احتمال بازگشت.")

    adv = _adv(assessment)
    ratios = adv.get("ratios") or {}
    if ratios.get("sharpe_ratio") is not None:
        sr = ratios["sharpe_ratio"]
        if sr > 1:
            parts.append("بازده تعدیل‌شده با ریسک خوب (Sharpe مثبت).")
        elif sr < -0.5:
            parts.append("بازده تعدیل‌شده با ریسک ضعیف.")

    if config.key.value == "gold" and assessment.premium_pct is not None:
        if assessment.premium_pct > 3:
            parts.append("پرمیوم بالای NAV — ریسک اصلاح قیمت بازار.")
        elif assessment.premium_pct < -2:
            parts.append("تخفیف نسبت به NAV — فرصت نسبی.")

    if not parts:
        parts.append("داده کافی برای توضیح دقیق نیست.")

    return " ".join(parts)


def _generate_limitations(assessment, config) -> list[str]:
    """محدودیت‌های تحلیل بر اساس دسته و داده."""
    limitations = []

    ind = _ind(assessment)
    bars = ind.get("bars") or 0
    if bars < 30:
        limitations.append(f"فقط {bars} روز داده — تحلیل‌های آماری محدود.")

    adv = _adv(assessment)
    fm = adv.get("factor_models") or {}
    if isinstance(fm, dict) and fm.get("error"):
        limitations.append(f"مدل فاکتوری: {fm['error']}")

    if config.key.value == "leverage":
        limitations.append("صندوق‌های اهرمی ریسک بالایی دارند؛ مناسب سرمایه‌گذاران پرریسک.")

    return limitations


def format_portfolio_brand(portfolio_items, prices: dict, user_profile: dict, ranked=None) -> str:
    """فرمت تحلیل پرتفوی برند-سازگار."""
    if not portfolio_items:
        return build_brand_message(
            "پرتفوی شما",
            "پرتفوی خالی است. با /pf_add صندوق اضافه کنید.",
            disclaimer="",
        )

    total_value = sum(item["quantity"] * prices.get(item["symbol"], 0) for item in portfolio_items)
    total_cost = sum(item["quantity"] * (item["avg_cost"] or 0) for item in portfolio_items)
    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0

    l1 = (
        f"💰 ارزش: {total_value:,.0f} | سرمایه: {total_cost:,.0f} | "
        f"سود/زیان: {pnl:+,.0f} ({pnl_pct:+.1f}%)"
    )

    l2_lines = ["📊 ترکیب پرتفوی:"]
    for item in portfolio_items:
        sym = item["symbol"]
        qty = item["quantity"]
        cost = item["avg_cost"] or 0
        price = prices.get(sym, 0)
        val = qty * price
        weight = (val / total_value * 100) if total_value > 0 else 0
        item_pnl_pct = ((price - cost) / cost * 100) if cost > 0 else 0

        rec_emoji = "🟢" if item_pnl_pct > 2 else "🟡" if item_pnl_pct > -2 else "🔴"
        l2_lines.append(f"  {rec_emoji} {sym}: {weight:.0f}% | {item_pnl_pct:+.1f}% | qty={qty:,}")

    l2 = "\n".join(l2_lines)

    l3_lines = ["🔍 تحلیل ریسک:"]

    max_weight = max((item["quantity"] * prices.get(item["symbol"], 0) / total_value * 100) for item in portfolio_items) if total_value > 0 else 0
    if max_weight > 40:
        l3_lines.append(f"  ⚠️ تمرکز بالا: {max_weight:.0f}% در یک صندوق")

    from core.market.taxonomy import classify_fund_category
    categories = {}
    for item in portfolio_items:
        cat = classify_fund_category(item.get("name", ""), item["symbol"])
        val = item["quantity"] * prices.get(item["symbol"], 0)
        categories[cat] = categories.get(cat, 0) + val

    if len(categories) < 3:
        l3_lines.append(f"  ⚠️ تنوع محدود: فقط {len(categories)} دسته")

    l3_lines.append("\n💡 پیشنهادات:")
    risk = user_profile.get("risk_profile", "medium")
    if risk == "low":
        leverage_val = categories.get("leverage", 0)
        if leverage_val > total_value * 0.1:
            l3_lines.append("  • ریسک کم: کاهش صندوق‌های اهرمی به <۱۰٪")
    elif risk == "high":
        fixed_val = categories.get("fixed_income", 0)
        if fixed_val > total_value * 0.4:
            l3_lines.append("  • ریسک بالا: کاهش درآمد ثابت به <۴۰٪ برای رشد بیشتر")

    l3 = "\n".join(l3_lines)

    return build_brand_message(
        "تحلیل پرتفوی",
        l1, l2, l3,
        source="LocalDB + User Profile",
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
        "مشاور هوشمند",
        l1, l2, l3,
        source="AI Advisor + Market Data",
        disclaimer="این پاسخ کمکی برای تصمیم‌گیری شماست، نهایی نیست.",
    )