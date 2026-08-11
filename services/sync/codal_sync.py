"""
CODAL Sync Job — Sync KODAL announcements for valid fund universe.

Runs on Iran server (Collector) daily.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.discovery.universe_store import get_valid_fund_symbols
from services.providers.codal_provider import CodalProvider
from services.discovery.codal_storage import get_codal_storage

logger = logging.getLogger(__name__)


def run_codal_sync(
    limit: Optional[int] = None,
    category: int = 1,
) -> dict[str, Any]:
    """
    اجرای sync اطلاعیه‌های کدال برای تمام صندوق‌های معتبر.
    
    Args:
        limit: تعداد صندوق‌ها (None = همه)
        category: دسته‌بندی کدال (1=صندوق)
    
    Returns:
        dict با آمار sync
    """
    symbols = get_valid_fund_symbols()
    
    if limit:
        symbols = symbols[:limit]
    
    logger.info("Starting CODAL sync for %d funds", len(symbols))
    
    codal_provider = CodalProvider()
    codal_storage = get_codal_storage()
    
    total_stored = 0
    processed = 0
    errors = 0
    
    for i, sym in enumerate(symbols, 1):
        try:
            if i % 10 == 0:
                logger.info("CODAL sync progress: %d/%d", i, len(symbols))
            
            # دریافت اطلاعیه‌ها
            disclosures = codal_provider.get_latest(sym, limit=20, category=category)
            
            if disclosures:
                stored = codal_storage.store_disclosures(disclosures)
                total_stored += stored
            
            processed += 1
            
        except Exception as e:
            logger.warning("CODAL sync failed for %s: %s", sym, e)
            errors += 1
            continue
    
    result = {
        "total_funds": len(symbols),
        "processed": processed,
        "total_disclosures_stored": total_stored,
        "errors": errors,
    }
    
    logger.info("CODAL sync complete: %s", result)
    return result


def run_codal_sync_user_funds(user_funds: list[str]) -> dict[str, Any]:
    """Sync CODAL only for user's portfolio funds (higher priority)"""
    valid_symbols = get_valid_fund_symbols()
    valid_set = set(valid_symbols)
    
    targets = [s for s in user_funds if s in valid_set]
    logger.info("CODAL sync for user funds: %d/%d valid", len(targets), len(user_funds))
    
    if not targets:
        return {"total_funds": 0, "processed": 0, "total_disclosures_stored": 0, "errors": 0}
    
    codal_provider = CodalProvider()
    codal_storage = get_codal_storage()
    
    total_stored = 0
    for sym in targets:
        try:
            disclosures = codal_provider.get_latest(sym, limit=20, category=1)
            if disclosures:
                total_stored += codal_storage.store_disclosures(disclosures)
        except Exception as e:
            logger.warning("CODAL user sync failed for %s: %s", sym, e)
    
    return {
        "total_funds": len(targets),
        "processed": len(targets),
        "total_disclosures_stored": total_stored,
        "errors": 0,
    }