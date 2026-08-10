"""Provider داده بازار از دیتابیس محلی (Sync Receiver).

این provider برای سرور خارجی (External) طراحی شده که داده‌ها را
از طریق Sync Worker دریافت و در SQLite ذخیره کرده است.
"""

from __future__ import annotations

import logging
from typing import Optional

from services.providers.base import MarketDataProvider
from services.providers.models import (
    NavData,
    OrderBookLevel,
    OrderBookSnapshot,
    ShareholderRow,
    SymbolQuote,
    MoneyFlowSnapshot,
)
from core.database.connection import get_database
from services.providers.textnorm import normalize_symbol

logger = logging.getLogger(__name__)


class LocalDBProvider:
    """Provider که داده‌ها را از دیتابیس محلی SQLite می‌خواند."""

    name = "localdb"

    def get_all_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        db = get_database()
        with db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT f.symbol, f.name, f.ins_code, f.isin, f.sector, f.sector_id,
                       h.close_price, h.last_price, h.volume, h.value,
                       h.change_pct, h.trade_count, h.bid_qty, h.ask_qty,
                       h.buy_real_volume, h.buy_legal_volume,
                       h.sell_real_volume, h.sell_legal_volume,
                       h.open_price, h.high_price, h.low_price, h.yesterday_price,
                       h.trade_date
                FROM history h
                JOIN funds f ON h.fund_id = f.id
                WHERE h.trade_date = (SELECT MAX(trade_date) FROM history)
                  AND f.is_active = 1
                """
            )
            rows = cursor.fetchall()

        quotes = []
        for row in rows:
            try:
                quote = self._row_to_quote(row)
                if quote:
                    quotes.append(quote)
            except Exception as exc:
                logger.warning("skip bad row: %s", exc)

        logger.info("LocalDBProvider total symbols=%s", len(quotes))
        return quotes

    def get_fund_symbols(self, symbol_type: Optional[int] = None) -> list[SymbolQuote]:
        all_quotes = self.get_all_symbols(symbol_type)
        funds = [q for q in all_quotes if q.is_fund_like]
        logger.info("LocalDBProvider fund-like=%s / total=%s", len(funds), len(all_quotes))
        return funds

    def get_symbol(self, symbol: str) -> SymbolQuote:
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ValueError("symbol خالی است")

        db = get_database()
        with db.transaction() as conn:
            cursor = conn.execute(
                """
                SELECT f.symbol, f.name, f.ins_code, f.isin, f.sector, f.sector_id,
                       h.close_price, h.last_price, h.volume, h.value,
                       h.change_pct, h.trade_count, h.bid_qty, h.ask_qty,
                       h.buy_real_volume, h.buy_legal_volume,
                       h.sell_real_volume, h.sell_legal_volume,
                       h.open_price, h.high_price, h.low_price, h.yesterday_price,
                       h.trade_date
                FROM history h
                JOIN funds f ON h.fund_id = f.id
                WHERE f.symbol = ?
                  AND h.trade_date = (SELECT MAX(trade_date) FROM history)
                """,
                (symbol_n,),
            )
            row = cursor.fetchone()

        if not row:
            raise ValueError(f"نماد پیدا نشد: {symbol_n}")

        return self._row_to_quote(row)

    def get_nav(self, symbol: str) -> NavData:
        """NAV از دیتابیس محلی — از nav_history یا history جدول می‌خواند."""
        symbol_n = normalize_symbol(symbol)
        if not symbol_n:
            raise ValueError("symbol خالی است")

        from core.database.connection import get_database
        db = get_database()
        try:
            with db.transaction() as conn:
                # 1) nav_history
                row = conn.execute(
                    """SELECT nh.issue_nav, nh.redeem_nav, nh.nav_date
                       FROM nav_history nh
                       JOIN funds f ON f.id = nh.fund_id
                       WHERE f.symbol = ?
                       ORDER BY nh.nav_date DESC LIMIT 1""",
                    (symbol_n,),
                ).fetchone()
                if row and (row["issue_nav"] or row["redeem_nav"]):
                    return NavData(
                        symbol=symbol_n,
                        issue_nav=row["issue_nav"],
                        redeem_nav=row["redeem_nav"],
                        date=row["nav_date"],
                        time=None,
                        raw={"source": "localdb.nav_history"},
                    )
                # 2) history (close_price به عنوان NAV تقریبی برای صندوق)
                row2 = conn.execute(
                    """SELECT h.close_price, h.trade_date
                       FROM history h
                       JOIN funds f ON f.id = h.fund_id
                       WHERE f.symbol = ? AND h.close_price IS NOT NULL
                       ORDER BY h.trade_date DESC LIMIT 1""",
                    (symbol_n,),
                ).fetchone()
                if row2 and row2["close_price"]:
                    return NavData(
                        symbol=symbol_n,
                        issue_nav=row2["close_price"],
                        redeem_nav=row2["close_price"],
                        date=row2["trade_date"],
                        time=None,
                        raw={"source": "localdb.history", "approx": True},
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("get_nav localdb failed for %s: %s", symbol_n, exc)

        return NavData(
            symbol=symbol_n,
            issue_nav=None,
            redeem_nav=None,
            date=None,
            time=None,
            raw={"source": "localdb", "note": "no nav data"},
        )

    def get_shareholders(self, symbol: str) -> list[ShareholderRow]:
        """سهامداران - فعلاً خالی برمی‌گرداند."""
        return []

    def _row_to_quote(self, row) -> Optional[SymbolQuote]:
        """تبدیل ردیف دیتابیس به SymbolQuote."""
        # Convert sqlite3.Row to dict
        row_dict = dict(row) if hasattr(row, "keys") else row
        
        # محاسبه is_fund_like از sector
        sector = row_dict.get("sector") or ""
        is_fund_like = "صندوق" in sector

        # Order book - convert to OrderBookLevel tuples
        bid_qty = row_dict.get("bid_qty") or 0
        ask_qty = row_dict.get("ask_qty") or 0
        bid_price = row_dict.get("close_price") or 0
        ask_price = row_dict.get("last_price") or 0

        bids = (OrderBookLevel(side="bid", level=1, price=bid_price, quantity=bid_qty, order_count=1),) if bid_qty > 0 else ()
        asks = (OrderBookLevel(side="ask", level=1, price=ask_price, quantity=ask_qty, order_count=1),) if ask_qty > 0 else ()

        orderbook = OrderBookSnapshot(bids=bids, asks=asks)

        # Money flow
        money_flow = MoneyFlowSnapshot(
            buy_real_volume=row_dict.get("buy_real_volume") or 0,
            buy_legal_volume=row_dict.get("buy_legal_volume") or 0,
            sell_real_volume=row_dict.get("sell_real_volume") or 0,
            sell_legal_volume=row_dict.get("sell_legal_volume") or 0,
            buy_real_count=0,
            buy_legal_count=0,
            sell_real_count=0,
            sell_legal_count=0,
        )

        return SymbolQuote(
            symbol=row_dict.get("symbol") or "",
            name=row_dict.get("name") or "",
            ins_code=row_dict.get("ins_code") or "",
            isin=row_dict.get("isin") or None,
            sector=row_dict.get("sector") or None,
            sector_id=row_dict.get("sector_id"),
            close_price=row_dict.get("close_price"),
            last_price=row_dict.get("last_price"),
            volume=row_dict.get("volume"),
            value=row_dict.get("value"),
            change_close_pct=row_dict.get("change_pct"),
            trade_count=row_dict.get("trade_count"),
            open_price=row_dict.get("open_price"),
            high=row_dict.get("high_price"),
            low=row_dict.get("low_price"),
            yesterday_price=row_dict.get("yesterday_price"),
            orderbook=orderbook,
            money_flow=money_flow,
            is_fund_like=is_fund_like,
            raw={"trade_date": row_dict.get("trade_date")},
        )