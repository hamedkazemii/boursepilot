#!/usr/bin/env python3
"""
اسموک‌تست زنده BRS برای صندوقچی.

نیاز:
  export BRS_API_KEY=...

اجرا از ریشه پروژه:
  python tools/brs_smoke_test.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# اجازه import از ریشه پروژه
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from services.providers.brs_provider import BrsProvider
from services.providers.exceptions import ProviderError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("brs_smoke")


def main() -> int:
    if not settings.BRS_API_KEY:
        print("BRS_API_KEY تنظیم نشده است.")
        return 2

    print("=" * 60)
    print(f"{settings.PRODUCT_NAME} — BRS smoke test")
    print("base:", settings.BRS_BASE_URL)
    print("key_len:", len(settings.BRS_API_KEY))
    print("=" * 60)

    provider = BrsProvider()

    try:
        funds = provider.get_fund_symbols()
        print(f"fund-like count: {len(funds)}")
        if not funds:
            print("هیچ صندوق‌مانندی پیدا نشد.")
            return 1

        # نمایش چند نمونه
        print("\nTOP sample funds:")
        for q in funds[:10]:
            print(
                f"  {q.symbol:12} | close={q.close_price} | "
                f"chg={q.change_close_pct} | vol={q.volume} | {q.sector}"
            )

        sample_symbol = "عیار"
        # اگر عیار نبود اولی
        if not any(f.symbol == sample_symbol for f in funds):
            sample_symbol = funds[0].symbol

        print("\nSymbol detail:", sample_symbol)
        detail = provider.get_symbol(sample_symbol)
        print(
            f"  last={detail.last_price} close={detail.close_price} "
            f"bid_qty={detail.orderbook.total_bid_quantity} "
            f"ask_qty={detail.orderbook.total_ask_quantity}"
        )

        print("\nNAV:", sample_symbol)
        nav = provider.get_nav(sample_symbol)
        print(f"  issue={nav.issue_nav} redeem={nav.redeem_nav} date={nav.date}")

        if detail.close_price and nav.redeem_nav:
            premium = (detail.close_price - nav.redeem_nav) / nav.redeem_nav * 100
            print(f"  premium/discount vs redeem NAV: {premium:.3f}%")

        print("\nShareholders head:")
        holders = provider.get_shareholders(sample_symbol)
        for h in holders[:5]:
            print(f"  {h.percent:6.3f}% | {h.name[:40]}")

        print("\nSMOKE OK")
        return 0

    except ProviderError as exc:
        logger.exception("provider error")
        print("SMOKE FAILED:", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
