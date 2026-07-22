#!/usr/bin/env python3
"""اجرای رنکینگ روزانه و ارسال به کانال تلگرام."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pipeline.daily_rank import DailyRankPipeline
from core.scoring.models import FundAssessment
from services.telegram_publisher import TelegramPublisher


def assessments_from_payload(payload: dict) -> list[FundAssessment]:
    """بازسازی سبک FundAssessment از JSON پایپ‌لاین برای فرمت تلگرام."""
    from core.scoring.models import FactorScore

    out: list[FundAssessment] = []
    for row in payload.get("rankings") or []:
        factors = []
        for f in row.get("factors") or []:
            factors.append(
                FactorScore(
                    key=f.get("key", ""),
                    title=f.get("title", ""),
                    score=float(f.get("score") or 0),
                    label=f.get("label", ""),
                    reasons=tuple(f.get("reasons") or []),
                    metrics=f.get("metrics") or {},
                )
            )
        out.append(
            FundAssessment(
                symbol=row.get("symbol") or "",
                name=row.get("name") or "",
                fund_type=row.get("fund_type") or "",
                ins_code=str(row.get("ins_code") or ""),
                sector=row.get("sector"),
                final_score=float(row.get("final_score") or 0),
                recommendation=row.get("recommendation") or "neutral",
                recommendation_label=row.get("recommendation_label") or "",
                rank=row.get("rank"),
                factors=tuple(factors),
                summary_reasons=tuple(row.get("summary_reasons") or []),
                close_price=row.get("close_price"),
                last_price=row.get("last_price"),
                change_pct=row.get("change_pct"),
                volume=row.get("volume"),
                value=row.get("value"),
                issue_nav=row.get("issue_nav"),
                redeem_nav=row.get("redeem_nav"),
                premium_pct=row.get("premium_pct"),
                extras=row.get("extras") or {},
            )
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--nav", action="store_true")
    parser.add_argument("--no-nav", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="فقط چاپ، بدون ارسال")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    fetch_nav = True if args.nav else False if args.no_nav else None
    pipe = DailyRankPipeline(fetch_nav=fetch_nav)
    result = pipe.run(limit=args.limit if args.limit > 0 else None)
    payload = result["payload"]
    ranked = assessments_from_payload(payload)

    publisher = TelegramPublisher()
    if args.dry_run:
        from services.telegram_publisher import format_ranking_telegram
        print(format_ranking_telegram(ranked, meta=payload))
        return 0

    ok = publisher.publish_ranking(ranked, meta=payload)
    print("telegram_sent" if ok else "telegram_failed", "count=", result["count"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
