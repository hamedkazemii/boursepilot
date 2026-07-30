"""تست پایپلاین تحلیل روزانه و sanity رتبه‌بندی."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.database.connection import Database
from core.history.engine import HistoryEngine
from core.history.repository import HistoryRepository
from core.pipeline.daily_analysis import DailyAnalysisPipeline


class TestDailyAnalysis(unittest.TestCase):
    def test_pipeline_offline_sane_gap(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        db = Database(Path(tmp.name) / "x.db")
        hist = HistoryEngine(db=db, provider=None, repo=HistoryRepository(db))
        # provider None path
        pipe = DailyAnalysisPipeline(provider=None, history=hist, allow_offline_seed=True)
        pipe.provider = None
        pipe._provider_error = "test"
        # isolate snapshot dir
        from services.snapshot.store import SnapshotStore
        pipe.store = SnapshotStore(Path(tmp.name) / "snap")
        result = pipe.run(limit=30)
        ranked = result["ranked"]
        self.assertGreaterEqual(len(ranked), 20)
        self.assertGreater(ranked[0].final_score, ranked[-1].final_score + 8)
        top = {a.symbol for a in ranked[:5]}
        worst = {a.symbol for a in ranked[-5:]}
        self.assertTrue(top.isdisjoint(worst))
        q = result["payload"]["quality"]
        self.assertTrue(q["sane"])
        self.assertLess(q["worst5_avg"], q["top5_avg"])
        db.close()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
