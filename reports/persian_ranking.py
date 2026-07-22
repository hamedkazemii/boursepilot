"""گزارش فارسی رنکینگ صندوق‌ها با توضیح."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from config import settings
from core.ranking.fund_ranker import FundRanker
from core.scoring.models import FundAssessment


class PersianRankingReport:
    def generate(
        self,
        ranked: list[FundAssessment],
        meta: Optional[dict[str, Any]] = None,
        top_n: int = 15,
        worst_n: int = 8,
    ) -> str:
        meta = meta or {}
        ranker = FundRanker()
        top = ranker.top(ranked, top_n)
        worst = ranker.worst(ranked, worst_n)
        by_type = ranker.by_type(ranked)

        now = meta.get("generated_at") or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
        lines: list[str] = []
        lines.append(f"📊 گزارش رنکینگ {settings.PRODUCT_NAME}")
        lines.append("=" * 44)
        lines.append(f"زمان: {now}")
        lines.append(f"تعداد صندوق‌های بررسی‌شده: {len(ranked)}")
        if meta.get("fetch_nav"):
            lines.append(f"NAV موفق: {meta.get('nav_success', 0)}")
        lines.append("")

        lines.append("🏆 برترین صندوق‌ها")
        lines.append("-" * 44)
        for a in top:
            lines.extend(self._fund_block(a, short=True))
            lines.append("")

        lines.append("⚠️ ضعیف‌ترین‌ها")
        lines.append("-" * 44)
        for a in worst:
            lines.append(
                f"{a.rank}) {a.symbol} | {a.final_score:.1f} | {a.recommendation_label}"
            )
            if a.summary_reasons:
                lines.append(f"   دلیل: {a.summary_reasons[0]}")
        lines.append("")

        lines.append("📁 برترین هر نوع")
        lines.append("-" * 44)
        for ftype, items in sorted(by_type.items(), key=lambda kv: -len(kv[1])):
            if not items:
                continue
            best = items[0]
            lines.append(
                f"• {ftype} ({len(items)}): {best.symbol} — {best.final_score:.1f} ({best.recommendation_label})"
            )

        lines.append("")
        lines.append("ℹ️ هر امتیاز بر اساس نقدشوندگی، پیش‌سفارش، جریان پول، مومنتوم، حجم/ارزش و NAV ساخته شده است.")
        return "\n".join(lines).strip() + "\n"

    def _fund_block(self, a: FundAssessment, short: bool = False) -> list[str]:
        lines = [
            f"{a.rank}) {a.symbol} — {a.name}",
            f"   نوع: {a.fund_type} | امتیاز: {a.final_score:.1f} | توصیه: {a.recommendation_label}",
        ]
        chg = f"{a.change_pct:.2f}%" if a.change_pct is not None else "-"
        lines.append(f"   تغییر: {chg} | حجم: {self._fmt(a.volume)} | ارزش: {self._fmt(a.value)}")
        if a.premium_pct is not None:
            lines.append(f"   حباب/تخفیف NAV: {a.premium_pct:.2f}%")
        # reasons
        for r in a.summary_reasons[:3]:
            lines.append(f"   • {r}")
        if not short:
            for f in a.factors:
                if f.reasons:
                    lines.append(f"   – {f.title}: {f.score:.0f} | {f.reasons[0]}")
        return lines

    @staticmethod
    def _fmt(v: Any) -> str:
        if v is None:
            return "-"
        try:
            return f"{float(v):,.0f}"
        except Exception:
            return str(v)
