#!/usr/bin/env python3
"""فقط کشف و اسنپ‌شات کاتالوگ صندوق‌ها."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.discovery.fund_catalog import FundCatalogService


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    svc = FundCatalogService()
    funds, payload, path = svc.discover_and_save()
    print("funds", len(funds))
    print("types", payload.get("type_counts"))
    print("saved", path)
    for item in payload.get("funds", [])[:10]:
        print(f"  {item['symbol']:12} {item['fund_type']:12} value={item.get('value')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
