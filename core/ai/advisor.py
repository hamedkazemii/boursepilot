"""AI Advisor — پاسخ کارشناسی + حافظه یادگیری روزانه.

بدون کلید خارجی: موتور قوانین + حافظه SQLite.
اگر AI_API_URL/AI_API_KEY تنظیم شود از LLM سازگار با OpenAI استفاده می‌کند.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Optional

import requests

from core.database.connection import Database, get_database
from core.scoring.models import FundAssessment

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    if not s:
        return ""
    trans = str.maketrans({
        "ي": "ی",
        "ك": "ک",
        "ة": "ه",
        "‌": " ",
        "۰": "0", "۱": "1", "۲": "2", "۳": "3", "۴": "4",
        "۵": "5", "۶": "6", "۷": "7", "۸": "8", "۹": "9",
    })
    return " ".join(str(s).translate(trans).split())


class AIAdvisor:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()
        self.api_url = (os.getenv("AI_API_URL") or "").strip()
        self.api_key = (os.getenv("AI_API_KEY") or "").strip()
        self.model = (os.getenv("AI_MODEL") or "llama-3.1-8b-instant").strip()

    def remember(self, scope: str, key: str, value: Any, confidence: float = 0.6) -> None:
        now = _now()
        payload = json.dumps(value, ensure_ascii=False, default=str)
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO ai_memory(scope, key, value_json, confidence, hits, last_used_at, created_at, updated_at)
                VALUES (?,?,?,?,0,?,?,?)
                ON CONFLICT(scope, key) DO UPDATE SET
                    value_json=excluded.value_json,
                    confidence=MAX(ai_memory.confidence, excluded.confidence),
                    updated_at=excluded.updated_at,
                    hits=ai_memory.hits + 1,
                    last_used_at=excluded.last_used_at
                """,
                (scope, key, payload, confidence, now, now, now),
            )

    def recall(self, scope: str, key: str) -> Any:
        row = self.db.fetchone(
            "SELECT value_json FROM ai_memory WHERE scope = ? AND key = ?",
            (scope, key),
        )
        if not row:
            return None
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE ai_memory SET hits = hits + 1, last_used_at = ? WHERE scope = ? AND key = ?",
                (_now(), scope, key),
            )
        try:
            return json.loads(row["value_json"])
        except Exception:
            return row["value_json"]

    def add_lesson(self, topic: str, content: str, *, source: str = "daily_review", quality: float = 0.6) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO ai_lessons(lesson_date, topic, content, source, quality, created_at)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    datetime.now().astimezone().date().isoformat(),
                    topic,
                    content,
                    source,
                    quality,
                    _now(),
                ),
            )

    def learn_from_ranking(self, ranked: list[FundAssessment], market: Optional[dict[str, Any]] = None) -> list[str]:
        lessons: list[str] = []
        if not ranked:
            return lessons
        top = ranked[:5]
        worst = list(reversed(ranked[-5:]))
        top_types: dict[str, int] = {}
        for a in top:
            top_types[a.fund_type] = top_types.get(a.fund_type, 0) + 1
        best_group = max(top_types, key=top_types.get) if top_types else "-"
        lesson1 = (
            f"امروز گروه غالب در برترین‌ها «{best_group}» بود. "
            f"میانگین امتیاز ۵ برتر: {_avg([a.final_score for a in top]):.1f} و ۵ ضعیف: {_avg([a.final_score for a in worst]):.1f}."
        )
        lessons.append(lesson1)
        self.add_lesson("market_regime", lesson1, quality=0.7)
        self.remember("global", "last_best_group", best_group, 0.7)
        self.remember("global", "last_top_symbols", [a.symbol for a in top], 0.7)
        for a in top[:3]:
            self.remember(
                f"fund:{a.symbol}",
                "last_strength",
                {"score": a.final_score, "reasons": list(a.summary_reasons[:3])},
                0.65,
            )
        for a in worst[:3]:
            self.remember(
                f"fund:{a.symbol}",
                "last_weakness",
                {"score": a.final_score, "reasons": list(a.summary_reasons[:3])},
                0.65,
            )
        if market:
            self.remember("global", "last_market", market, 0.6)
            lessons.append(f"وضعیت بازار: {market.get('market_status')} | قدرت {market.get('market_power')}")
        return lessons

    def answer(
        self,
        question: str,
        *,
        user: Optional[dict[str, Any]] = None,
        ranked: Optional[list[FundAssessment]] = None,
        portfolio_text: str = "",
    ) -> str:
        q = (question or "").strip()
        if not q:
            return "سوال خالی است."
        context = self._build_context(user=user, ranked=ranked, portfolio_text=portfolio_text)
        if self.api_url and self.api_key:
            try:
                return self._llm_answer(q, context)
            except Exception as exc:  # noqa: BLE001
                logger.warning("llm failed, fallback rules: %s", exc)
        return self._rule_answer(q, context, ranked=ranked or [], user=user)

    def _build_context(
        self,
        *,
        user: Optional[dict[str, Any]],
        ranked: Optional[list[FundAssessment]],
        portfolio_text: str,
    ) -> str:
        parts = ["تو تحلیل‌گر حرفه‌ای صندوق‌های ETF ایران برای محصول صندوقچی هستی."]
        lessons = self.db.fetchall("SELECT topic, content FROM ai_lessons ORDER BY id DESC LIMIT 8")
        if lessons:
            parts.append("درس‌های اخیر:")
            for r in lessons:
                parts.append(f"- {r['topic']}: {r['content']}")
        best = self.recall("global", "last_best_group")
        if best:
            parts.append(f"آخرین گروه غالب: {best}")
        if ranked:
            parts.append("۵ برتر فعلی: " + ", ".join(f"{a.symbol}({a.final_score:.0f})" for a in ranked[:5]))
            parts.append(
                "۵ ضعیف فعلی: "
                + ", ".join(f"{a.symbol}({a.final_score:.0f})" for a in list(reversed(ranked[-5:])))
            )
        if user:
            parts.append(
                f"کاربر risk={user.get('risk_profile')} horizon={user.get('horizon_months')}m capital={user.get('capital')}"
            )
        if portfolio_text:
            parts.append("پرتفوی:\n" + portfolio_text)
        return "\n".join(parts)

    def _llm_answer(self, question: str, context: str) -> str:
        url = self.api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url = url + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": context + "\nپاسخ کوتاه، فارسی، عملی و با ریسک‌هشدار."},
                {"role": "user", "content": question},
            ],
            "temperature": 0.4,
            "max_tokens": 700,
        }
        r = requests.post(url, headers=headers, json=body, timeout=45)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

    def _rule_answer(
        self,
        q: str,
        context: str,
        *,
        ranked: list[FundAssessment],
        user: Optional[dict[str, Any]],
    ) -> str:
        nq = _norm(q)
        risk = (user or {}).get("risk_profile") or "medium"
        capital = float((user or {}).get("capital") or 0)

        alloc_keys = [
            "پرتفو", "پیشنهاد", "تخصیص", "بخرم", "سرمایه", "میلیون", "میلیارد",
            "پس انداز", "افق", "ماهه", "ساله", "دارم",
        ]
        is_alloc = any(k in nq for k in alloc_keys) or (
            "ریسک" in nq and any(x in nq for x in ["کم", "متوسط", "زیاد", "بالا"])
        )
        if is_alloc:
            m = re.search(r"(\d+[\d,]*)\s*(میلیون|میلیارد)?", nq)
            if m and capital <= 0:
                num = float(m.group(1).replace(",", ""))
                if m.group(2) == "میلیون":
                    num *= 1_000_000
                elif m.group(2) == "میلیارد":
                    num *= 1_000_000_000
                capital = num
            if "کم" in nq:
                risk = "low"
            elif "زیاد" in nq or "بالا" in nq:
                risk = "high"
            elif "متوسط" in nq:
                risk = "medium"
            return self._allocate(risk=risk, capital=capital, ranked=ranked)

        if any(k in nq for k in ["برتر", "بهترین", "top"]):
            if not ranked:
                return "هنوز رنکینگ آماده‌ی امروز نیست. /today را بزنید."
            lines = ["🏆 پیشنهادهای برتر امروز (بر اساس روند+نسبی):"]
            for a in ranked[:5]:
                lines.append(f"• {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
                if a.summary_reasons:
                    lines.append(
                        f"  - {a.summary_reasons[1] if len(a.summary_reasons) > 1 else a.summary_reasons[0]}"
                    )
            lines.append("این پیشنهاد جایگزین مشاوره‌ی شخصی نیست؛ ریسک بازار را در نظر بگیرید.")
            return "\n".join(lines)

        if any(k in nq for k in ["ضعیف", "خطر", "نخر", "worst"]):
            if not ranked:
                return "رنکینگ آماده نیست."
            lines = ["⚠️ صندوق‌های ضعیف‌تر امروز:"]
            for a in list(reversed(ranked[-5:])):
                lines.append(f"• {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}")
                if a.summary_reasons:
                    lines.append(
                        f"  - {a.summary_reasons[1] if len(a.summary_reasons) > 1 else a.summary_reasons[0]}"
                    )
            return "\n".join(lines)

        if ranked:
            for a in ranked:
                if a.symbol in q or a.symbol in nq or (a.name and (a.name in q or _norm(a.name) in nq)):
                    lines = [
                        f"📌 تحلیل {a.symbol}",
                        f"امتیاز نسبی: {a.final_score:.1f} | توصیه: {a.recommendation_label}",
                        f"نوع: {a.fund_type}",
                        "دلایل:",
                    ]
                    for rsn in a.summary_reasons[:5]:
                        lines.append(f"• {rsn}")
                    return "\n".join(lines)

        if any(k in nq for k in ["بازار", "امروز", "وضعیت"]):
            best = self.recall("global", "last_best_group") or "-"
            mkt = self.recall("global", "last_market") or {}
            return (
                f"وضعیت بازار: {mkt.get('market_status', 'نامشخص')}\n"
                f"قدرت: {mkt.get('market_power', '-')}\n"
                f"گروه غالب اخیر: {best}\n"
                "برای جزئیات /today یا /market را بزنید."
            )

        return (
            "می‌توانم کمک کنم درباره:\n"
            "• پیشنهاد پرتفو بر اساس ریسک\n"
            "• برترین/ضعیف‌ترین صندوق‌ها\n"
            "• تحلیل یک نماد\n"
            "• وضعیت بازار\n\n"
            "مثال: «۵۰ میلیون ریسک کم یک‌ساله» یا «تحلیل عیار»"
        )

    def _allocate(self, *, risk: str, capital: float, ranked: list[FundAssessment]) -> str:
        risk = (risk or "medium").lower()
        if risk in {"کم", "low", "conservative"}:
            risk = "low"
        elif risk in {"زیاد", "high", "aggressive"}:
            risk = "high"
        else:
            risk = "medium"

        if risk == "low":
            mix = [("درآمد ثابت", 0.55), ("طلا", 0.30), ("سهامی", 0.15)]
        elif risk == "high":
            mix = [("سهامی", 0.40), ("اهرم", 0.20), ("طلا", 0.25), ("درآمد ثابت", 0.15)]
        else:
            mix = [("طلا", 0.30), ("درآمد ثابت", 0.35), ("سهامی", 0.35)]

        lines = ["🧠 پیشنهاد تخصیص (قائم بر ریسک و رنکینگ روندی):", f"پروفایل ریسک: {risk}"]
        if capital > 0:
            lines.append(f"سرمایه: {capital:,.0f} ریال")
        lines.append("")
        for group, w in mix:
            amt = capital * w if capital > 0 else None
            pick = next((a for a in ranked if group in (a.fund_type or "") and a.final_score >= 55), None)
            if pick is None:
                pick = next((a for a in ranked if group in (a.fund_type or "")), None)
            if amt is not None:
                lines.append(f"• {group}: {w*100:.0f}% ≈ {amt:,.0f}" + (f" → {pick.symbol}" if pick else ""))
            else:
                lines.append(f"• {group}: {w*100:.0f}%" + (f" → {pick.symbol}" if pick else ""))
        lines.append("")
        lines.append("منطق: ترکیب امنیت نقدینگی + روند نسبی گروه‌ها. بازبینی ماهانه توصیه می‌شود.")
        self.add_lesson("allocation", f"risk={risk} mix={mix}", quality=0.55)
        return "\n".join(lines)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _avg(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0
