#!/usr/bin/env python3
"""نقطه ورود سازگار صندوقچی.

قبلاً RealMarketScanner/TSETMC بود.
الان به مسیر BRS + رنکینگ/تلگرام وصل است.
"""

from __future__ import annotations

import logging
import os
import sys


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    print("=" * 60)
    print("صندوقچی — daily entrypoint")
    print("=" * 60)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if token and chat:
        from tools.run_telegram_rank import main as rank_main
        sys.argv = ["run_telegram_rank.py", "--no-nav"]
        if os.getenv("FETCH_NAV_IN_DAILY_RANK", "").lower() in {"1", "true", "yes", "on"}:
            sys.argv = ["run_telegram_rank.py", "--nav"]
        return int(rank_main() or 0)

    from core.pipeline.daily_rank import DailyRankPipeline

    fetch_nav = os.getenv("FETCH_NAV_IN_DAILY_RANK", "false").lower() in {"1", "true", "yes", "on"}
    result = DailyRankPipeline(fetch_nav=fetch_nav).run()
    print(result.get("text", "")[:2000])
    print("count=", result.get("count"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
