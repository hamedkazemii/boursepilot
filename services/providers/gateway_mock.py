"""Mock Market Gateway برای تست بدون دسترسی به سرور داخلی.

این Mock داده‌های واقعی‌مانند تولید می‌کند تا تمام تست‌های واحد بدون نیاز به سرور ایران اجرا شوند.
"""

from __future__ import annotations

from typing import Any

from services.providers.models import NavData, SymbolQuote


class MockMarketGateway:
    """Mock Gateway که داده‌های واقعی‌مانند برمی‌گرداند."""

    def __init__(self):
        self._symbols = self._make_symbols()
        self._navs = self._make_navs()

    def get_json(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        params = params or {}
        # Handle path parameter style: "symbol/عیار" or "symbol/یاقوت"
        if endpoint.startswith("symbol/"):
            sym = endpoint.split("/", 1)[1]
            for s in self._symbols:
                if s.symbol == sym:
                    return self._symbol_to_dict(s)
            return {"error": "not found"}
        if endpoint == "symbols":
            return [self._symbol_to_dict(s) for s in self._symbols]
        if endpoint == "symbol":
            sym = params.get("l18", "")
            for s in self._symbols:
                if s.symbol == sym:
                    return self._symbol_to_dict(s)
            return {"error": "not found"}
        if endpoint == "nav":
            sym = params.get("l18", "")
            nav = self._navs.get(sym)
            if nav:
                return {
                    "l18": sym,
                    "psubtran": nav.issue_nav,
                    "predtran": nav.redeem_nav,
                    **nav.raw,
                }
            return {"error": "not found"}
        if endpoint == "shareholders":
            return []
        return {"error": "unknown endpoint"}

    def _make_symbols(self) -> list[SymbolQuote]:
        return [
            SymbolQuote(
                symbol="عیار",
                name="صندوق سرمایه‌گذاری عیار",
                ins_code="123456",
                close_price=12500,
                last_price=12600,
                change_last=150,
                change_last_pct=1.2,
                volume=50000,
                value=625000000,
                trade_count=120,
                is_fund_like=True,
                sector="درآمد ثابت",
                raw={},
            ),
            SymbolQuote(
                symbol="یاقوت",
                name="صندوق یاقوت",
                ins_code="123457",
                close_price=3400,
                last_price=3450,
                change_last=71,
                change_last_pct=2.1,
                volume=120000,
                value=408000000,
                trade_count=250,
                is_fund_like=True,
                sector="سهامی",
                raw={},
            ),
            SymbolQuote(
                symbol="کاریزما",
                name="صندوق کاریزما",
                ins_code="123458",
                close_price=8900,
                last_price=8850,
                change_last=-45,
                change_last_pct=-0.5,
                volume=30000,
                value=267000000,
                trade_count=80,
                is_fund_like=True,
                sector="طلا",
                raw={},
            ),
            SymbolQuote(
                symbol="ذوب",
                name="سهام ذوب آهن",
                ins_code="123459",
                close_price=4500,
                last_price=4520,
                change_last=14,
                change_last_pct=0.3,
                volume=200000,
                value=900000000,
                trade_count=400,
                is_fund_like=False,
                sector="فلزات",
                raw={},
            ),
        ]

    def _make_navs(self) -> dict[str, NavData]:
        return {
            "عیار": NavData(
                symbol="عیار",
                issue_nav=12400,
                redeem_nav=12350,
                raw={"premium_pct": 1.6, "market_price": 12600},
            ),
            "یاقوت": NavData(
                symbol="یاقوت",
                issue_nav=3400,
                redeem_nav=3380,
                raw={"premium_pct": 1.5, "market_price": 3450},
            ),
        }

    @staticmethod
    def _symbol_to_dict(s: SymbolQuote) -> dict[str, Any]:
        return {
            "l18": s.symbol,
            "l30": s.name,
            "pc": s.close_price,
            "pl": s.last_price,
            "tno": s.trade_count,
            "tvol": s.volume,
            "tval": s.value,
            "py": s.yesterday_price,
            "pf": s.open_price,
            "pMax": s.high,
            "pMin": s.low,
            "eps": None,
            "pe": None,
            "sector": s.sector,
            "flow": s.board,
            "ztitad": None,
            "bvol": None,
        }
