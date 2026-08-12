"""
TabloKhaniEngine — تحلیل میکراستراکچر و عمق مظنه (Order Book Analysis).

این موتور جداسازی کامل FACT / ANALYSIS دارد:
- FACT: مشاهدات مستقیم از داده‌های خام (OrderBookSnapshot, MoneyFlowSnapshot, Transaction)
- ANALYSIS: تفسیر و استنتاج بر اساس FACTها با ارجاع (fact_refs)

هیچ تفسیری بدون evidence مجاز نیست.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from services.providers.models import OrderBookSnapshot, OrderBookLevel, MoneyFlowSnapshot, SymbolQuote
from services.providers.base import MarketDataProvider
from core.history.repository import HistoryRepository

logger = logging.getLogger(__name__)


class OrderBookPressure(str, Enum):
    """فشار مظنه"""
    STRONG_BUY = "strong_buy"       # تقاضا بسیار قوی
    BUY = "buy"                      # تقاضا قوی
    NEUTRAL = "neutral"              # متعادل
    SELL = "sell"                    # عرضه قوی
    STRONG_SELL = "strong_sell"      # عرضه بسیار قوی
    QUEUE_BUY = "queue_buy"          # صف خرید
    QUEUE_SELL = "queue_sell"        # صف فروش
    UNKNOWN = "unknown"              # نامشخص


class SpreadQuality(str, Enum):
    """کیفیت اسپرد"""
    TIGHT = "tight"                  # تنگ (خوب)
    NORMAL = "normal"                # معمولی
    WIDE = "wide"                    # پهن (بد)
    CROSSED = "crossed"              # تقاطع (نامعتبر)
    UNKNOWN = "unknown"              # نامشخص


class DepthQuality(str, Enum):
    """کیفیت عمق"""
    DEEP = "deep"                    # عمیق
    MODERATE = "moderate"            # متوسط
    SHALLOW = "shallow"              # سطحی
    UNKNOWN = "unknown"              # نامشخص


class MoneyFlowPressure(str, Enum):
    """فشار جریان پول"""
    REAL_BUY_DOMINANT = "real_buy_dominant"     # خریداران حقیقی غلبه
    LEGAL_BUY_DOMINANT = "legal_buy_dominant"   # خریداران حقوقی غلبه
    REAL_SELL_DOMINANT = "real_sell_dominant"   # فروشندگان حقیقی غلبه
    LEGAL_SELL_DOMINANT = "legal_sell_dominant" # فروشندگان حقوقی غلبه
    BALANCED = "balanced"                        # متعادل
    UNKNOWN = "unknown"                          # نامشخص


@dataclass
class Fact:
    """یک مشاهده مستقیم (FACT)"""
    name: str
    value: Any
    source: str  # "orderbook" | "money_flow" | "transaction" | "quote"
    timestamp: datetime
    confidence: float  # 0-1
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class Analysis:
    """یک تحلیل/تفسیر (ANALYSIS)"""
    name: str
    value: Any
    reasoning: str
    fact_refs: list[str]  # names of facts this analysis depends on
    confidence: float  # 0-1
    methodology_version: str = "v1"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "reasoning": self.reasoning,
            "fact_refs": self.fact_refs,
            "confidence": self.confidence,
            "methodology_version": self.methodology_version,
        }


@dataclass
class TabloKhaniReport:
    """گزارش کامل تحلیل تابلوخوانی"""
    symbol: str
    generated_at: datetime = field(default_factory=datetime.now)
    request_id: str = ""

    # Raw data
    orderbook: Optional[OrderBookSnapshot] = None
    money_flow: Optional[MoneyFlowSnapshot] = None
    quote: Optional[SymbolQuote] = None

    # FACT layer
    facts: list[Fact] = field(default_factory=list)

    # ANALYSIS layer
    analyses: list[Analysis] = field(default_factory=list)

    # Summary fields
    orderbook_pressure: OrderBookPressure = OrderBookPressure.UNKNOWN
    spread_quality: SpreadQuality = SpreadQuality.UNKNOWN
    depth_quality: DepthQuality = DepthQuality.UNKNOWN
    money_flow_pressure: MoneyFlowPressure = MoneyFlowPressure.UNKNOWN
    queue_status: str = "نامشخص"

    # Confidence
    overall_confidence: float = 0.0

    def add_fact(self, fact: Fact) -> None:
        self.facts.append(fact)

    def add_analysis(self, analysis: Analysis) -> None:
        self.analyses.append(analysis)

    def get_fact(self, name: str) -> Optional[Fact]:
        for f in self.facts:
            if f.name == name:
                return f
        return None

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "generated_at": self.generated_at.isoformat(),
            "request_id": self.request_id,
            "orderbook": self.orderbook.to_dict() if self.orderbook else None,
            "money_flow": self.money_flow.to_dict() if self.money_flow else None,
            "quote_price": self.quote.last_price if self.quote else None,
            "facts": [f.to_dict() for f in self.facts],
            "analyses": [a.to_dict() for a in self.analyses],
            "summary": {
                "orderbook_pressure": self.orderbook_pressure.value,
                "spread_quality": self.spread_quality.value,
                "depth_quality": self.depth_quality.value,
                "money_flow_pressure": self.money_flow_pressure.value,
                "queue_status": self.queue_status,
            },
            "overall_confidence": self.overall_confidence,
        }


class TabloKhaniEngine:
    """
    موتور تحلیل میکراستراکچر (تابلوخوانی).

    Flow:
    1. Fetch orderbook, money_flow, quote (live-first via DataQualityGate)
    2. Extract FACTs from raw data
    3. Run ANALYSIS on facts with fact_refs
    4. Produce TabloKhaniReport
    """

    def __init__(
        self,
        provider: Optional[MarketDataProvider] = None,
        repository: Optional[HistoryRepository] = None,
        data_quality_gate: Optional[Any] = None,
    ):
        self.provider = provider
        self.repository = repository
        self.data_quality_gate = data_quality_gate
        self._request_id = ""

    def analyze(
        self,
        symbol: str,
        *,
        request_id: Optional[str] = None,
        orderbook: Optional[OrderBookSnapshot] = None,
        money_flow: Optional[MoneyFlowSnapshot] = None,
        quote: Optional[SymbolQuote] = None,
    ) -> TabloKhaniReport:
        """
        تحلیل کامل تابلوخوانی برای یک نماد.

        Args:
            symbol: نماد صندوق
            request_id: شناسه درخواست برای Trace
            orderbook: سفارش‌نامه از پیش گرفته شده (اختیاری)
            money_flow: جریان پول از پیش گرفته شده (اختیاری)
            quote: نقل‌قول از پیش گرفته شده (اختیاری)

        Returns:
            TabloKhaniReport با FACTها و ANALYSISها
        """
        self._request_id = request_id or f"tk_{symbol}_{datetime.now().timestamp()}"
        logger.info(f"[{self._request_id}] TabloKhaniEngine analyze: {symbol}")

        report = TabloKhaniReport(symbol=symbol, request_id=self._request_id)

        # Store raw data
        report.orderbook = orderbook
        report.money_flow = money_flow
        report.quote = quote

        # 1. Extract FACTs
        self._extract_orderbook_facts(report)
        self._extract_money_flow_facts(report)
        self._extract_quote_facts(report)

        # 2. Run ANALYSIS
        self._analyze_orderbook_pressure(report)
        self._analyze_spread_quality(report)
        self._analyze_depth_quality(report)
        self._analyze_money_flow_pressure(report)
        self._analyze_queue_status(report)

        # 3. Calculate overall confidence
        self._calculate_confidence(report)

        logger.info(
            f"[{self._request_id}] TabloKhani result: "
            f"pressure={report.orderbook_pressure.value}, "
            f"spread={report.spread_quality.value}, "
            f"depth={report.depth_quality.value}, "
            f"mf={report.money_flow_pressure.value}, "
            f"conf={report.overall_confidence:.2f}"
        )
        return report

    # ================================================================
    # FACT Extraction
    # ================================================================

    def _extract_orderbook_facts(self, report: TabloKhaniReport) -> None:
        """استخراج FACTها از OrderBookSnapshot"""
        ob = report.orderbook
        if not ob:
            return

        now = datetime.now()

        # Best bid/ask
        if ob.best_bid:
            report.add_fact(Fact(
                name="best_bid_price",
                value=ob.best_bid.price,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
                metadata={"level": ob.best_bid.level},
            ))
            report.add_fact(Fact(
                name="best_bid_qty",
                value=ob.best_bid.quantity,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
            ))
            report.add_fact(Fact(
                name="best_bid_orders",
                value=ob.best_bid.order_count,
                source="orderbook",
                timestamp=now,
                confidence=0.9,
            ))

        if ob.best_ask:
            report.add_fact(Fact(
                name="best_ask_price",
                value=ob.best_ask.price,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
                metadata={"level": ob.best_ask.level},
            ))
            report.add_fact(Fact(
                name="best_ask_qty",
                value=ob.best_ask.quantity,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
            ))
            report.add_fact(Fact(
                name="best_ask_orders",
                value=ob.best_ask.order_count,
                source="orderbook",
                timestamp=now,
                confidence=0.9,
            ))

        # Total bid/ask
        report.add_fact(Fact(
            name="total_bid_qty",
            value=ob.total_bid_quantity,
            source="orderbook",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="total_ask_qty",
            value=ob.total_ask_quantity,
            source="orderbook",
            timestamp=now,
            confidence=0.9,
        ))

        # Depth: count of levels
        report.add_fact(Fact(
            name="bid_levels",
            value=len(ob.bids),
            source="orderbook",
            timestamp=now,
            confidence=1.0,
        ))
        report.add_fact(Fact(
            name="ask_levels",
            value=len(ob.asks),
            source="orderbook",
            timestamp=now,
            confidence=1.0,
        ))

        # Spread
        if ob.best_bid and ob.best_ask:
            spread = ob.best_ask.price - ob.best_bid.price
            mid = (ob.best_ask.price + ob.best_bid.price) / 2
            spread_pct = (spread / mid * 100) if mid > 0 else 0
            report.add_fact(Fact(
                name="spread",
                value=spread,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
            ))
            report.add_fact(Fact(
                name="spread_pct",
                value=spread_pct,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
            ))
            report.add_fact(Fact(
                name="mid_price",
                value=mid,
                source="orderbook",
                timestamp=now,
                confidence=0.95,
            ))

    def _extract_money_flow_facts(self, report: TabloKhaniReport) -> None:
        """استخراج FACTها از MoneyFlowSnapshot"""
        mf = report.money_flow
        if not mf:
            return

        now = datetime.now()

        report.add_fact(Fact(
            name="buy_real_vol",
            value=mf.buy_real_volume,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="buy_legal_vol",
            value=mf.buy_legal_volume,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="sell_real_vol",
            value=mf.sell_real_volume,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="sell_legal_vol",
            value=mf.sell_legal_volume,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="buy_real_cnt",
            value=mf.buy_real_count,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="buy_legal_cnt",
            value=mf.buy_legal_count,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="sell_real_cnt",
            value=mf.sell_real_count,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="sell_legal_cnt",
            value=mf.sell_legal_count,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))

        # Derived totals
        total_buy_vol = mf.buy_real_volume + mf.buy_legal_volume
        total_sell_vol = mf.sell_real_volume + mf.sell_legal_volume
        total_buy_cnt = mf.buy_real_count + mf.buy_legal_count
        total_sell_cnt = mf.sell_real_count + mf.sell_legal_count

        report.add_fact(Fact(
            name="total_buy_vol",
            value=total_buy_vol,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="total_sell_vol",
            value=total_sell_vol,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="total_buy_cnt",
            value=total_buy_cnt,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="total_sell_cnt",
            value=total_sell_cnt,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))

        # Net flow
        net_vol = total_buy_vol - total_sell_vol
        net_cnt = total_buy_cnt - total_sell_cnt
        report.add_fact(Fact(
            name="net_volume_flow",
            value=net_vol,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))
        report.add_fact(Fact(
            name="net_count_flow",
            value=net_cnt,
            source="money_flow",
            timestamp=now,
            confidence=0.9,
        ))

    def _extract_quote_facts(self, report: TabloKhaniReport) -> None:
        """استخراج FACTها از SymbolQuote (price, volume, etc.)"""
        q = report.quote
        if not q:
            return

        now = datetime.now()

        if q.last_price is not None:
            report.add_fact(Fact(
                name="last_price",
                value=q.last_price,
                source="quote",
                timestamp=now,
                confidence=0.95,
            ))
        if q.volume is not None:
            report.add_fact(Fact(
                name="volume",
                value=q.volume,
                source="quote",
                timestamp=now,
                confidence=0.9,
            ))
        if q.value is not None:
            report.add_fact(Fact(
                name="trade_value",
                value=q.value,
                source="quote",
                timestamp=now,
                confidence=0.9,
            ))
        if q.trade_count is not None:
            report.add_fact(Fact(
                name="trade_count",
                value=q.trade_count,
                source="quote",
                timestamp=now,
                confidence=0.9,
            ))
        if q.change_close_pct is not None:
            report.add_fact(Fact(
                name="change_close_pct",
                value=q.change_close_pct,
                source="quote",
                timestamp=now,
                confidence=0.9,
            ))

    # ================================================================
    # ANALYSIS Layer
    # ================================================================

    def _analyze_orderbook_pressure(self, report: TabloKhaniReport) -> None:
        """تحلیل فشار مظنه"""
        total_bid = report.get_fact("total_bid_qty")
        total_ask = report.get_fact("total_ask_qty")
        best_bid_qty = report.get_fact("best_bid_qty")
        best_ask_qty = report.get_fact("best_ask_qty")
        best_bid_orders = report.get_fact("best_bid_orders")
        best_ask_orders = report.get_fact("best_ask_orders")

        # If no orderbook data, mark as UNKNOWN and return
        if not (total_bid and total_ask):
            report.orderbook_pressure = OrderBookPressure.UNKNOWN
            report.add_analysis(Analysis(
                name="orderbook_pressure",
                value=report.orderbook_pressure.value,
                reasoning="داده مظنه موجود نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        fact_refs = []
        reasoning_parts = []

        fact_refs.extend(["total_bid_qty", "total_ask_qty"])
        bid = total_bid.value
        ask = total_ask.value
        total = bid + ask

        if total > 0:
            ratio = bid / total
            reasoning_parts.append(f"bid_ratio={ratio:.2f}")

            if ratio >= 0.75:
                report.orderbook_pressure = OrderBookPressure.STRONG_BUY
                reasoning_parts.append("فشار خرید قوی (bid >= 75%)")
            elif ratio >= 0.6:
                report.orderbook_pressure = OrderBookPressure.BUY
                reasoning_parts.append("فشار خرید (bid >= 60%)")
            elif ratio >= 0.4:
                report.orderbook_pressure = OrderBookPressure.NEUTRAL
                reasoning_parts.append("متعادل (bid 40-60%)")
            elif ratio >= 0.25:
                report.orderbook_pressure = OrderBookPressure.SELL
                reasoning_parts.append("فشار فروش (bid <= 40%)")
            else:
                report.orderbook_pressure = OrderBookPressure.STRONG_SELL
                reasoning_parts.append("فشار فروش قوی (bid <= 25%)")
        else:
            report.orderbook_pressure = OrderBookPressure.NEUTRAL
            reasoning_parts.append("بدون حجم در مظنه")

        # Check queue conditions
        queue_buy = best_ask_qty and best_ask_qty.value == 0
        queue_sell = best_bid_qty and best_bid_qty.value == 0

        if queue_buy and queue_sell:
            report.orderbook_pressure = OrderBookPressure.NEUTRAL
            reasoning_parts.append("هر دو صف (صف خرید و صف فروش)")
        elif queue_buy:
            report.orderbook_pressure = OrderBookPressure.QUEUE_BUY
            reasoning_parts.append("صف خرید")
        elif queue_sell:
            report.orderbook_pressure = OrderBookPressure.QUEUE_SELL
            reasoning_parts.append("صف فروش")

        report.add_analysis(Analysis(
            name="orderbook_pressure",
            value=report.orderbook_pressure.value,
            reasoning=" | ".join(reasoning_parts),
            fact_refs=fact_refs,
            confidence=0.85 if fact_refs else 0.3,
        ))

    def _analyze_spread_quality(self, report: TabloKhaniReport) -> None:
        """تحلیل کیفیت اسپرد"""
        spread_pct = report.get_fact("spread_pct")

        if not spread_pct:
            report.spread_quality = SpreadQuality.UNKNOWN
            report.add_analysis(Analysis(
                name="spread_quality",
                value=report.spread_quality.value,
                reasoning="داده اسپرد موجود نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        fact_refs = ["spread_pct"]
        reasoning_parts = []
        sp = spread_pct.value
        reasoning_parts.append(f"spread_pct={sp:.3f}%")

        if sp <= 0.1:
            report.spread_quality = SpreadQuality.TIGHT
            reasoning_parts.append("اسپرد بسیار تنگ (خوب)")
        elif sp <= 0.5:
            report.spread_quality = SpreadQuality.NORMAL
            reasoning_parts.append("اسپرد معمولی")
        elif sp <= 2.0:
            report.spread_quality = SpreadQuality.WIDE
            reasoning_parts.append("اسپرد پهن")
        else:
            report.spread_quality = SpreadQuality.CROSSED
            reasoning_parts.append("اسپرد تقاطع/نامعتبر")

        report.add_analysis(Analysis(
            name="spread_quality",
            value=report.spread_quality.value,
            reasoning=" | ".join(reasoning_parts),
            fact_refs=fact_refs,
            confidence=0.8,
        ))

    def _analyze_depth_quality(self, report: TabloKhaniReport) -> None:
        """تحلیل کیفیت عمق"""
        bid_levels = report.get_fact("bid_levels")
        ask_levels = report.get_fact("ask_levels")
        total_bid_qty = report.get_fact("total_bid_qty")
        total_ask_qty = report.get_fact("total_ask_qty")

        # If no orderbook data, mark as UNKNOWN and return
        if not (bid_levels or ask_levels):
            report.depth_quality = DepthQuality.UNKNOWN
            report.add_analysis(Analysis(
                name="depth_quality",
                value=report.depth_quality.value,
                reasoning="داده عمق مظنه موجود نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        fact_refs = []
        reasoning_parts = []

        total_levels = 0
        total_qty = 0.0

        if bid_levels:
            fact_refs.append("bid_levels")
            total_levels += bid_levels.value
        if ask_levels:
            fact_refs.append("ask_levels")
            total_levels += ask_levels.value
        if total_bid_qty:
            fact_refs.append("total_bid_qty")
            total_qty += total_bid_qty.value
        if total_ask_qty:
            fact_refs.append("total_ask_qty")
            total_qty += total_ask_qty.value

        reasoning_parts.append(f"levels={total_levels}, qty={total_qty:,.0f}")

        if total_levels >= 8 and total_qty > 100000:
            report.depth_quality = DepthQuality.DEEP
            reasoning_parts.append("عمق خوب (حداقل 8 سطح، حجم بالا)")
        elif total_levels >= 5 and total_qty > 50000:
            report.depth_quality = DepthQuality.MODERATE
            reasoning_parts.append("عمق متوسط")
        elif total_levels >= 2:
            report.depth_quality = DepthQuality.SHALLOW
            reasoning_parts.append("عمق سطحی")
        else:
            report.depth_quality = DepthQuality.UNKNOWN
            reasoning_parts.append("عمق نامشخص/ناموجود")

        report.add_analysis(Analysis(
            name="depth_quality",
            value=report.depth_quality.value,
            reasoning=" | ".join(reasoning_parts),
            fact_refs=fact_refs,
            confidence=0.8 if fact_refs else 0.2,
        ))

    def _analyze_money_flow_pressure(self, report: TabloKhaniReport) -> None:
        """تحلیل فشار جریان پول"""
        net_vol = report.get_fact("net_volume_flow")
        buy_real_vol = report.get_fact("buy_real_vol")
        buy_legal_vol = report.get_fact("buy_legal_vol")
        sell_real_vol = report.get_fact("sell_real_vol")
        sell_legal_vol = report.get_fact("sell_legal_vol")
        total_buy_vol = report.get_fact("total_buy_vol")
        total_sell_vol = report.get_fact("total_sell_vol")

        # If no money flow data, mark as UNKNOWN
        if not (buy_real_vol or buy_legal_vol or sell_real_vol or sell_legal_vol):
            report.money_flow_pressure = MoneyFlowPressure.UNKNOWN
            report.add_analysis(Analysis(
                name="money_flow_pressure",
                value=report.money_flow_pressure.value,
                reasoning="داده جریان پول موجود نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        fact_refs = []
        reasoning_parts = []

        if net_vol:
            fact_refs.append("net_volume_flow")
            nv = net_vol.value
            reasoning_parts.append(f"net_vol={nv:,.0f}")

        if total_buy_vol and total_sell_vol:
            fact_refs.extend(["total_buy_vol", "total_sell_vol"])
            tb = total_buy_vol.value
            ts = total_sell_vol.value
            total = tb + ts
            if total > 0:
                buy_ratio = tb / total
                reasoning_parts.append(f"buy_vol_ratio={buy_ratio:.2f}")

        # Determine dominant side
        real_buy = buy_real_vol.value if buy_real_vol else 0
        legal_buy = buy_legal_vol.value if buy_legal_vol else 0
        real_sell = sell_real_vol.value if sell_real_vol else 0
        legal_sell = sell_legal_vol.value if sell_legal_vol else 0

        if real_buy > real_sell and real_buy > legal_buy and real_buy > legal_sell:
            report.money_flow_pressure = MoneyFlowPressure.REAL_BUY_DOMINANT
            reasoning_parts.append("خریداران حقیقی غلبه")
        elif legal_buy > legal_sell and legal_buy > real_buy and legal_buy > real_sell:
            report.money_flow_pressure = MoneyFlowPressure.LEGAL_BUY_DOMINANT
            reasoning_parts.append("خریداران حقوقی غلبه")
        elif real_sell > real_buy and real_sell > legal_buy and real_sell > legal_sell:
            report.money_flow_pressure = MoneyFlowPressure.REAL_SELL_DOMINANT
            reasoning_parts.append("فروشندگان حقیقی غلبه")
        elif legal_sell > legal_buy and legal_sell > real_buy and legal_sell > real_sell:
            report.money_flow_pressure = MoneyFlowPressure.LEGAL_SELL_DOMINANT
            reasoning_parts.append("فروشندگان حقوقی غلبه")
        else:
            report.money_flow_pressure = MoneyFlowPressure.BALANCED
            reasoning_parts.append("متعادل")

        report.add_analysis(Analysis(
            name="money_flow_pressure",
            value=report.money_flow_pressure.value,
            reasoning=" | ".join(reasoning_parts),
            fact_refs=fact_refs,
            confidence=0.8 if fact_refs else 0.3,
        ))

    def _analyze_queue_status(self, report: TabloKhaniReport) -> None:
        """تحلیل وضعیت صف"""
        best_bid_qty = report.get_fact("best_bid_qty")
        best_ask_qty = report.get_fact("best_ask_qty")

        if not (best_bid_qty and best_ask_qty):
            report.queue_status = "نامشخص"
            report.add_analysis(Analysis(
                name="queue_status",
                value=report.queue_status,
                reasoning="داده صف موجود نیست",
                fact_refs=[],
                confidence=0.0,
            ))
            return

        fact_refs = []
        reasoning_parts = []

        queue_buy = best_ask_qty and best_ask_qty.value == 0
        queue_sell = best_bid_qty and best_bid_qty.value == 0

        if queue_buy:
            fact_refs.append("best_ask_qty")
            report.queue_status = "صف خرید"
            reasoning_parts.append("صف خرید (best_ask_qty == 0)")
        elif queue_sell:
            fact_refs.append("best_bid_qty")
            report.queue_status = "صف فروش"
            reasoning_parts.append("صف فروش (best_bid_qty == 0)")
        else:
            # Both have qty, no queue
            fact_refs.extend(["best_bid_qty", "best_ask_qty"])
            report.queue_status = "بدون صف"
            reasoning_parts.append("بدون صف")

        report.add_analysis(Analysis(
            name="queue_status",
            value=report.queue_status,
            reasoning=" | ".join(reasoning_parts),
            fact_refs=fact_refs,
            confidence=0.9 if fact_refs else 0.4,
        ))

    def _calculate_confidence(self, report: TabloKhaniReport) -> None:
        """محاسبه اطمینان کلی"""
        if not report.analyses:
            report.overall_confidence = 0.0
            return

        # Only average analyses with actual data (confidence > 0)
        confidences = [a.confidence for a in report.analyses if a.confidence > 0]
        if not confidences:
            report.overall_confidence = 0.0
            return

        report.overall_confidence = sum(confidences) / len(confidences)


# ================================================================
# Convenience function
# ================================================================

def analyze_tablo_khani(
    symbol: str,
    provider: BrsProvider,
    repository: Optional[HistoryRepository] = None,
    request_id: Optional[str] = None,
) -> TabloKhaniReport:
    """
    Helper برای تحلیل مستقیم با provider (fetch internal).

    Note: در معماری کامل باید از DataQualityGate عبور کند.
    این helper برای تست و استفاده ساده است.
    """
    engine = TabloKhaniEngine(provider=provider, repository=repository)
    # Fetch data - these methods may not exist on all provider implementations
    ob = getattr(provider, 'get_orderbook', lambda s: None)(symbol) if hasattr(provider, 'get_orderbook') else None
    mf = getattr(provider, 'get_money_flow', lambda s: None)(symbol) if hasattr(provider, 'get_money_flow') else None
    quote = provider.get_symbol(symbol)

    return engine.analyze(
        symbol,
        request_id=request_id,
        orderbook=ob,
        money_flow=mf,
        quote=quote,
    )