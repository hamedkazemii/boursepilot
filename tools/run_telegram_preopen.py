#!/usr/bin/env python3
"""اسکن پیش‌سفارش و ارسال به کانال تلگرام."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.classification.fund_type import classify_fund_type
from core.preopen.analyzer import PreopenAnalyzer
from services.discovery.fund_catalog import FundCatalogService
from services.snapshot.store import SnapshotStore
from services.telegram_publisher import TelegramPublisher, format_preopen_telegram


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    catalog = FundCatalogService()
    funds = catalog.discover()
    if args.limit > 0:
        funds = funds[: args.limit]
    types = {q.symbol: classify_fund_type(q) for q in funds}
    signals = PreopenAnalyzer().rank(funds, fund_types=types)

    store = SnapshotStore()
    payload = {"count": len(signals), "signals": [s.to_dict() for s in signals]}
    store.save_json("preopen_scan", payload)
    store.save_latest("preopen_scan", payload)
    text = format_preopen_telegram(signals)
    (store.base_dir / "latest" / "preopen_scan.txt").write_text(text, encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/preopen_scan.txt").write_text(text, encoding="utf-8")

    if args.dry_run:
        print(text)
        return 0

    ok = TelegramPublisher().publish_preopen(signals)
    print("telegram_sent" if ok else "telegram_failed", "count=", len(signals))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
