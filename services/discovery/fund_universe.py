"""
Fund Universe Builder — Source of Truth: BRS AllSymbols.

این ماژول Universe کامل صندوق‌ها را از BRS AllSymbols می‌سازد.
فقط نمادهایی که BRS آن‌ها را در sector "صندوق سرمایه‌گذاری قابل معامله" (cs_id=68)
تصنیف کرده است، وارد Universe می‌شوند.

مزیت‌ها:
- Source of Truth واحد: BRS AllSymbols
- انبار نمادهای مشتقه، اختیار، حق‌تقدم، سهام، بانک، بیمه
- بر اساس metadata واقعی BRS (cs, cs_id, isin, ins_code) نه heuristic
- Symbol + ISIN/ins_code برای match دقیق و جلوگیری از duplicate
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from services.providers.brs_client import BrsClient
from config import settings

logger = logging.getLogger(__name__)

# BRS sector IDs
FUND_SECTOR_ID = 68          # صندوق سرمایه‌گذاری قابل معامله
INSURANCE_SECTOR_ID = 66     # بیمه و صندوق بازنشستگی

FUND_SECTOR_NAME = "صندوق سرمایه‌گذاری قابل معامله"
INSURANCE_SECTOR_NAME = "بیمه و صندوق بازنشستگی"


@dataclass(frozen=True)
class FundUniverseEntry:
    """
    یک ورودی در Universe صندوق‌ها.
    بر اساس BRS AllSymbols response ساخته شده.
    """
    symbol: str                    # l18 - نماد فارسی
    name: str                      # l30 - نام کامل
    isin: Optional[str]            # ISIN
    ins_code: Optional[str]        # ins_code / id (بصورت string)
    cs: str                        # sector name (صندوق سرمایه‌گذاری قابل معامله)
    cs_id: int                     # sector id (68)
    cs_sub: Optional[str] = None   # sub-sector
    cs_sub_id: Optional[int] = None
    board: Optional[str] = None    # m_board
    board_id: Optional[int] = None
    shares: Optional[int] = None   # z
    market_value: Optional[int] = None  # mv
    last_price: Optional[float] = None  # pl
    close_price: Optional[float] = None # pc
    yesterday_price: Optional[float] = None # py
    nav_issue: Optional[float] = None  # psubtran
    nav_redeem: Optional[float] = None # predtran
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    @property
    def unique_key(self) -> str:
        """کلید یکتا برای deduplication: ISIN > ins_code > symbol"""
        if self.isin:
            return f"ISIN:{self.isin}"
        if self.ins_code:
            return f"INS:{self.ins_code}"
        return f"SYM:{self.symbol}"


class FundUniverseBuilder:
    """
    سازنده Universe صندوق‌ها از BRS AllSymbols.
    
    Flow:
    1. دریافت AllSymbols از BRS (type=1 همه نمادها)
    2. فیلتر کردن فقط cs_id == 68 (صندوق سرمایه‌گذاری قابل معامله)
    3. تبدیل به FundUniverseEntry
    4. Deduplication با unique_key (ISIN > ins_code > symbol)
    5. ذخیره در DB جدول fund_universe
    """
    
    def __init__(self, client: Optional[BrsClient] = None):
        self.client = client or BrsClient(
            api_key=settings.BRS_API_KEY,
            base_url=settings.BRS_BASE_URL,
        )
        self.stats = {
            "total_fetched": 0,
            "fund_sector_count": 0,
            "insurance_sector_count": 0,
            "other_sectors_count": 0,
            "deduplicated": 0,
            "final_count": 0,
            "api_calls": 0,
        }
    
    def fetch_all_symbols(self) -> list[dict[str, Any]]:
        """دریافت تمام نمادها از BRS AllSymbols."""
        logger.info("Fetching AllSymbols from BRS...")
        data = self.client.get_all_symbols(symbol_type=1)  # type=1 همه نمادها
        self.stats["total_fetched"] = len(data)
        self.stats["api_calls"] += 1
        logger.info(f"Fetched {len(data)} total symbols from BRS")
        return data
    
    def classify_symbols(self, symbols: list[dict[str, Any]]) -> tuple[list[dict], list[dict], list[dict]]:
        """تقسیم نمادها بر اساس sector_id."""
        fund_symbols = []
        insurance_symbols = []
        other_symbols = []
        
        for s in symbols:
            cs_id = s.get("cs_id")
            if cs_id == FUND_SECTOR_ID:
                fund_symbols.append(s)
                self.stats["fund_sector_count"] += 1
            elif cs_id == INSURANCE_SECTOR_ID:
                insurance_symbols.append(s)
                self.stats["insurance_sector_count"] += 1
            else:
                other_symbols.append(s)
                self.stats["other_sectors_count"] += 1
        
        logger.info(f"Classification: Fund={len(fund_symbols)}, Insurance={len(insurance_symbols)}, Other={len(other_symbols)}")
        return fund_symbols, insurance_symbols, other_symbols
    
    def build_entries(self, fund_symbols: list[dict[str, Any]]) -> list[FundUniverseEntry]:
        """تبدیل نمادهای صندوق به FundUniverseEntry."""
        entries = []
        for s in fund_symbols:
            try:
                entry = FundUniverseEntry(
                    symbol=s.get("l18", "").strip(),
                    name=s.get("l30", "").strip(),
                    isin=s.get("isin"),
                    ins_code=str(s.get("id")) if s.get("id") else None,
                    cs=s.get("cs", ""),
                    cs_id=s.get("cs_id", 0),
                    cs_sub=s.get("cs_sub"),
                    cs_sub_id=s.get("cs_sub_id"),
                    board=s.get("m_board"),
                    board_id=s.get("m_board_id"),
                    shares=s.get("z"),
                    market_value=s.get("mv"),
                    last_price=self._safe_float(s.get("pl")),
                    close_price=self._safe_float(s.get("pc")),
                    yesterday_price=self._safe_float(s.get("py")),
                    nav_issue=self._safe_float(s.get("psubtran")),
                    nav_redeem=self._safe_float(s.get("predtran")),
                )
                if entry.symbol:  # فقط نمادهای با نماد معتبر
                    entries.append(entry)
            except Exception as e:
                logger.warning(f"Failed to build entry for {s.get('l18', 'unknown')}: {e}")
        
        logger.info(f"Built {len(entries)} fund entries")
        return entries
    
    def deduplicate(self, entries: list[FundUniverseEntry]) -> list[FundUniverseEntry]:
        """حذف duplicate بر اساس unique_key (ISIN > ins_code > symbol)."""
        seen = set()
        unique = []
        for e in entries:
            key = e.unique_key
            if key not in seen:
                seen.add(key)
                unique.append(e)
            else:
                self.stats["deduplicated"] += 1
                logger.debug(f"Duplicate removed: {e.symbol} ({key})")
        
        logger.info(f"After deduplication: {len(unique)} unique funds (removed {self.stats['deduplicated']})")
        return unique
    
    def get_universe(self) -> list[FundUniverseEntry]:
        """متد اصلی: دریافت Universe کامل و تمیز."""
        # 1. Fetch
        all_symbols = self.fetch_all_symbols()
        
        # 2. Classify
        fund_symbols, insurance_symbols, other_symbols = self.classify_symbols(all_symbols)
        
        # 3. Build entries
        entries = self.build_entries(fund_symbols)
        
        # 4. Deduplicate
        unique_entries = self.deduplicate(entries)
        
        self.stats["final_count"] = len(unique_entries)
        
        # Log insurance symbols for audit
        if insurance_symbols:
            ins_names = [s.get("l18", "") for s in insurance_symbols[:10]]
            logger.info(f"Insurance symbols excluded (sample): {ins_names}")
        
        return unique_entries
    
    def get_stats(self) -> dict[str, int]:
        return self.stats.copy()
    
    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        if val is None or val == "":
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None


def build_fund_universe() -> list[FundUniverseEntry]:
    """Convenience function."""
    builder = FundUniverseBuilder()
    return builder.get_universe()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    universe = build_fund_universe()
    print(f"\n=== FUND UNIVERSE ===")
    print(f"Total valid funds: {len(universe)}")
    for u in universe[:10]:
        print(f"  {u.symbol} | {u.name} | ISIN={u.isin} | Board={u.board}")
    print("...")
    builder = FundUniverseBuilder()
    print(f"\nStats: {builder.get_stats()}")