"""
Candlestick Backfill Job — پر کردن تاریخچه صندوق‌ها از BRS Candlestick.php

این job روی سرور ایران (Collector) اجرا می‌شود:
- Candlestick.php?type=3 برای کندل‌های روزانه تعدیل‌شده (split/dividend adjusted)
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
from services.providers.brs_provider import BrsProvider

logger = logging.getLogger(__name__)


class CandlestickBackfillJob:
    """
    پر کردن تاریخچه صندوق‌ها از BRS Candlestick API (type=3 = adjusted daily).
    
    استراتژی:
    1. پیدا کردن صندوق‌های فعال با تاریخچه کمتر از min_days
    2. برای هر صندوق، درخواست Candlestick.php?type=3 (کندل‌های تعدیل‌شده)
    3. Upsert به جدول history (برای سازگاری با موتور اندیکاتورها)
    4. همچنین ذخیره در جدول candlesticks (جدول جدید برای داده‌های تعدیل‌شده)
    5. گزارش تعداد روزهای اضافه شده
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
        
        # 1. پیدا کردن صندوق‌های کم‌تاریخچه (فقط صندوق‌های fund_like)
        funds_needing_history = self._find_funds_needing_history()
        stats["funds_checked"] = len(funds_needing_history)
        
        if not funds_needing_history:
            logger.info("All funds have sufficient history (>= %d days)", self.min_history_days)
            stats["finished_at"] = datetime.now().isoformat()
            return stats
        
        # محدودیت تعداد در هر اجرا
        funds_to_process = funds_needing_history[:self.max_funds_per_run]
        logger.info("Backfilling candlesticks for %d/%d funds", len(funds_to_process), len(funds_needing_history))
        
        # 2. برای هر صندوق، دریافت و ذخیره کندل‌ها
        for fund in funds_to_process:
            try:
                days_added = self._backfill_fund_candlesticks(fund)
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
            "CandlestickBackfillJob done: checked=%d backfilled=%d days_added=%d errors=%d",
            stats["funds_checked"], stats["funds_backfilled"], stats["total_days_added"], len(stats["errors"])
        )
        return stats
    
    def _find_funds_needing_history(self) -> list[dict]:
        """پیدا کردن صندوق‌های fund_like که تاریخچه کمتر از min_history_days روز دارند."""
        with self.db.transaction() as conn:
            rows = conn.execute("""
                SELECT f.id, f.symbol, f.name,
                       COUNT(h.id) as history_count,
                       MIN(h.trade_date) as oldest_date,
                       MAX(h.trade_date) as newest_date
                FROM funds f
                LEFT JOIN history h ON h.fund_id = f.id
                WHERE f.is_active = 1 AND f.is_fund_like = 1
                GROUP BY f.id, f.symbol, f.name
                HAVING history_count < ? OR history_count = 0
                ORDER BY history_count ASC, f.symbol
            """, (self.min_history_days,)).fetchall()
            
            result = []
            for row in rows:
                # Skip derivative products (symbols ending with digit like 2, 4, etc.)
                symbol = row["symbol"]
                if symbol[-1].isdigit() and len(symbol) > 1 and symbol[-2] not in '0123456789':
                    # This is likely a derivative (e.g., "آتیه ملت4")
                    continue
                result.append({
                    "fund_id": row["id"],
                    "symbol": row["symbol"],
                    "name": row["name"],
                    "history_count": row["history_count"],
                    "oldest_date": row["oldest_date"],
                    "newest_date": row["newest_date"],
                })
            return result
    
    def _backfill_fund_candlesticks(self, fund: dict) -> int:
        """
        دریافت کندل‌های تعدیل‌شده برای یک صندوق و ذخیره در DB.
        
        Returns: تعداد روزهای جدید اضافه شده
        """
        symbol = fund["symbol"]
        fund_id = fund["fund_id"]
        
        # محاسبه تاریخ شروع: از ۲ سال پیش
        # برای BRS Candlestick type=3، استفاده از count برای دریافت تعداد زیادی کندل
        # بدون پارامتر date تا تمام کندل‌ها برگردانده شوند
        logger.info("Fetching candlesticks for %s (type=3 adjusted, count=1000)", symbol)
        
        # درخواست از BRS - type=3 برای کندل‌های روزانه تعدیل‌شده
        try:
            candlesticks = self.provider.get_candlestick(
                symbol=symbol,
                candlestick_type=3,  # روزانه تعدیل‌شده
                count=1000,  # دریافت حداکثر ۱۰۰۰ کندل
            )
        except Exception as e:
            logger.error("BRS Candlestick request failed for %s: %s", symbol, e)
            raise
        
        if not candlesticks:
            logger.warning("No candlestick data returned for %s", symbol)
            return 0
        
        # پارس و ذخیره
        days_added = 0
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
                    
                    # ذخیره در جدول candlesticks (داده تعدیل‌شده)
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
                    
                    # هم‌زمان در جدول history برای سازگاری با IndicatorEngine
                    conn.execute("""
                        INSERT INTO history (
                            fund_id, trade_date, open_price, high_price, low_price,
                            close_price, last_price, yesterday_price,
                            volume, value, trade_count, change_pct, source, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'brs_candlestick', ?)
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
                        to_float(open_price),
                        to_float(high_price),
                        to_float(low_price),
                        to_float(close_price),
                        to_float(close_price),  # last_price = close_price for daily
                        to_float(open_price),   # yesterday_price = open_price as fallback
                        to_float(volume),
                        to_float(value),
                        0,  # trade_count
                        None,  # change_pct
                        datetime.now().isoformat(),
                    ))
                    days_added += 1
                    
                except Exception as e:
                    logger.warning("Failed to parse candlestick row for %s: %s", symbol, e)
                    continue
        
        return days_added


# Convenience function for cron
def run_candlestick_backfill() -> dict:
    """اجرای backfill برای cron."""
    job = CandlestickBackfillJob()
    return job.run()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    result = run_candlestick_backfill()
    print(f"Candlestick backfill result: {result}")
    sys.exit(0 if not result.get("errors") else 1)