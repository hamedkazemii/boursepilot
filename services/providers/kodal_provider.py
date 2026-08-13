"""KODAL Provider — دریافت اطلاعیه‌های رسمی از سامانه کدال (https://kodal.ir).

این ماژول برای یکپارچه‌سازی با API رسمی کدال طراحی شده است.
Endpointهای واقعی باید از مستندات رسمی کدال تأیید شوند.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class KodalDisclosure:
    """یک اطلاعیه کدال."""
    disclosure_id: str
    symbol: str
    title: str
    summary: str
    importance: str  # "high", "medium", "low"
    category: str    # "financial", "corporate_action", "governance", "material_event", "other"
    published_at: str
    url: Optional[str] = None
    raw: Optional[dict[str, Any]] = None


class KodalProvider:
    """Provider دریافت اطلاعیه‌های کدال برای صندوق‌ها."""

    name = "kodal"

    def __init__(self, base_url: str = "https://kodal.ir/api/v1", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = None

    @property
    def is_available(self) -> bool:
        return True

    def _get_session(self):
        if self._session is None:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "BoursePilot/1.0"})
        return self._session

    def get_disclosures(
        self,
        symbol: str,
        limit: int = 20,
        since_days: Optional[int] = None,
    ) -> list[KodalDisclosure]:
        """دریافت آخرین اطلاعیه‌های یک نماد.

        Args:
            symbol: نماد صندوق/سهم
            limit: تعداد نتایج
            since_days: فقط اطلاعیه‌های اخیر (مثلاً ۳۰ روز)

        Returns:
            لیست KodalDisclosure
        """
        # TODO: Replace with real KODAL API endpoint
        # Example endpoint: GET /disclosures?symbol={symbol}&limit={limit}
        logger.warning("KODAL get_disclosures not fully implemented - using stub")
        return []

    def search_disclosures(
        self,
        query: str,
        category: Optional[str] = None,
        importance: Optional[str] = None,
        limit: int = 50,
    ) -> list[KodalDisclosure]:
        """جستجوی اطلاعیه‌ها بر اساس کلمات کلیدی."""
        logger.warning("KODAL search_disclosures not fully implemented - using stub")
        return []

    def get_latest_material_events(self, limit: int = 20) -> list[KodalDisclosure]:
        """مهم‌ترین اطلاعیه‌های اخیر کل بازار."""
        logger.warning("KODAL get_latest_material_events not fully implemented - using stub")
        return []


# ------------------------------------------------------------
# Storage helpers (برای نگهداری در دیتابیس محلی)
# ------------------------------------------------------------

def create_kodal_table_sql() -> str:
    """SQL برای ساخت جدول اطلاعیه‌های کدال."""
    return """
CREATE TABLE IF NOT EXISTS kodal_disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    disclosure_id TEXT NOT NULL UNIQUE,
    symbol TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    importance TEXT NOT NULL,
    category TEXT NOT NULL,
    published_at TEXT NOT NULL,
    url TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(symbol) REFERENCES funds(symbol) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_kodal_symbol ON kodal_disclosures(symbol);
CREATE INDEX IF NOT EXISTS idx_kodal_published ON kodal_disclosures(published_at);
CREATE INDEX IF NOT EXISTS idx_kodal_importance ON kodal_disclosures(importance);
"""


def upsert_kodal_disclosure(db, disclosure: KodalDisclosure) -> bool:
    """ذخیره/به‌روزرسانی یک اطلاعیه کدال."""
    import json
    try:
        db.execute(
            """
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
            """,
            (
                disclosure.disclosure_id,
                disclosure.symbol,
                disclosure.title,
                disclosure.summary,
                disclosure.importance,
                disclosure.category,
                disclosure.published_at,
                disclosure.url,
                json.dumps(disclosure.raw, ensure_ascii=False) if disclosure.raw else None,
                datetime.now().astimezone().isoformat(timespec="seconds"),
            ),
        )
        return True
    except Exception as e:
        logger.error("Failed to upsert KODAL disclosure: %s", e)
        return False


def get_kodal_disclosures(db, symbol: str, limit: int = 10) -> list[dict]:
    """دریافت اطلاعیه‌های یک نماد از دیتابیس محلی."""
    rows = db.execute(
        """
        SELECT disclosure_id, title, summary, importance, category, published_at, url, raw_json
        FROM kodal_disclosures
        WHERE symbol = ?
        ORDER BY published_at DESC
        LIMIT ?
        """,
        (symbol, limit),
    ).fetchall()
    return [dict(r) for r in rows]