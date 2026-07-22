"""تحلیل وضعیت پیش‌سفارش / عمق برای بازه ۸:۴۵–۹:۰۰."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional

from core.factors.common import safe_div
from services.providers.models import SymbolQuote


@dataclass(frozen=True)
class PreopenSignal:
    symbol: str
    name: str
    fund_type: str
    bid_qty: float
    ask_qty: float
    ratio: float
    bias: str  # buy_pressure|sell_pressure|balanced|buy_queue|sell_queue
    bias_label: str
    score: float
    reasons: tuple[str, ...]
    best_bid: Optional[float]
    best_ask: Optional[float]
    change_pct: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PreopenAnalyzer:
    """رتبه‌بندی فشار پیش‌سفارش بدون نیاز به ساعت سیستم (ساعت را scheduler تعیین می‌کند)."""

    def analyze_quote(self, quote: SymbolQuote, fund_type: str = "") -> PreopenSignal:
        bid = float(quote.orderbook.total_bid_quantity or 0.0)
        ask = float(quote.orderbook.total_ask_quantity or 0.0)
        ratio = safe_div(bid, max(ask, 1.0), default=1.0)
        bb = quote.orderbook.best_bid.price if quote.orderbook.best_bid else None
        ba = quote.orderbook.best_ask.price if quote.orderbook.best_ask else None

        if ask <= 0 and bid > 0:
            bias, bias_label, score = "buy_queue", "صف خرید / عرضه صفر", 95.0
        elif bid <= 0 and ask > 0:
            bias, bias_label, score = "sell_queue", "صف فروش / تقاضا صفر", 10.0
        elif ratio >= 3:
            bias, bias_label, score = "buy_pressure", "فشار خرید قوی", 88.0
        elif ratio >= 1.5:
            bias, bias_label, score = "buy_pressure", "فشار خرید", 72.0
        elif ratio <= 0.33:
            bias, bias_label, score = "sell_pressure", "فشار فروش قوی", 18.0
        elif ratio < 0.9:
            bias, bias_label, score = "sell_pressure", "فشار فروش", 35.0
        else:
            bias, bias_label, score = "balanced", "تعادل نسبی", 55.0

        reasons = [
            bias_label,
            f"نسبت تقاضا/عرضه پنج‌سطحی: {ratio:.2f}",
            f"حجم تقاضا: {bid:,.0f} | حجم عرضه: {ask:,.0f}",
        ]
        return PreopenSignal(
            symbol=quote.symbol,
            name=quote.name,
            fund_type=fund_type,
            bid_qty=bid,
            ask_qty=ask,
            ratio=round(ratio, 4),
            bias=bias,
            bias_label=bias_label,
            score=score,
            reasons=tuple(reasons),
            best_bid=bb,
            best_ask=ba,
            change_pct=quote.change_close_pct if quote.change_close_pct is not None else quote.change_last_pct,
        )

    def rank(self, quotes: list[SymbolQuote], fund_types: Optional[dict[str, str]] = None) -> list[PreopenSignal]:
        fund_types = fund_types or {}
        signals = [self.analyze_quote(q, fund_types.get(q.symbol, "")) for q in quotes]
        return sorted(signals, key=lambda s: s.score, reverse=True)

    def to_report(self, signals: list[PreopenSignal], top_n: int = 15) -> str:
        now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
        lines = [
            "🔔 گزارش پیش‌سفارش صندوق‌ها",
            "=" * 44,
            f"زمان: {now}",
            f"تعداد: {len(signals)}",
            "",
            "داغ‌ترین فشار خرید",
            "-" * 44,
        ]
        buys = [s for s in signals if s.bias in {"buy_pressure", "buy_queue"}][:top_n]
        sells = [s for s in signals if s.bias in {"sell_pressure", "sell_queue"}]
        sells = sorted(sells, key=lambda s: s.score)[: min(10, len(sells))]

        for i, s in enumerate(buys, 1):
            lines.append(f"{i}) {s.symbol} | {s.bias_label} | ratio={s.ratio:.2f}")
            lines.append(f"   {s.reasons[2]}")
        lines.append("")
        lines.append("فشار فروش / ریسک")
        lines.append("-" * 44)
        for i, s in enumerate(sells, 1):
            lines.append(f"{i}) {s.symbol} | {s.bias_label} | ratio={s.ratio:.2f}")
        return "\n".join(lines).strip() + "\n"
