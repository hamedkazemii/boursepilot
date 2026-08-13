"""تولید توضیح فارسی «چرا این رتبه؟» جدا برای برتر و ضعیف."""

from __future__ import annotations

from typing import Literal

from core.scoring.models import FactorScore, FundAssessment

Kind = Literal["top", "worst", "neutral"]


def explain_fund(a: FundAssessment, *, kind: Kind = "neutral", max_items: int = 6) -> list[str]:
    """
    توضیح نقش‌محور:
    - top: تمرکز روی نقاط قوت + سیگنال‌های حمایتی
    - worst: تمرکز روی نقاط ضعف / ریسک‌ها (نه کپی توضیح برترها)
    - neutral: ترکیب متعادل
    """
    factors = list(a.factors or ())
    strong = sorted([f for f in factors if f.score >= 65], key=lambda f: f.score, reverse=True)
    weak = sorted([f for f in factors if f.score <= 45], key=lambda f: f.score)  # weakest first
    mid = sorted(
        [f for f in factors if 45 < f.score < 65],
        key=lambda f: abs(f.score - 50),
    )

    out: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        t = (text or "").strip()
        if not t or t in seen:
            return
        # حذف خطوط کلیشه‌ای امتیاز نهایی
        if t.startswith("امتیاز نهایی"):
            return
        if t.startswith("نقطه قوت") and kind == "worst":
            # در کارت ضعیف، strength خام را رد کن مگر بعداً به‌عنوان استثنا
            return
        seen.add(t)
        out.append(t)

    if kind == "worst":
        add(f"امتیاز نسبتاً پایین ({a.final_score:.1f}) و توصیه: {a.recommendation_label}")
        # اول ضعف‌های واقعی
        for f in weak[:3]:
            add(_factor_line(f, tone="weak"))
        # اگر فاکتور خیلی ضعیف نبود، پایین‌ترین‌ها را با ادبیات ریسک/ضعف نسبی بنویس
        if len(out) < 4:
            for f in sorted(factors, key=lambda x: x.score)[:3]:
                if f.score <= 55:
                    add(_factor_line(f, tone="weak"))
                else:
                    # حتی فاکتور متوسط/خوب را در کارت ضعیف به‌صورت «کافی نبودن برای رتبه بالا» بگو
                    detail = f.reasons[0] if f.reasons else f.label or f"{f.score:.0f}"
                    add(
                        f"نقطه ضعف نسبی — {f.title}: برای رتبه بالا کافی نیست "
                        f"({detail} / {f.score:.0f})"
                    )
        # سیگنال‌های بازار منفی
        if a.change_pct is not None and a.change_pct <= -0.5:
            add(f"بازده/تغییر روز منفی است ({a.change_pct:+.2f}%).")
        if a.change_pct is not None and a.change_pct <= -1.5:
            add("فشار فروش امروز نسبت به میانگین بازار پررنگ‌تر است.")
        if a.premium_pct is not None and _sane_premium(a.premium_pct) and a.premium_pct >= 1.0:
            add(f"حباب NAV بالاست ({a.premium_pct:+.2f}%) و جذابیت ورود کمتر است.")
        if a.premium_pct is not None and _sane_premium(a.premium_pct) and a.premium_pct <= -3.0:
            add(
                f"تخفیف زیاد نسبت به NAV ({a.premium_pct:+.2f}%) می‌تواند نشانه فشار فروش "
                "یا نگرانی بازار باشد."
            )
        # فقط یک قوت فرعی در انتها (برای انصاف)
        if strong:
            add(f"نکته مثبت محدود: {_factor_line(strong[0], tone='strong', bare=True)}")
        if not any("ضعف" in x or "ریسک" in x or "منفی" in x or "پایین" in x for x in out):
            add("ترکیب فاکتورها نسبت به سایر صندوق‌ها ضعیف‌تر ارزیابی شده است.")
    elif kind == "top":
        add(f"امتیاز بالا ({a.final_score:.1f}) و توصیه: {a.recommendation_label}")
        for f in strong[:3]:
            add(_factor_line(f, tone="strong"))
        if a.change_pct is not None and a.change_pct >= 0.8:
            add(f"مومنتوم روز مثبت است ({a.change_pct:+.2f}%).")
        if a.premium_pct is not None and _sane_premium(a.premium_pct) and a.premium_pct <= -0.5:
            add(f"با تخفیف نسبت به NAV معامله می‌شود ({a.premium_pct:+.2f}%).")
        # یک هشدار کوچک
        if weak:
            add(f"ریسک قابل‌توجه: {_factor_line(weak[0], tone='weak', bare=True)}")
        if len(out) < 3:
            for f in sorted(factors, key=lambda x: x.score, reverse=True)[:3]:
                add(_factor_line(f, tone="strong" if f.score >= 60 else "neutral"))
    else:
        for f in strong[:2]:
            add(_factor_line(f, tone="strong"))
        for f in weak[:2]:
            add(_factor_line(f, tone="weak"))
        for f in mid[:1]:
            add(_factor_line(f, tone="neutral"))

    # از summary_reasons فقط خطوط سازگار با kind
    for r in a.summary_reasons or ():
        if kind == "worst" and ("نقطه قوت" in r or "قوی" in r and "ضعف" not in r):
            continue
        if kind == "top" and r.startswith("نقطه ضعف"):
            # فقط اگر جا بود
            if len(out) >= max_items - 1:
                continue
        add(r)

    if not out:
        if kind == "worst":
            out.append("عملکرد نسبی این صندوق در ترکیب نقدشوندگی، جریان پول و مومنتوم ضعیف‌تر بوده است.")
        else:
            out.append("بر اساس ترکیب نقدشوندگی، جریان پول و مومنتوم امتیازدهی شده است.")

    return out[:max_items]


def _factor_line(f: FactorScore, *, tone: str, bare: bool = False) -> str:
    detail = ""
    if f.reasons:
        detail = f.reasons[0]
    elif f.label:
        detail = f"{f.label}"
    else:
        detail = f"امتیاز {f.score:.0f}"

    if bare:
        return f"{f.title}: {detail} ({f.score:.0f})"

    if tone == "strong":
        return f"نقطه قوت — {f.title}: {detail} ({f.score:.0f})"
    if tone == "weak":
        return f"نقطه ضعف — {f.title}: {detail} ({f.score:.0f})"
    return f"{f.title}: {detail} ({f.score:.0f})"


def _sane_premium(p: float) -> bool:
    """حباب‌های غیرواقعی (مثلاً -90٪ به‌خاطر واحد قیمت/NAV) را فیلتر کن."""
    return -25.0 <= float(p) <= 25.0
