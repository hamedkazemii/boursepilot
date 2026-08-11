"""
Candlestick Sync Job — دریافت کندل‌های تعدیل‌شده روزانه از BRS

این job روی سرور ایران (Collector) اجرا می‌شود:
- Candlestick.php?type=3 برای کندل‌های روزانه تعدیل‌شده (split/dividend adjusted)
- برای تحلیل تکنیکال دقیق و محاسبه اندیکاتورهای بلندمدت
- اجرای روزانه در cron شبانه
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from core.database.connection import get_database
from services.providers.brs_provider import BrsProvider

logger = logging.getLogger(__name__)


class CandlestickSyncJob:
    """
    همگام‌سازی کندل‌های تعدیل‌شده روزانه از BRS Candlestick API.
    
    استراتژی:
    1. برای صندوق‌های فعال، دریافت کندل‌های type=3 (تعدیل‌شده)
    2. ذخیره در جدول candlesticks (جدول جدید)
    3. استفاده برای محاسبه اندیکاتورهای دقیق (EMA، MACD، RSI با قیمت تعدیل‌شده)
    """
    
    def __init__(
        self,
        provider: Optional[BrsProvider] = None,
        max_funds_per_run: int = 100,
        lookback_days: int = 400,  # تعداد روزهای backfill
        db_path: Optional[str] = None,
    ):
        self.provider = provider or BrsProvider()
        self.max_funds_per_run = max_funds_per_run
        self.lookback_days = lookback_days
        self.db = get_database(db_path)
        self._ensure_candlestick_table()
    
    def _ensure_candlestick_table(self) -> None:
        """ایجاد جدول candlesticks اگر وجود نداشته باشد."""
        with self.db.transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candlesticks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fund_id INTEGER NOT NULL,
                    trade_date TEXT NOT NULL,
                    open_price REAL,
                    high_price REAL,
                    low_price REAL,
                    close_price REAL,
                    volume REAL,
                    value REAL,
                    candlestick_type INTEGER NOT NULL DEFAULT 3,  -- 3=تعدیل‌شده
                    source TEXT NOT NULL DEFAULT 'brs_candlestick',
                    created_at TEXT NOT NULL,
                    UNIQUE(fund_id, trade_date, candlestick_type),
                    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candlesticks_fund_date 
                ON candlesticks(fund_id, trade_date)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_candlesticks_date 
                ON candlesticks(trade_date)
            """)
    
    def run(self) -> dict:
        """اجرای job و بازگرداندن آمار."""
        started = datetime.now()
        stats = {
            "started_at": started.isoformat(),
            "funds_processed": 0,
            "total_candles_added": 0,
            "errors": [],
            "quota_report": {},
        }
        
        # دریافت لیست صندوق‌های فعال
        funds = self._get_active_funds()
        
        if not funds:
            logger.warning("No active funds found")
            stats["finished_at"] = datetime.now().isoformat()
            return stats
        
        # محدودیت تعداد
        funds_to_process = funds[:self.max_funds_per_run]
        logger.info("Syncing candlesticks for %d/%d funds", len(funds_to_process), len(funds))
        
        for fund in funds_to_process:
            try:
                candles_added = self._sync_fund_candlesticks(fund)
                if candles_added > 0:
                    stats["funds_processed"] += 1
                    stats["total_candles_added"] += candles_added
                    logger.info("Synced %d candles for %s", candles_added, fund["symbol"])
            except Exception as e:
                error_msg = f"Failed to sync candlesticks for {fund['symbol']}: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)
        
        # گزارش quota
        if hasattr(self.provider, "get_quota_report"):
            stats["quota_report"] = self.provider.get_quota_report()
        
        stats["finished_at"] = datetime.now().isoformat()
        stats["duration_seconds"] = (datetime.now() - started).total_seconds()
        
        logger.info(
            "CandlestickSyncJob done: processed=%d candles_added=%d errors=%d",
            stats["funds_processed"], stats["total_candles_added"], len(stats["errors"])
        )
        return stats
    
    def _get_active_funds(self) -> list[dict]:
        """دریافت لیست صندوق‌های فعال از دیتابیس."""
        with self.db.transaction() as conn:
            rows = conn.execute("""
                SELECT id, symbol, name
                FROM funds
                WHERE is_active = 1
                ORDER BY symbol
            """).fetchall()
            return [dict(row) for row in rows]
    
    def _sync_fund_candlesticks(self, fund: dict) -> int:
        """
        دریافت و ذخیره کندل‌های تعدیل‌شده برای یک صندوق.
        
        Returns: تعداد کندل‌های اضافه/به‌روزرسانی شده
        """
        symbol = fund["symbol"]
        fund_id = fund["id"]
        
        # محاسبه تاریخ شروع: lookback_days روز پیش
        from_date = (datetime.now().date() - timedelta(days=self.lookback_days)).isoformat()
        
        logger.info("Fetching candlesticks for %s from %s (type=3 adjusted)", symbol, from_date)
        
        try:
            # type=3 = روزانه تعدیل‌شده (split/dividend adjusted)
            candlesticks = self.provider.get_candlestick(
                symbol=symbol,
                candlestick_type=3,
                date=from_date,  # Some APIs use date as start date
            )
        except Exception as e:
            logger.error("BRS Candlestick request failed for %s: %s", symbol, e)
            raise
        
        if not candlesticks:
            logger.warning("No candlestick data returned for %s", symbol)
            return 0
        
        # پارس و ذخیره
        candles_added = 0
        with self.db.transaction() as conn:
            for row in candlesticks:
                if not isinstance(row, dict):
                    continue
                
                try:
                    # فیلدهای BRS Candlestick response
                    trade_date = row.get("date") or row.get("trade_date")
                    if not trade_date:
                        continue
                    
                    trade_date = str(trade_date).strip()
                    if len(trade_date) != 10:
                        continue
                    
                    # قیمت‌ها (تعدیل‌شده)
                    open_price = row.get("open") or row.get("open_price")
                    high_price = row.get("high") or row.get("high_price")
                    low_price = row.get("low") or row.get("low_price")
                    close_price = row.get("close") or row.get("close_price")
                    
                    volume = row.get("volume")
                    value = row.get("value")
                    
                    def to_float(v):
                        if v is None or v == "":
                            return None
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            return None
                    
                    conn.execute("""
                        INSERT INTO candlesticks (
                            fund_id, trade_date, open_price, high_price, low_price,
                            close_price, volume, value, candlestick_type, source, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 3, 'brs_candlestick', ?)
                        ON CONFLICT(fund_id, trade_date, candlestick_type) DO UPDATE SET
                            open_price=excluded.open_price,
                            high_price=excluded.high_price,
                            low_price=excluded.low_price,
                            close_price=excluded.close_price,
                            volume=excluded.volume,
                            value=excluded.value
                    """, (
                        fund_id,
                        trade_date,
                        to_float(open_price),
                        to_float(high_price),
                        to_float(low_price),
                        to_float(close_price),
                        to_float(volume),
                        to_float(value),
                        datetime.now().isoformat(),
                    ))
                    candles_added += 1
                    
                except Exception as e:
                    logger.warning("Failed to parse candlestick row for %s: %s", symbol, e)
                    continue
        
        return candles_added


# Convenience function for cron
def run_candlestick_sync() -> dict:
    """اجرای candlestick sync برای cron."""
    job = CandlestickSyncJob()
    return job.run()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_candlestick_sync()
    print(f"Candlestick sync result: {result}")
    sys.exit(0 if not result.get("errors") else 1)