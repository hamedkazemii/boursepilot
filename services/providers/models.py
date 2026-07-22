"""
مدل‌های استاندارد داده بازار برای صندوقچی.

همه providerها باید خروجی خود را به این DTOها نگاشت کنند
تا هسته تحلیل به فرمت خام BRS/TSETMC وابسته نباشد.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class OrderBookLevel:
    """یک سطح از عمق مظنه."""

    side: str  # "bid" | "ask"
    level: int  # 1..5
    price: float
    quantity: float
    order_count: int


@dataclass(frozen=True)
class OrderBookSnapshot:
    """۵ سطح عرضه و تقاضا."""

    bids: tuple[OrderBookLevel, ...] = ()
    asks: tuple[OrderBookLevel, ...] = ()

    @property
    def best_bid(self) -> Optional[OrderBookLevel]:
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[OrderBookLevel]:
        return self.asks[0] if self.asks else None

    @property
    def total_bid_quantity(self) -> float:
        return float(sum(x.quantity for x in self.bids))

    @property
    def total_ask_quantity(self) -> float:
        return float(sum(x.quantity for x in self.asks))

    def to_dict(self) -> dict[str, Any]:
        return {
            "bids": [asdict(x) for x in self.bids],
            "asks": [asdict(x) for x in self.asks],
            "total_bid_quantity": self.total_bid_quantity,
            "total_ask_quantity": self.total_ask_quantity,
        }


@dataclass(frozen=True)
class MoneyFlowSnapshot:
    """جریان حقیقی / حقوقی."""

    buy_real_count: int = 0
    buy_legal_count: int = 0
    sell_real_count: int = 0
    sell_legal_count: int = 0
    buy_real_volume: float = 0.0
    buy_legal_volume: float = 0.0
    sell_real_volume: float = 0.0
    sell_legal_volume: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NavData:
    """خالص ارزش دارایی (NAV) صندوق."""

    symbol: str
    issue_nav: Optional[float]
    redeem_nav: Optional[float]
    date: Optional[str] = None
    time: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "issue_nav": self.issue_nav,
            "redeem_nav": self.redeem_nav,
            "date": self.date,
            "time": self.time,
        }


@dataclass(frozen=True)
class SymbolQuote:
    """نقل‌قول استاندارد یک نماد / صندوق."""

    symbol: str
    name: str
    ins_code: str
    isin: Optional[str] = None
    sector: Optional[str] = None
    sector_id: Optional[int] = None
    board: Optional[str] = None
    state: Optional[str] = None

    last_price: Optional[float] = None
    close_price: Optional[float] = None
    yesterday_price: Optional[float] = None
    open_price: Optional[float] = None
    change_last: Optional[float] = None
    change_last_pct: Optional[float] = None
    change_close: Optional[float] = None
    change_close_pct: Optional[float] = None

    volume: Optional[float] = None
    value: Optional[float] = None
    trade_count: Optional[int] = None
    avg_volume_1m: Optional[float] = None

    low: Optional[float] = None
    high: Optional[float] = None
    threshold_min: Optional[float] = None
    threshold_max: Optional[float] = None

    market_value: Optional[float] = None
    shares: Optional[float] = None

    time: Optional[str] = None
    date: Optional[str] = None

    orderbook: OrderBookSnapshot = field(default_factory=OrderBookSnapshot)
    money_flow: MoneyFlowSnapshot = field(default_factory=MoneyFlowSnapshot)

    is_fund_like: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # raw ممکن است بزرگ باشد؛ در خروجی استاندارد نگه می‌داریم ولی caller می‌تواند حذف کند
        data["orderbook"] = self.orderbook.to_dict()
        data["money_flow"] = self.money_flow.to_dict()
        return data


@dataclass(frozen=True)
class ShareholderRow:
    """یک ردیف سهامدار عمده."""

    name: str
    volume: float
    percent: float
    change: float = 0.0
    shareholder_id: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
