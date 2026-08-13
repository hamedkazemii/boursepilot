"""
History Backfill Job — پر کردن تاریخچه صندوق‌ها از BRS Candlestick.php

این job روی سرور ایران (Collector) اجرا می‌شود:
- Candlestick.php?type=3 برای دریافت تاریخچه قیمتی روزانه تعدیل‌شده (open, high, low, close, volume)
- History.php type=1 برگرداننده آمار معاملات (buy/sell) است، نه تاریخچه قیمتی
- برای صندوق‌هایی که history < 250 روز دارند
- اجرای روزانه در cron شبانه
- داده جعلی/مصنوعی تولید نمی‌کند - فقط داده واقعی BRS
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from core.database.connection import get_database
from services.discovery.universe_store import get_universe_store, ValidFund
from services.providers.brs_provider import BrsProvider
from services.providers.factory import get_market_data_provider

logger = logging.getLogger(__name__)


class HistoryBackfillJob:
    """
    پر کردن تاریخچه صندوق‌ها از BRS Candlestick API.
    
    استراتژی:
    1. پیدا کردن صندوق‌هایی با تاریخچه کمتر از min_days (از fund_universe)
    2. برای هر صندوق، درخواست Candlestick.php?type=3 (روزانه تعدیل‌شده)
    3. Upsert به جدول history
    4. گزارش تعداد روزهای اضافه شده
    """
    
    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        min_history_days: int = 250,  # حداقل ۲۵۰ روز برای ۱ سال
        max_funds_per_run: int = 50,  # محدودیت در هر اجرا برای quota
        db_path: Optional[str] = None,
    ):
        self.provider = provider or BrsProvider()
        self.min_history_days = min_history_days
        self.max_funds_per_run = max_funds_per_run
        self.db = get_database(db_path)
        self.universe_store = get_universe_store()
    
    def run(self) -> dict:
        """اجرای job و بازگرداندن آمار."""
        started = datetime.now()
        stats = {
            "started_at": started.isoformat(),
            "funds_checked": 0,
            "funds_backfilled": 0,
            "total_days_added": 0,
            "errors": [],
            "quota_report": {},
        }
        
        # 1. پیدا کردن صندوق‌های کم‌تاریخچه از fund_universe
        funds_needing_history = self._find_funds_needing_history()
        stats["funds_checked"] = len(funds_needing_history)
        
        if not funds_needing_history:
            logger.info("All funds have sufficient history (>= %d days)", self.min_history_days)
            stats["finished_at"] = datetime.now().isoformat()
            return stats
        
        # محدودیت تعداد در هر اجرا
        funds_to_process = funds_needing_history[:self.max_funds_per_run]
        logger.info("Backfilling history for %d/%d funds", len(funds_to_process), len(funds_needing_history))
        
        # 2. برای هر صندوق، دریافت و ذخیره تاریخچه
        for fund in funds_to_process:
            try:
                days_added = self._backfill_fund_history(fund)
                if days_added > 0:
                    stats["funds_backfilled"] += 1
                    stats["total_days_added"] += days_added
                    logger.info("Backfilled %d days for %s", days_added, fund["symbol"])
            except Exception as e:
                error_msg = f"Failed to backfill {fund['symbol']}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # 3. گزارش quota
        if hasattr(self.provider, "get_quota_report"):
            stats["quota_report"] = self.provider.get_quota_report()
        
        stats["finished_at"] = datetime.now().isoformat()
        stats["duration_seconds"] = (datetime.now() - started).total_seconds()
        
        logger.info(
            "HistoryBackfillJob done: checked=%d backfilled=%d days_added=%d errors=%d",
            stats["funds_checked"], stats["funds_backfilled"], stats["total_days_added"], len(stats["errors"])
        )
        return stats
    
    def _find_funds_needing_history(self) -> list[dict]:
        """پیدا کردن صندوق‌هایی که تاریخچه کمتر از min_history_days روز دارند."""
        # دریافت تمام صندوق‌های معتبر از fund_universe
        universe = self.universe_store.load_universe(active_only=True)
        
        result = []
        for fund in universe:
            fund_id = self._get_fund_id_from_funds_table(fund.symbol)
            if not fund_id:
                # صندوق در جدول قدیمی funds وجود ندارد، skip
                logger.debug("Fund %s not in old funds table, skipping", fund.symbol)
                continue
            
            with self.db.transaction() as conn:
                row = conn.execute("""
                    SELECT COUNT(h.id) as history_count,
                           MIN(h.trade_date) as oldest_date,
                           MAX(h.trade_date) as newest_date
                    FROM history h
                    WHERE h.fund_id = ?
                """, (fund_id,)).fetchone()
            
            history_count = row["history_count"] if row else 0
            oldest_date = row["oldest_date"] if row else None
            newest_date = row["newest_date"] if row else None
            
            if history_count < self.min_history_days:
                result.append({
                    "fund_id": fund_id,
                    "symbol": fund.symbol,
                    "name": fund.name,
                    "history_count": history_count,
                    "oldest_date": oldest_date,
                    "newest_date": newest_date,
                })
        
        # Sort by history_count ascending (least history first)
        result.sort(key=lambda x: x["history_count"])
        return result
    
    def _get_fund_id_from_funds_table(self, symbol: str) -> Optional[int]:
        """دریافت fund_id از جدول قدیمی funds برای نماد داده شده."""
        # First try exact symbol match
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id FROM funds WHERE symbol = ? AND is_active = 1",
                (symbol,)
            ).fetchone()
        if row:
            return row["id"]
        
        # If not found, try to find by ISIN from fund_universe
        with self.db.transaction() as conn:
            # Get ISIN from fund_universe
            row = conn.execute(
                "SELECT isin FROM fund_universe WHERE symbol = ? AND is_active = 1",
                (symbol,)
            ).fetchone()
        if not row or not row["isin"]:
            return None
        
        isin = row["isin"]
        # Find matching fund in old funds table by ISIN
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT id FROM funds WHERE isin = ? AND is_active = 1",
                (isin,)
            ).fetchone()
        return row["id"] if row else None
    
    def _backfill_fund_history(self, fund: dict) -> int:
        """دریافت و ذخیره تاریخچه قیمت یک صندوق از Candlestick endpoint."""
        symbol = fund["symbol"]
        
        logger.info("Backfilling candlestick history for %s", symbol)
        
        # Use Candlestick endpoint type=3 (daily adjusted) for price history
        # This is the correct endpoint for technical analysis price data
        payload = self.provider.get_candlestick(symbol, candlestick_type=3, count=500)
        
        if not payload:
            logger.warning("No candlestick data returned for %s", symbol)
            return 0
        
        days_added = 0
        fund_id = self._get_fund_id_from_funds_table(symbol)
        if not fund_id:
            logger.warning("Fund %s not found in funds table", symbol)
            return 0
        
        def to_float(v):
            if v is None or v == "":
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None
        
        def convert_persian_date(persian_date: str) -> str:
            """تبدیل تاریخ شمسی 1405-05-19 به میلادی."""
            try:
                if not persian_date or len(persian_date) != 10:
                    return persian_date
                parts = persian_date.split("-")
                if len(parts) != 3:
                    return persian_date
                jy, jm, jd = int(parts[0]), int(parts[1]), int(parts[2])
                # Jalali to Gregorian conversion
                jy += 1595
                days = -355668 + (365 * jy) + (jy // 33) * 8 + (jy % 33 + 3) // 4 + jd
                if jm < 7:
                    days += (jm - 1) * 31
                else:
                    days += (jm - 7) * 30 + 186
                gy = 400 * (days // 146097)
                days %= 146097
                if days > 36524:
                    gy += 100 * (days // 36525)
                    days %= 36525
                    if days >= 365:
                        days += 1
                gy += 4 * (days // 1461)
                days %= 1461
                if days > 365:
                    gy += (days - 1) // 365
                    days = (days - 1) % 365
                gd = days + 1
                if (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0):
                    kab = 29
                else:
                    kab = 28
                sal_a = [0, 31, kab, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
                gm = 0
                while gm < 13 and gd > sal_a[gm]:
                    gd -= sal_a[gm]
                    gm += 1
                return f"{gy:04d}-{gm:02d}-{gd:02d}"
            except Exception:
                return persian_date
        
        with self.db.transaction() as conn:
            for candle in payload:
                try:
                    trade_date = candle.get("date")
                    if not trade_date:
                        continue
                    
                    # Convert Persian date to Gregorian
                    trade_date = convert_persian_date(trade_date)
                    
                    open_price = to_float(candle.get("open"))
                    high_price = to_float(candle.get("high"))
                    low_price = to_float(candle.get("low"))
                    close_price = to_float(candle.get("close"))
                    volume = to_float(candle.get("volume"))
                    value = None
                    trade_count = None
                    change_pct = None
                    
                    conn.execute("""
                        INSERT INTO history (
                            fund_id, trade_date, open_price, high_price,
                            low_price, close_price, last_price, yesterday_price,
                            volume, value, trade_count, change_pct, source, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'brs', ?)
                        ON CONFLICT(fund_id, trade_date) DO UPDATE SET
                            open_price=excluded.open_price,
                            high_price=excluded.high_price,
                            low_price=excluded.low_price,
                            close_price=excluded.close_price,
                            last_price=excluded.last_price,
                            yesterday_price=excluded.yesterday_price,
                            volume=excluded.volume,
                            value=excluded.value,
                            trade_count=excluded.trade_count,
                            change_pct=excluded.change_pct
                    """, (
                        fund_id,
                        trade_date,
                        open_price,
                        high_price,
                        low_price,
                        close_price,
                        close_price,  # last_price = close for daily candles
                        None,  # yesterday_price not in candlestick
                        volume,
                        value,
                        trade_count,
                        change_pct,
                        datetime.now().isoformat(),
                    ))
                    days_added += 1
                    
                except Exception as e:
                    logger.warning("Failed to parse candlestick row for %s: %s", symbol, e)
                    continue
        
        return days_added


# Convenience function for cron
def run_history_backfill() -> dict:
    """اجرای backfill برای cron."""
    job = HistoryBackfillJob()
    return job.run()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_history_backfill()
    print(f"History backfill result: {result}")
    sys.exit(0 if not result.get("errors") else 1)