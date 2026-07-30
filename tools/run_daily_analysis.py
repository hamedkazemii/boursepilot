#!/usr/bin/env python3
"""اجرای پایپلاین کامل تحلیل روزانه صندوقچی."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ai.advisor import AIAdvisor
from core.pipeline.daily_analysis import DailyAnalysisPipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--nav", action="store_true")
    parser.add_argument("--no-seed", action="store_true", help="بدون seed تاریخچه")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    pipe = DailyAnalysisPipeline(
        fetch_nav=bool(args.nav),
        allow_offline_seed=not args.no_seed,
    )
    result = pipe.run(limit=args.limit if args.limit > 0 else None)
    payload = result["payload"]

    # daily AI learning
    try:
        ai = AIAdvisor()
        lessons = ai.learn_from_ranking(result["ranked"], market=payload.get("market"))
        payload["ai_lessons"] = lessons
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("ai learn failed: %s", exc)

    print(
        json.dumps(
            {
                "source": result["source"],
                "count": result["count"],
                "quality": payload.get("quality"),
                "top": [a["symbol"] + f"({a['final_score']})" for a in payload.get("top", [])],
                "worst": [a["symbol"] + f"({a['final_score']})" for a in payload.get("worst", [])],
                "market": payload.get("market"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    sane = bool((payload.get("quality") or {}).get("sane"))
    return 0 if sane else 2


if __name__ == "__main__":
    raise SystemExit(main())
