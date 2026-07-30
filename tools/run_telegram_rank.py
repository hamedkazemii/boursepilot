#!/usr/bin/env python3
"""رنکینگ روزانه هوشمند + ارسال تلگرام."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import settings
from core.ai.advisor import AIAdvisor
from core.pipeline.daily_analysis import DailyAnalysisPipeline
from services.telegram_publisher import TelegramPublisher


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--nav", action="store_true")
    parser.add_argument("--no-nav", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--smart", action="store_true", default=None)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--top", type=int, default=0)
    parser.add_argument("--worst", type=int, default=0)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    fetch_nav = True if args.nav else False if args.no_nav else False
    pipe = DailyAnalysisPipeline(fetch_nav=fetch_nav, allow_offline_seed=True)
    result = pipe.run(limit=args.limit if args.limit > 0 else None)
    ranked = result["ranked"]
    payload = result["payload"]

    try:
        AIAdvisor().learn_from_ranking(ranked, market=payload.get("market"))
    except Exception:
        pass

    smart = settings.TELEGRAM_SMART_REPORT if args.smart is None else True
    if args.compact:
        smart = False
    if args.smart:
        smart = True

    top_n = args.top if args.top > 0 else (settings.TELEGRAM_TOP_N if smart else 12)
    worst_n = args.worst if args.worst > 0 else (settings.TELEGRAM_WORST_N if smart else 6)

    # enforce meaningful top/worst from full universe
    top_n = min(top_n, max(1, len(ranked) // 4)) if len(ranked) >= 20 else min(top_n, 5)
    worst_n = min(worst_n, max(1, len(ranked) // 4)) if len(ranked) >= 20 else min(worst_n, 5)

    publisher = TelegramPublisher()
    if args.dry_run:
        if smart:
            from services.telegram_publisher import build_smart_morning_messages

            msgs = build_smart_morning_messages(ranked, meta=payload, top_n=top_n, worst_n=worst_n)
            for i, m in enumerate(msgs, 1):
                print(f"\n===== MESSAGE {i}/{len(msgs)} =====\n")
                print(m)
            q = payload.get("quality") or {}
            print(f"\n# quality={q} source={result['source']}")
        else:
            from services.telegram_publisher import format_ranking_telegram

            print(format_ranking_telegram(ranked, meta=payload, top_n=top_n, worst_n=worst_n))
        return 0

    ok = publisher.publish_ranking(
        ranked,
        meta=payload,
        top_n=top_n,
        worst_n=worst_n,
        smart=smart,
    )
    print(
        "telegram_sent" if ok else "telegram_failed",
        "count=",
        result["count"],
        "source=",
        result["source"],
        "sane=",
        (payload.get("quality") or {}).get("sane"),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
