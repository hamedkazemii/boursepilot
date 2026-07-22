"""رتبه‌بندی صندوق‌ها بر اساس امتیاز نهایی."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from core.scoring.models import FundAssessment


class FundRanker:
    def rank(self, assessments: Iterable[FundAssessment]) -> list[FundAssessment]:
        items = sorted(list(assessments), key=lambda a: a.final_score, reverse=True)
        ranked: list[FundAssessment] = []
        for i, a in enumerate(items, start=1):
            ranked.append(replace(a, rank=i))
        return ranked

    def by_type(self, ranked: list[FundAssessment]) -> dict[str, list[FundAssessment]]:
        groups: dict[str, list[FundAssessment]] = defaultdict(list)
        for a in ranked:
            groups[a.fund_type].append(a)
        # re-rank inside type display order already score sorted
        return dict(groups)

    def top(self, ranked: list[FundAssessment], n: int = 20) -> list[FundAssessment]:
        return ranked[: max(0, n)]

    def worst(self, ranked: list[FundAssessment], n: int = 10) -> list[FundAssessment]:
        if n <= 0:
            return []
        return list(reversed(ranked[-n:]))
