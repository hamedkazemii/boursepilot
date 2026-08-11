"""
CODAL Disclosure Storage Service.

Stores and retrieves KODAL announcements from database.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from core.database.connection import get_database
from services.providers.codal_provider import CodalDisclosure

logger = logging.getLogger(__name__)


class CodalStorage:
    """ ذخیره و بازیابی اطلاعیه‌های کدال در دیتابیس """

    def __init__(self, db=None):
        self.db = db or get_database()

    def store_disclosures(self, disclosures: list[CodalDisclosure]) -> int:
        """
        ذخیره لیست اطلاعیه‌ها در دیتابیس.
        
        Returns: تعداد رکوردهای جدید/به‌روزرسانی شده
        """
        if not disclosures:
            return 0

        stored = 0
        with self.db.transaction() as conn:
            for d in disclosures:
                try:
                    # Create unique ID from link or title+date
                    disclosure_id = d.link or f"{d.symbol}|{d.date_publish}|{d.title[:50]}"
                    
                    conn.execute("""
                        INSERT INTO kodal_disclosures (
                            disclosure_id, symbol, title, summary, importance, category,
                            published_at, url, raw_json, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(disclosure_id) DO UPDATE SET
                            title=excluded.title,
                            summary=excluded.summary,
                            importance=excluded.importance,
                            category=excluded.category,
                            published_at=excluded.published_at,
                            url=excluded.url,
                            raw_json=excluded.raw_json
                    """, (
                        disclosure_id,
                        d.symbol,
                        d.title,
                        self._extract_summary(d),
                        self._classify_importance(d),
                        self._classify_category(d),
                        f"{d.date_publish} {d.time_publish}",
                        d.link,
                        json.dumps(d.raw_data, ensure_ascii=False),
                        datetime.now().isoformat(),
                    ))
                    stored += 1
                except Exception as e:
                    logger.warning("Failed to store codal disclosure for %s: %s", d.symbol, e)
                    continue

        logger.info("Stored %d CODAL disclosures", stored)
        return stored

    def _extract_summary(self, d: CodalDisclosure) -> str:
        """خلاصه کوتاه از عنوان اطلاعیه"""
        title = d.title.lower()
        if "صورت‌های مالی" in title or "مالی" in title:
            return "گزارش مالی"
        if "مجمع" in title or "مجمع عمومی" in title:
            return "مجمع عمومی"
        if "افزایش سرمایه" in title:
            return "افزایش سرمایه"
        if "کاهش سرمایه" in title:
            return "کاهش سرمایه"
        if "تقسیم سود" in title or "سود" in title:
            return "تقسیم سود"
        if "انتصاب" in title or "عزل" in title:
            return "تغییرات هیئت مدیره"
        if "تغییر" in title:
            return "تغییرات بنیادین"
        return d.title[:200] if d.title else "اطلاعیه کدال"

    def _classify_importance(self, d: CodalDisclosure) -> str:
        """طبقه‌بندی اهمیت"""
        title = d.title.lower()
        if "حسابرسی شده" in title:
            return "high"
        if "مجمع" in title:
            return "high"
        if "افزایش سرمایه" in title:
            return "high"
        if "صورت‌های مالی" in title:
            return "medium"
        return "low"

    def _classify_category(self, d: CodalDisclosure) -> str:
        """طبقه‌بندی دسته‌بندی"""
        title = d.title.lower()
        if "صورت‌های مالی" in title:
            return "financial_report"
        if "مجمع" in title:
            return "general_assembly"
        if "افزایش سرمایه" in title or "کاهش سرمایه" in title:
            return "capital_change"
        if "تقسیم سود" in title:
            return "dividend"
        if "انتصاب" in title or "عزل" in title:
            return "board_change"
        return "other"

    def get_latest_for_symbol(self, symbol: str, limit: int = 10) -> list[dict]:
        """بازیابی آخرین اطلاعیه‌های یک نماد"""
        with self.db.transaction() as conn:
            rows = conn.execute("""
                SELECT disclosure_id, symbol, title, summary, importance, category,
                       published_at, url, raw_json, created_at
                FROM kodal_disclosures
                WHERE symbol = ?
                ORDER BY published_at DESC
                LIMIT ?
            """, (symbol, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_recent_all(self, limit: int = 50, days: int = 30) -> list[dict]:
        """بازیابی آخرین اطلاعیه‌های همه نمادها"""
        from_date = datetime.now().replace(day=datetime.now().day - days).strftime("%Y-%m-%d")
        with self.db.transaction() as conn:
            rows = conn.execute("""
                SELECT disclosure_id, symbol, title, summary, importance, category,
                       published_at, url, raw_json, created_at
                FROM kodal_disclosures
                WHERE published_at >= ?
                ORDER BY published_at DESC
                LIMIT ?
            """, (from_date, limit)).fetchall()
            return [dict(r) for r in rows]

    def get_count_by_symbol(self, symbol: str) -> int:
        """تعداد اطلاعیه‌های یک نماد"""
        with self.db.transaction() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM kodal_disclosures WHERE symbol = ?",
                (symbol,)
            ).fetchone()
            return row["cnt"] if row else 0


def get_codal_storage():
    return CodalStorage()