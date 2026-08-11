"""
History Backfill Job — پر کردن تاریخچه صندوق‌ها از BRS History.php

این job روی سرور ایران (Collector) اجرا می‌شود:
- History.php?type=2 برای دریافت تاریخچه قیمتی روزانه (open, high, low, close, volume)
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
    پر کردن تاریخچه صندوق‌ها از BRS History API.
    
    استراتژی:
    1. پیدا کردن صندوق‌هایی با تاریخچه کمتر از min_days (از fund_universe)
    2. برای هر صندوق، درخواست History.php?type=2 از تاریخ قدیمی‌تر تا امروز
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
        """
        دریافت تاریخچه کامل برای یک صندوق و ذخیره در DB.
        
        Returns: تعداد روزهای جدید اضافه شده
        """
        symbol = fund["symbol"]
        fund_id = fund["fund_id"]
        
        # محاسبه بازه تاریخ: از قدیمی‌ترین تاریخ موجود تا امروز
        # اگر تاریخچه‌ای نداریم، از ۲ سال پیش درخواست می‌کنیم
        if fund["oldest_date"]:
            # درخواست از ۳۰ روز قبل از قدیمی‌ترین تا امروز (برای overlap و اطمینان)
            try:
                oldest = datetime.fromisoformat(fund["oldest_date"]).date()
                from_date = (oldest - timedelta(days=30)).isoformat()
            except Exception:
                from_date = (datetime.now().date() - timedelta(days=730)).isoformat()  # 2 years
        else:
            from_date = (datetime.now().date() - timedelta(days=730)).isoformat()  # 2 years
        
        to_date = datetime.now().date().isoformat()
        
        logger.info("Fetching history for %s from %s to %s", symbol, from_date, to_date)
        
        # درخواست از BRS - type=2 برای تاریخچه قیمتی
        try:
            history_data = self.provider.get_history(
                symbol=symbol,
                history_type=2,  # قیمتی
                from_date=from_date,
                to_date=to_date,
            )
        except Exception as e:
            logger.error("BRS History request failed for %s: %s", symbol, e)
            raise
        
        if not history_data:
            logger.warning("No history data returned for %s", symbol)
            return 0
        
        # پارس و ذخیره
        days_added = 0
        with self.db.transaction() as conn:
            for row in history_data:
                if not isinstance(row, dict):
                    continue
                
                try:
                    # فیلدهای BRS History response
                    trade_date = row.get("date") or row.get("trade_date")
                    if not trade_date:
                        continue
                    
                    # نرمال‌سازی تاریخ
                    trade_date = str(trade_date).strip()
                    if len(trade_date) != 10:
                        continue
                    
                    # قیمت‌ها
                    close_price = row.get("close_price") or row.get("close") or row.get("pl")
                    open_price = row.get("open_price") or row.get("open") or row.get("pf")
                    high_price = row.get("high_price") or row.get("high") or row.get("pmax")
                    low_price = row.get("low_price") or row.get("low") or row.get("pmin")
                    yesterday_price = row.get("yesterday_price") or row.get("py")
                    last_price = row.get("last_price") or row.get("pl")
                    
                    volume = row.get("volume") or row.get("tvol") or row.get("vol")
                    value = row.get("value") or row.get("tval")
                    change_pct = row.get("change_pct") or row.get("pcp") or row.get("plp")
                    trade_count = row.get("trade_count") or row.get("tno")
                    
                    # تبدیل به float
                    def to_float(v):
                        if v is None or v == "":
                            return None
                        try:
                            return float(v)
                        except (ValueError, TypeError):
                            return None
                    
                    conn.execute("""
                        INSERT INTO history (
                            fund_id, trade_date, open_price, high_price, low_price,
                            close_price, last_price, yesterday_price,
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
                        to_float(open_price),
                        to_float(high_price),
                        to_float(low_price),
                        to_float(close_price),
                        to_float(last_price),
                        to_float(yesterday_price),
                        to_float(volume),
                        to_float(value),
                        int(trade_count) if trade_count else 0,
                        to_float(change_pct),
                        datetime.now().isoformat(),
                    ))
                    days_added += 1
                    
                except Exception as e:
                    logger.warning("Failed to parse history row for %s: %s", symbol, e)
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