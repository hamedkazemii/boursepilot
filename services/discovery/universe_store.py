"""
Fund Universe Central Access — Single Source of Truth.

این ماژول دسترسی متمرکز به Universe صندوق‌ها را فراهم می‌کند.
تمام بخش‌های سیستم (ranking, scoring, reports, backfill, NAV, CODAL, portfolio, telegram)
باید از `get_valid_fund_universe()` استفاده کنند.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from core.database.connection import Database, get_database
from services.discovery.fund_universe import FundUniverseBuilder, FundUniverseEntry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidFund:
    """صندوق معتبر برای استفاده در تمام تحلیل‌ها."""
    symbol: str
    name: str
    isin: Optional[str]
    ins_code: Optional[str]
    cs: str
    cs_id: int
    cs_sub: Optional[str]
    cs_sub_id: Optional[int]
    board: Optional[str]
    board_id: Optional[int]
    shares: Optional[int]
    market_value: Optional[int]
    last_price: Optional[float]
    close_price: Optional[float]
    yesterday_price: Optional[float]
    nav_issue: Optional[float]
    nav_redeem: Optional[float]
    
    @property
    def unique_key(self) -> str:
        if self.isin:
            return f"ISIN:{self.isin}"
        if self.ins_code:
            return f"INS:{self.ins_code}"
        return f"SYM:{self.symbol}"


class FundUniverseStore:
    """
    ذخیره و بازیابی Universe از DB.
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db or get_database()
    
    def save_universe(self, universe: list[FundUniverseEntry]) -> int:
        """ذخیره Universe در DB."""
        if not universe:
            logger.warning("Empty universe, nothing to save")
            return 0
        
        synced_at = datetime.now(timezone.utc).isoformat()
        saved = 0
        
        with self.db.transaction() as conn:
            for entry in universe:
                # Skip if no ISIN (can't dedupe properly)
                if not entry.isin:
                    logger.warning(f"Skipping fund without ISIN: {entry.symbol}")
                    continue
                
                conn.execute("""
                    INSERT INTO fund_universe (
                        symbol, name, isin, ins_code, cs, cs_id,
                        cs_sub, cs_sub_id, board, board_id,
                        shares, market_value, last_price, close_price,
                        yesterday_price, nav_issue, nav_redeem,
                        is_active, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(isin) DO UPDATE SET
                        symbol=excluded.symbol,
                        name=excluded.name,
                        ins_code=excluded.ins_code,
                        cs=excluded.cs,
                        cs_id=excluded.cs_id,
                        cs_sub=excluded.cs_sub,
                        cs_sub_id=excluded.cs_sub_id,
                        board=excluded.board,
                        board_id=excluded.board_id,
                        shares=excluded.shares,
                        market_value=excluded.market_value,
                        last_price=excluded.last_price,
                        close_price=excluded.close_price,
                        yesterday_price=excluded.yesterday_price,
                        nav_issue=excluded.nav_issue,
                        nav_redeem=excluded.nav_redeem,
                        is_active=1,
                        synced_at=excluded.synced_at
                """, (
                    entry.symbol, entry.name, entry.isin, entry.ins_code,
                    entry.cs, entry.cs_id, entry.cs_sub, entry.cs_sub_id,
                    entry.board, entry.board_id, entry.shares, entry.market_value,
                    entry.last_price, entry.close_price, entry.yesterday_price,
                    entry.nav_issue, entry.nav_redeem, synced_at
                ))
                saved += 1
        
        logger.info(f"Saved {saved} funds to fund_universe table")
        return saved
    
    def load_universe(self, active_only: bool = True) -> list[ValidFund]:
        """بارگذاری Universe از DB."""
        query = """
            SELECT symbol, name, isin, ins_code, cs, cs_id,
                   cs_sub, cs_sub_id, board, board_id,
                   shares, market_value, last_price, close_price,
                   yesterday_price, nav_issue, nav_redeem
            FROM fund_universe
        """
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY symbol"
        
        with self.db.transaction() as conn:
            rows = conn.execute(query).fetchall()
        
        universe = []
        for row in rows:
            universe.append(ValidFund(
                symbol=row["symbol"],
                name=row["name"],
                isin=row["isin"],
                ins_code=row["ins_code"],
                cs=row["cs"],
                cs_id=row["cs_id"],
                cs_sub=row["cs_sub"],
                cs_sub_id=row["cs_sub_id"],
                board=row["board"],
                board_id=row["board_id"],
                shares=row["shares"],
                market_value=row["market_value"],
                last_price=row["last_price"],
                close_price=row["close_price"],
                yesterday_price=row["yesterday_price"],
                nav_issue=row["nav_issue"],
                nav_redeem=row["nav_redeem"],
            ))
        
        logger.info(f"Loaded {len(universe)} funds from fund_universe")
        return universe
    
    def get_symbols(self, active_only: bool = True) -> list[str]:
        """لیست نمادهای صندوق‌های معتبر."""
        query = "SELECT symbol FROM fund_universe"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY symbol"
        
        with self.db.transaction() as conn:
            rows = conn.execute(query).fetchall()
        return [r["symbol"] for r in rows]
    
    def get_fund_by_symbol(self, symbol: str) -> Optional[ValidFund]:
        """دریافت یک صندوق با نماد."""
        query = """
            SELECT symbol, name, isin, ins_code, cs, cs_id,
                   cs_sub, cs_sub_id, board, board_id,
                   shares, market_value, last_price, close_price,
                   yesterday_price, nav_issue, nav_redeem
            FROM fund_universe
            WHERE symbol = ? AND is_active = 1
        """
        with self.db.transaction() as conn:
            row = conn.execute(query, (symbol,)).fetchone()
        
        if not row:
            return None
        
        return ValidFund(
            symbol=row["symbol"],
            name=row["name"],
            isin=row["isin"],
            ins_code=row["ins_code"],
            cs=row["cs"],
            cs_id=row["cs_id"],
            cs_sub=row["cs_sub"],
            cs_sub_id=row["cs_sub_id"],
            board=row["board"],
            board_id=row["board_id"],
            shares=row["shares"],
            market_value=row["market_value"],
            last_price=row["last_price"],
            close_price=row["close_price"],
            yesterday_price=row["yesterday_price"],
            nav_issue=row["nav_issue"],
            nav_redeem=row["nav_redeem"],
        )
    
    def get_fund_by_isin(self, isin: str) -> Optional[ValidFund]:
        """دریافت یک صندوق با ISIN."""
        query = """
            SELECT symbol, name, isin, ins_code, cs, cs_id,
                   cs_sub, cs_sub_id, board, board_id,
                   shares, market_value, last_price, close_price,
                   yesterday_price, nav_issue, nav_redeem
            FROM fund_universe
            WHERE isin = ? AND is_active = 1
        """
        with self.db.transaction() as conn:
            row = conn.execute(query, (isin,)).fetchone()
        
        if not row:
            return None
        
        return ValidFund(
            symbol=row["symbol"],
            name=row["name"],
            isin=row["isin"],
            ins_code=row["ins_code"],
            cs=row["cs"],
            cs_id=row["cs_id"],
            cs_sub=row["cs_sub"],
            cs_sub_id=row["cs_sub_id"],
            board=row["board"],
            board_id=row["board_id"],
            shares=row["shares"],
            market_value=row["market_value"],
            last_price=row["last_price"],
            close_price=row["close_price"],
            yesterday_price=row["yesterday_price"],
            nav_issue=row["nav_issue"],
            nav_redeem=row["nav_redeem"],
        )
    
    def deactivate_missing(self, current_isins: set[str]) -> int:
        """غیرفعال کردن صندوق‌هایی که در Universe جدید نیستند."""
        if not current_isins:
            return 0
        
        placeholders = ",".join("?" * len(current_isins))
        query = f"""
            UPDATE fund_universe
            SET is_active = 0
            WHERE is_active = 1 AND isin NOT IN ({placeholders})
        """
        with self.db.transaction() as conn:
            cursor = conn.execute(query, list(current_isins))
            return cursor.rowcount


