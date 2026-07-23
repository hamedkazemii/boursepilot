#!/usr/bin/env python3
"""همگام‌سازی روزانه تاریخچه صندوق‌ها در SQLite."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.history.engine import HistoryEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="BoursePilot History Engine sync")
    parser.add_argument("--limit", type=int, default=0, help="محدود کردن تعداد صندوق‌ها")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--db", type=str, default="", help="مسیر SQLite اختیاری")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.db:
        from core.database.connection import Database
        from core.history.repository import HistoryRepository

        db = Database(args.db)
        engine = HistoryEngine(db=db, repo=HistoryRepository(db))
    else:
        engine = HistoryEngine()

    result = engine.sync_daily(
        limit=args.limit if args.limit > 0 else None,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print("stats:", json.dumps(engine.stats(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
