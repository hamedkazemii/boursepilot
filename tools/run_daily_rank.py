#!/usr/bin/env python3
"""اجرای پایپ‌لاین روزانه رنکینگ صندوقچی."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline.daily_rank import DailyRankPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily fund ranking pipeline")
    parser.add_argument("--limit", type=int, default=0, help="limit funds for debug")
    parser.add_argument("--nav", action="store_true", help="fetch NAV for each fund")
    parser.add_argument("--no-nav", action="store_true", help="do not fetch NAV")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    fetch_nav = None
    if args.nav:
        fetch_nav = True
    elif args.no_nav:
        fetch_nav = False

    pipe = DailyRankPipeline(fetch_nav=fetch_nav)
    limit = args.limit if args.limit > 0 else None
    result = pipe.run(limit=limit)

    print("=" * 50)
    print("DONE count=", result["count"])
    print("rank_path=", result["rank_path"])
    print("text_path=", result["text_path"])
    print("-" * 50)
    print(result["text"][:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