# Global instance (lazy)
_universe_store: Optional[FundUniverseStore] = None


def get_universe_store() -> FundUniverseStore:
    """دریافت instance سراسری FundUniverseStore."""
    global _universe_store
    if _universe_store is None:
        _universe_store = FundUniverseStore()
    return _universe_store


def sync_fund_universe() -> tuple[int, dict]:
    """
    همگام‌سازی کامل Universe از BRS.
    Returns: (saved_count, stats)
    """
    logger.info("Starting fund universe sync from BRS...")
    builder = FundUniverseBuilder()
    universe = builder.get_universe()
    stats = builder.get_stats()
    
    store = get_universe_store()
    saved = store.save_universe(universe)
    
    # Deactivate funds no longer in BRS
    current_isins = {u.isin for u in universe if u.isin}
    deactivated = store.deactivate_missing(current_isins)
    if deactivated:
        logger.info(f"Deactivated {deactivated} funds no longer in BRS universe")
    
    return saved, stats


def get_valid_fund_universe(refresh: bool = False) -> list[ValidFund]:
    """
    توابع مرکزی واحد برای دریافت Universe معتبر صندوق‌ها.
    
    این تابع باید در تمام بخش‌های سیستم استفاده شود:
    - ranking
    - scoring
    - reports
    - history backfill
    - candlestick sync
    - NAV
    - CODAL
    - portfolio analysis
    - market reports
    
    Args:
        refresh: اگر True باشد، از BRS مجدداً sync می‌کند
    
    Returns:
        لیست ValidFundهای معتبر (cs_id=68)
    """
    store = get_universe_store()
    
    if refresh:
        sync_fund_universe()
    
    return store.load_universe(active_only=True)


def get_valid_fund_symbols(refresh: bool = False) -> list[str]:
    """لیست نمادهای صندوق‌های معتبر."""
    if refresh:
        sync_fund_universe()
    return get_universe_store().get_symbols(active_only=True)


def get_valid_fund(symbol: str, refresh: bool = False) -> Optional[ValidFund]:
    """دریافت یک صندوق معتبر با نماد."""
    if refresh:
        sync_fund_universe()
    return get_universe_store().get_fund_by_symbol(symbol)


def is_valid_fund(symbol: str, refresh: bool = False) -> bool:
    """بررسی اینکه آیا نماد در Universe معتبر است."""
    return get_valid_fund(symbol, refresh) is not None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test sync
    print("=== Syncing Universe ===")
    saved, stats = sync_fund_universe()
    print(f"Saved: {saved}")
    print(f"Stats: {stats}")
    
    # Test load
    print("\n=== Loading Universe ===")
    universe = get_valid_fund_universe()
    print(f"Total valid funds: {len(universe)}")
    for u in universe[:10]:
        print(f"  {u.symbol} | {u.name[:40]} | ISIN={u.isin}")
    print("...")
    
    # Test lookup
    print("\n=== Lookup Tests ===")
    for sym in ["عیار", "توان", "سرو", "فیروزه", "کوثری"]:
        fund = get_valid_fund(sym)
        if fund:
            print(f"  {sym}: OK - {fund.name[:30]}")
        else:
            print(f"  {sym}: NOT FOUND")