"""تست History Engine با SQLite موقت — بدون شبکه."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.database.connection import Database
from core.history.engine import HistoryEngine
from core.history.repository import HistoryRepository
from core.scoring.models import FactorScore, FundAssessment
from services.providers.models import (
    MoneyFlowSnapshot,
    NavData,
    OrderBookLevel,
    OrderBookSnapshot,
    SymbolQuote,
)


def _quote(symbol: str = "عیار", change: float = 1.2) -> SymbolQuote:
    return SymbolQuote(
        symbol=symbol,
        name=f"صندوق {symbol}",
        ins_code="123",
        sector="صندوق طلا",
        last_price=1000,
        close_price=1000,
        open_price=990,
        high=1010,
        low=980,
        volume=50000,
        value=5e10,
        change_close_pct=change,
        date="2026-07-23",
        orderbook=OrderBookSnapshot(
            bids=(OrderBookLevel("bid", 1, 999, 1000, 2),),
            asks=(OrderBookLevel("ask", 1, 1001, 800, 1),),
        ),
        money_flow=MoneyFlowSnapshot(
            buy_real_volume=30000,
            sell_real_volume=20000,
            buy_legal_volume=10000,
            sell_legal_volume=5000,
        ),
        is_fund_like=True,
    )


class FakeProvider:
    name = "fake"

    def __init__(self, quotes: list[SymbolQuote] | None = None) -> None:
        self.quotes = quotes or [_quote("عیار", 1.5), _quote("اهرم", -0.8), _quote("یاقوت", 0.2)]

    def get_fund_symbols(self, symbol_type=None):
        return list(self.quotes)

    def get_all_symbols(self, symbol_type=None):
        return list(self.quotes)

    def get_symbol(self, symbol: str) -> SymbolQuote:
        for q in self.quotes:
            if q.symbol == symbol:
                return q
        raise KeyError(symbol)

    def get_nav(self, symbol: str) -> NavData:
        return NavData(symbol=symbol, issue_nav=100, redeem_nav=99, date="2026-07-23")

    def get_shareholders(self, symbol: str):
        return []


class TestHistoryEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.db = Database(self.db_path)
        self.repo = HistoryRepository(self.db)
        self.provider = FakeProvider()
        self.engine = HistoryEngine(db=self.db, provider=self.provider, repo=self.repo)

    def tearDown(self) -> None:
        self.db.close()
        self.tmp.cleanup()

    def test_schema_tables(self) -> None:
        tables = {
            r["name"]
            for r in self.db.fetchall(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        for t in ("funds", "history", "nav_history", "market_snapshot", "daily_scores", "request_cache"):
            self.assertIn(t, tables)

    def test_sync_insert_and_incremental_update(self) -> None:
        r1 = self.engine.sync_daily()
        self.assertEqual(r1["funds"], 3)
        self.assertEqual(r1["history"]["inserted"], 3)
        self.assertEqual(self.repo.history_count(), 3)
        self.assertEqual(len(self.repo.list_funds()), 3)

        # second sync same day → update not insert
        r2 = self.engine.sync_daily()
        self.assertEqual(r2["history"]["inserted"], 0)
        self.assertEqual(r2["history"]["updated"], 3)
        self.assertEqual(self.repo.history_count(), 3)

    def test_get_series(self) -> None:
        self.engine.sync_daily()
        series = self.engine.get_series("عیار")
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["volume"], 50000)
        self.assertIsNotNone(series[0]["buy_real_volume"])

    def test_nav_and_scores(self) -> None:
        self.engine.sync_daily()
        nav = NavData(symbol="عیار", issue_nav=110, redeem_nav=100, date="2026-07-23")
        self.assertTrue(self.repo.upsert_nav("عیار", nav, market_price=99, premium_pct=-1.0))
        self.assertFalse(self.repo.upsert_nav("عیار", nav, market_price=99, premium_pct=-1.0))

        a = FundAssessment(
            symbol="عیار",
            name="صندوق عیار",
            fund_type="طلا",
            ins_code="123",
            sector="صندوق",
            final_score=81.0,
            recommendation="buy",
            recommendation_label="خرید",
            rank=1,
            factors=(
                FactorScore("liquidity", "نقدشوندگی", 80, "خوب", ("عمق مناسب",)),
            ),
            summary_reasons=("امتیاز نهایی 81", "نقدشوندگی خوب"),
            change_pct=1.5,
        )
        n = self.engine.persist_scores([a], score_date="2026-07-23")
        self.assertEqual(n, 1)
        row = self.db.fetchone("SELECT final_score, rank FROM daily_scores")
        self.assertEqual(float(row["final_score"]), 81.0)
        self.assertEqual(int(row["rank"]), 1)

    def test_request_cache(self) -> None:
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return {"ok": True, "v": calls["n"]}

        a = self.engine.cached_json("test", {"x": 1}, fetch)
        b = self.engine.cached_json("test", {"x": 1}, fetch)
        self.assertEqual(a["v"], 1)
        self.assertEqual(b["v"], 1)
        self.assertEqual(calls["n"], 1)


if __name__ == "__main__":
    unittest.main()
