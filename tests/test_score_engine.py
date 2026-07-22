"""تست موتور امتیاز و فاکتورها با fixture — بدون شبکه."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from core.pipeline.daily_rank import DailyRankPipeline
from core.preopen.analyzer import PreopenAnalyzer
from core.scoring.score_engine import ScoreEngine
from services.providers.brs_mapper import map_nav, map_symbol_quote
from services.snapshot.store import SnapshotStore

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "brs"


class FakeProvider:
    name = "fake"

    def __init__(self) -> None:
        rows = json.loads((FIXTURES / "all_symbols_sample.json").read_text(encoding="utf-8"))
        self.quotes = [map_symbol_quote(r) for r in rows if r.get("l18")]
        # mark only fund-like for discover
        self.funds = [q for q in self.quotes if q.is_fund_like]
        self.nav = map_nav("عیار", json.loads((FIXTURES / "nav_ayar.json").read_text(encoding="utf-8")))

    def get_all_symbols(self, symbol_type=None):
        return list(self.quotes)

    def get_fund_symbols(self, symbol_type=None):
        return list(self.funds)

    def get_symbol(self, symbol: str):
        for q in self.quotes:
            if q.symbol == symbol:
                return q
        raise KeyError(symbol)

    def get_nav(self, symbol: str):
        return self.nav

    def get_shareholders(self, symbol: str):
        return []


class TestScoreEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = FakeProvider()
        self.engine = ScoreEngine()

    def test_assess_ayar(self) -> None:
        q = next(x for x in self.provider.funds if x.symbol == "عیار")
        a = self.engine.assess(q, nav=self.provider.nav)
        self.assertEqual(a.symbol, "عیار")
        self.assertGreaterEqual(a.final_score, 0)
        self.assertLessEqual(a.final_score, 100)
        self.assertTrue(a.recommendation_label)
        self.assertGreaterEqual(len(a.factors), 5)
        self.assertTrue(a.summary_reasons)
        # premium should be computable
        self.assertIsNotNone(a.premium_pct)

    def test_pipeline_offline(self) -> None:
        store = SnapshotStore(base_dir=Path("data/snapshots_test"))
        pipe = DailyRankPipeline(provider=self.provider, store=store, fetch_nav=True)
        result = pipe.run()
        self.assertGreaterEqual(result["count"], 1)
        self.assertTrue(Path(result["rank_path"]).exists())
        self.assertTrue(Path(result["text_path"]).exists())
        # Persian text
        self.assertIn("رنکینگ", result["text"])

    def test_preopen(self) -> None:
        analyzer = PreopenAnalyzer()
        signals = analyzer.rank(self.provider.funds)
        self.assertEqual(len(signals), len(self.provider.funds))
        text = analyzer.to_report(signals)
        self.assertIn("پیش‌سفارش", text)


if __name__ == "__main__":
    unittest.main()
