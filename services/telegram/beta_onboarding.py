"""سیستم آنبوردینگ بتا — سؤالات اولیه کاربر جدید."""

from __future__ import annotations

from typing import Any


# سوالات آنبوردینگ به ترتیب
ONBOARDING_STEPS = [
    {
        "key": "experience",
        "question": "📊 چقدر با بازار آشنا هستید؟",
        "options": [
            ("beginner", "🟢 تازه‌کار — اولین باره"),
            ("intermediate", "🟡 متوسط — چندبار خریدم"),
            ("advanced", "🔵 حرفه‌ای — فعال بازارم"),
        ],
    },
    {
        "key": "risk",
        "question": "⚖️ تحمل ریسکتون چقدره؟",
        "options": [
            ("low", "🟢 کم — اصل سرمایه برام مهمه"),
            ("medium", "🟡 متوسط — کمی نوسان قبول دارم"),
            ("high", "🔵 زیاد — بالا/پایین مشکلی نیست"),
        ],
    },
    {
        "key": "horizon",
        "question": "⏳ افق سرمایه‌گذاری‌تون چقدره؟",
        "options": [
            ("3", "🟢 کوتاه‌مدت — ۳ ماه"),
            ("6", "🟡 میان‌مدت — ۶ ماه"),
            ("12", "🔵 بلندمدت — ۱ سال یا بیشتر"),
        ],
    },
    {
        "key": "capital",
        "question": "💰 حدود سرمایه‌تون چقدره؟ (تومان)",
        "input": True,
        "placeholder": "مثال: ۵۰۰۰۰۰۰۰ یا ۵۰ میلیون",
    },
]


def onboarding_keyboard(step_index: int) -> dict[str, Any] | None:
    if step_index >= len(ONBOARDING_STEPS):
        return None
    step = ONBOARDING_STEPS[step_index]
    if step.get("input"):
        return None  # متنی منتظر می‌مونه
    rows = []
    for value, label in step["options"]:
        rows.append([{"text": label, "callback_data": f"onboard:{step['key']}:{value}"}])
    return {"inline_keyboard": rows}


def onboarding_question(step_index: int) -> str:
    if step_index >= len(ONBOARDING_STEPS):
        return "✅ تنظیمات شما کامل شد!"
    step = ONBOARDING_STEPS[step_index]
    progress = "━" * step_index + "●" + ("─" * (len(ONBOARDING_STEPS) - step_index - 1))
    steps_done = step_index + 1
    total = len(ONBOARDING_STEPS)
    return (
        f"{step['question']}\n\n"
        f"مرحله {steps_done} از {total}\n"
        f"{progress}"
    )


def parse_onboarding_response(data: str) -> tuple[str, str] | None:
    """.Parse callback like 'onboard:risk:low' → ('risk', 'low')."""
    if not data.startswith("onboard:"):
        return None
    parts = data.split(":")
    if len(parts) != 3:
        return None
    return parts[1], parts[2]


def onboarding_complete_message(name: str = "سرمایه‌گذار") -> str:
    return (
        f"🎉 خوش آمدید {name} \n\n"
        "پروفایل شما کامل شد! از طریق منوی زیر می‌تونید:\n"
        "• تحلیل روزانه بازار ببینید 📊\n"
        "• صندوق‌های برتر پیدا کنید 🏆\n"
        "• پرتفوی خودتون رو بسازید 📁\n"
        "• از مشاور هوشمند بپرسید 🤖\n\n"
        "هر وقت خواستید سوال بپرسید، کافیه تایپ کنید!"
    )
