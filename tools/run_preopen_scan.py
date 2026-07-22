#!/usr/bin/env python3
"""اسکن پیش‌سفارش صندوق‌ها (برای جاب ۸:۴۵–۹)."""

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    catalog = FundCatalogService()
    funds = catalog.discover()
    if args.limit > 0:
        funds = funds[: args.limit]

    types = {q.symbol: classify_fund_type(q) for q in funds}
    analyzer = PreopenAnalyzer()
    signals = analyzer.rank(funds, fund_types=types)
    text = analyzer.to_report(signals)

    store = SnapshotStore()
    payload = {
        "count": len(signals),
        "signals": [s.to_dict() for s in signals],
    }
    path = store.save_json("preopen_scan", payload)
    store.save_latest("preopen_scan", payload)
    txt_path = path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")
    (store.base_dir / "latest" / "preopen_scan.txt").write_text(text, encoding="utf-8")
    Path("reports").mkdir(exist_ok=True)
    Path("reports/preopen_scan.txt").write_text(text, encoding="utf-8")

    print(text[:2000])
    print("saved", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
