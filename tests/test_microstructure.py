"""
Unit tests for TabloKhaniEngine (Microstructure Analysis)
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.pipeline.microstructure import (
    TabloKhaniEngine,
    TabloKhaniReport,
    Fact,
    Analysis,
    OrderBookPressure,
    SpreadQuality,
    DepthQuality,
    MoneyFlowPressure,
)
from services.providers.models import OrderBookSnapshot, OrderBookLevel, MoneyFlowSnapshot, SymbolQuote


def _make_orderbook(
    bid_levels=None,
    ask_levels=None,
    best_bid_price=1000,
    best_ask_price=1005,
):
    """Create an OrderBookSnapshot for testing"""
    if bid_levels is None:
        bid_levels = [
            OrderBookLevel(side="bid", level=1, price=best_bid_price, quantity=50000, order_count=100),
            OrderBookLevel(side="bid", level=2, price=best_bid_price-1, quantity=30000, order_count=50),
            OrderBookLevel(side="bid", level=3, price=best_bid_price-2, quantity=20000, order_count=30),
        ]
    if ask_levels is None:
        ask_levels = [
            OrderBookLevel(side="ask", level=1, price=best_ask_price, quantity=40000, order_count=80),
            OrderBookLevel(side="ask", level=2, price=best_ask_price+1, quantity=35000, order_count=60),
            OrderBookLevel(side="ask", level=3, price=best_ask_price+2, quantity=25000, order_count=40),
        ]
    return OrderBookSnapshot(bids=tuple(bid_levels), asks=tuple(ask_levels))


def _make_money_flow(
    buy_real_vol=100000,
    buy_legal_vol=50000,
    sell_real_vol=30000,
    sell_legal_vol=20000,
):
    """Create a MoneyFlowSnapshot for testing"""
    return MoneyFlowSnapshot(
        buy_real_volume=buy_real_vol,
        buy_legal_volume=buy_legal_vol,
        sell_real_volume=sell_real_vol,
        sell_legal_volume=sell_legal_vol,
        buy_real_count=100,
        buy_legal_count=20,
        sell_real_count=80,
        sell_legal_count=15,
    )


def _make_quote(last_price=1002, volume=200000, value=200000000, trade_count=500, change_close_pct=1.5):
    """Create a SymbolQuote for testing"""
    return SymbolQuote(
        symbol="TEST",
        name="Test Fund",
        last_price=last_price,
        volume=volume,
        value=value,
        trade_count=trade_count,
        change_close_pct=change_close_pct,
        is_fund_like=True,
        ins_code="12345",
    )


class TestTabloKhaniEngine:
    """Tests for TabloKhaniEngine"""

    @pytest.fixture
    def engine(self):
        return TabloKhaniEngine(provider=None, repository=None)

    def test_analyze_with_full_data(self, engine):
        """Test full analysis with orderbook, money_flow, quote"""
        ob = _make_orderbook()
        mf = _make_money_flow()
        q = _make_quote()

        report = engine.analyze("TEST", request_id="test-001", orderbook=ob, money_flow=mf, quote=q)

        assert report.symbol == "TEST"
        assert report.request_id == "test-001"
        assert report.orderbook is not None
        assert report.money_flow is not None
        assert report.quote is not None

        # Check facts extracted
        fact_names = [f.name for f in report.facts]
        assert "best_bid_price" in fact_names
        assert "best_ask_price" in fact_names
        assert "total_bid_qty" in fact_names
        assert "total_ask_qty" in fact_names
        assert "spread_pct" in fact_names
        assert "mid_price" in fact_names
        assert "buy_real_vol" in fact_names
        assert "net_volume_flow" in fact_names
        assert "last_price" in fact_names
        assert "volume" in fact_names

        # Check analyses
        analysis_names = [a.name for a in report.analyses]
        assert "orderbook_pressure" in analysis_names
        assert "spread_quality" in analysis_names
        assert "depth_quality" in analysis_names
        assert "money_flow_pressure" in analysis_names
        assert "queue_status" in analysis_names

        # Check summary fields
        assert report.orderbook_pressure in OrderBookPressure
        assert report.spread_quality in SpreadQuality
        assert report.depth_quality in DepthQuality
        assert report.money_flow_pressure in MoneyFlowPressure

    def test_analyze_orderbook_pressure_strong_buy(self, engine):
        """Test orderbook pressure: strong buy (bid dominant)"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 80000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 10000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        # 80000 / 90000 = 0.88 >= 0.75 -> STRONG_BUY
        assert report.orderbook_pressure == OrderBookPressure.STRONG_BUY

        analysis = next(a for a in report.analyses if a.name == "orderbook_pressure")
        assert "فشار خرید قوی" in analysis.reasoning
        assert "bid_ratio=0.89" in analysis.reasoning

    def test_analyze_orderbook_pressure_buy(self, engine):
        """Test orderbook pressure: buy (bid > ask)"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 60000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 30000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        # 60000 / 90000 = 0.67 >= 0.6 -> BUY
        assert report.orderbook_pressure == OrderBookPressure.BUY

    def test_analyze_orderbook_pressure_neutral(self, engine):
        """Test orderbook pressure: neutral"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 50000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 50000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        # 50000 / 100000 = 0.5 -> NEUTRAL
        assert report.orderbook_pressure == OrderBookPressure.NEUTRAL

    def test_analyze_orderbook_pressure_sell(self, engine):
        """Test orderbook pressure: sell"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 30000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 60000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        # 30000 / 90000 = 0.33 -> SELL (between 0.25 and 0.4)
        assert report.orderbook_pressure == OrderBookPressure.SELL

    def test_analyze_orderbook_pressure_strong_sell(self, engine):
        """Test orderbook pressure: strong sell"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 10000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 80000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        # 10000 / 90000 = 0.11 <= 0.25 -> STRONG_SELL
        assert report.orderbook_pressure == OrderBookPressure.STRONG_SELL

    def test_analyze_orderbook_queue_buy(self, engine):
        """Test orderbook pressure: queue buy (best_ask_qty == 0)"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 50000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 0, 0)],  # Queue buy
        )
        report = engine.analyze("TEST", orderbook=ob)

        assert report.orderbook_pressure == OrderBookPressure.QUEUE_BUY

    def test_analyze_orderbook_queue_sell(self, engine):
        """Test orderbook pressure: queue sell (best_bid_qty == 0)"""
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 0, 0)],  # Queue sell
            ask_levels=[OrderBookLevel("ask", 1, 1005, 50000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)

        assert report.orderbook_pressure == OrderBookPressure.QUEUE_SELL

    def test_analyze_spread_quality_tight(self, engine):
        """Test spread quality: tight (<= 0.1%)"""
        ob = _make_orderbook(best_bid_price=1000, best_ask_price=1000.05)  # 0.05 / 1000 = 0.005%
        report = engine.analyze("TEST", orderbook=ob)

        assert report.spread_quality == SpreadQuality.TIGHT

    def test_analyze_spread_quality_normal(self, engine):
        """Test spread quality: normal (0.1% - 0.5%)"""
        ob = _make_orderbook(best_bid_price=1000, best_ask_price=1003)  # 3 / 1001.5 = 0.3%
        report = engine.analyze("TEST", orderbook=ob)

        assert report.spread_quality == SpreadQuality.NORMAL

    def test_analyze_spread_quality_wide(self, engine):
        """Test spread quality: wide (0.5% - 2%)"""
        ob = _make_orderbook(best_bid_price=1000, best_ask_price=1010)  # 10 / 1005 = 1%
        report = engine.analyze("TEST", orderbook=ob)

        assert report.spread_quality == SpreadQuality.WIDE

    def test_analyze_spread_quality_crossed(self, engine):
        """Test spread quality: crossed (> 2%)"""
        ob = _make_orderbook(best_bid_price=1000, best_ask_price=1030)  # 30 / 1015 = ~3%
        report = engine.analyze("TEST", orderbook=ob)

        assert report.spread_quality == SpreadQuality.CROSSED

    def test_analyze_depth_quality_deep(self, engine):
        """Test depth quality: deep (>= 8 levels, qty > 100000)"""
        bid_levels = [OrderBookLevel("bid", i, 1000-i, 50000, 50) for i in range(1, 6)]
        ask_levels = [OrderBookLevel("ask", i, 1005+i, 50000, 50) for i in range(1, 6)]
        ob = OrderBookSnapshot(bids=tuple(bid_levels), asks=tuple(ask_levels))  # 10 levels, 500000 total

        report = engine.analyze("TEST", orderbook=ob)

        assert report.depth_quality == DepthQuality.DEEP

    def test_analyze_depth_quality_moderate(self, engine):
        """Test depth quality: moderate (>= 5 levels, qty > 50000)"""
        bid_levels = [OrderBookLevel("bid", i, 1000-i, 15000, 50) for i in range(1, 4)]
        ask_levels = [OrderBookLevel("ask", i, 1005+i, 15000, 50) for i in range(1, 4)]
        ob = OrderBookSnapshot(bids=tuple(bid_levels), asks=tuple(ask_levels))  # 6 levels, 90000 total

        report = engine.analyze("TEST", orderbook=ob)

        assert report.depth_quality == DepthQuality.MODERATE

    def test_analyze_depth_quality_shallow(self, engine):
        """Test depth quality: shallow (>= 2 levels)"""
        bid_levels = [OrderBookLevel("bid", i, 1000-i, 10000, 10) for i in range(1, 3)]
        ask_levels = [OrderBookLevel("ask", i, 1005+i, 10000, 10) for i in range(1, 3)]
        ob = OrderBookSnapshot(bids=tuple(bid_levels), asks=tuple(ask_levels))  # 4 levels, 40000 total

        report = engine.analyze("TEST", orderbook=ob)

        assert report.depth_quality == DepthQuality.SHALLOW

    def test_analyze_money_flow_real_buy_dominant(self, engine):
        """Test money flow: real buy dominant"""
        mf = _make_money_flow(
            buy_real_vol=200000,
            buy_legal_vol=10000,
            sell_real_vol=5000,
            sell_legal_vol=3000,
        )
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure == MoneyFlowPressure.REAL_BUY_DOMINANT

    def test_analyze_money_flow_legal_buy_dominant(self, engine):
        """Test money flow: legal buy dominant"""
        mf = _make_money_flow(
            buy_real_vol=5000,
            buy_legal_vol=200000,
            sell_real_vol=3000,
            sell_legal_vol=2000,
        )
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure == MoneyFlowPressure.LEGAL_BUY_DOMINANT

    def test_analyze_money_flow_real_sell_dominant(self, engine):
        """Test money flow: real sell dominant"""
        mf = _make_money_flow(
            buy_real_vol=5000,
            buy_legal_vol=3000,
            sell_real_vol=200000,
            sell_legal_vol=10000,
        )
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure == MoneyFlowPressure.REAL_SELL_DOMINANT

    def test_analyze_money_flow_legal_sell_dominant(self, engine):
        """Test money flow: legal sell dominant"""
        mf = _make_money_flow(
            buy_real_vol=3000,
            buy_legal_vol=5000,
            sell_real_vol=10000,
            sell_legal_vol=200000,
        )
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure == MoneyFlowPressure.LEGAL_SELL_DOMINANT

    def test_analyze_money_flow_balanced(self, engine):
        """Test money flow: balanced"""
        mf = _make_money_flow(
            buy_real_vol=50000,
            buy_legal_vol=50000,
            sell_real_vol=50000,
            sell_legal_vol=50000,
        )
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure == MoneyFlowPressure.BALANCED

    def test_analyze_queue_status(self, engine):
        """Test queue status analysis"""
        # Queue buy
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 50000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 0, 0)],
        )
        report = engine.analyze("TEST", orderbook=ob)
        assert report.queue_status == "صف خرید"

        # Queue sell
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 0, 0)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 50000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)
        assert report.queue_status == "صف فروش"

        # No queue
        ob = _make_orderbook(
            bid_levels=[OrderBookLevel("bid", 1, 1000, 50000, 100)],
            ask_levels=[OrderBookLevel("ask", 1, 1005, 40000, 20)],
        )
        report = engine.analyze("TEST", orderbook=ob)
        assert report.queue_status == "بدون صف"

    def test_confidence_calculation(self, engine):
        """Test overall confidence calculation"""
        ob = _make_orderbook()
        mf = _make_money_flow()
        q = _make_quote()

        report = engine.analyze("TEST", orderbook=ob, money_flow=mf, quote=q)

        # All analyses with data should have confidence > 0
        assert report.overall_confidence > 0
        assert report.overall_confidence <= 1.0

        for analysis in report.analyses:
            assert analysis.confidence > 0
            assert analysis.confidence <= 1.0
            # Analyses with data should have fact_refs
            if analysis.confidence > 0.3:  # real data analyses
                assert len(analysis.fact_refs) > 0
            assert analysis.reasoning

    def test_fact_references_in_analysis(self, engine):
        """Test that analyses reference facts"""
        ob = _make_orderbook()
        report = engine.analyze("TEST", orderbook=ob)

        pressure_analysis = next(a for a in report.analyses if a.name == "orderbook_pressure")
        assert "total_bid_qty" in pressure_analysis.fact_refs
        assert "total_ask_qty" in pressure_analysis.fact_refs

    def test_report_to_dict(self, engine):
        """Test TabloKhaniReport.to_dict()"""
        ob = _make_orderbook()
        mf = _make_money_flow()
        q = _make_quote()

        report = engine.analyze("TEST", request_id="test-001", orderbook=ob, money_flow=mf, quote=q)
        d = report.to_dict()

        assert d["symbol"] == "TEST"
        assert d["request_id"] == "test-001"
        assert "facts" in d
        assert "analyses" in d
        assert "summary" in d
        assert "overall_confidence" in d

        summary = d["summary"]
        assert "orderbook_pressure" in summary
        assert "spread_quality" in summary
        assert "depth_quality" in summary
        assert "money_flow_pressure" in summary
        assert "queue_status" in summary

    def test_analyze_with_no_data(self, engine):
        """Test analysis with no data returns UNKNOWN"""
        report = engine.analyze("TEST")

        assert report.orderbook_pressure == OrderBookPressure.UNKNOWN
        assert report.spread_quality == SpreadQuality.UNKNOWN
        assert report.depth_quality == DepthQuality.UNKNOWN
        assert report.money_flow_pressure == MoneyFlowPressure.UNKNOWN
        assert report.queue_status == "نامشخص"
        assert report.overall_confidence == 0.0

    def test_partial_data_orderbook_only(self, engine):
        """Test with only orderbook data"""
        ob = _make_orderbook()
        report = engine.analyze("TEST", orderbook=ob)

        assert report.orderbook_pressure != OrderBookPressure.UNKNOWN
        assert report.spread_quality != SpreadQuality.UNKNOWN
        assert report.depth_quality != DepthQuality.UNKNOWN
        # Money flow should be UNKNOWN
        assert report.money_flow_pressure == MoneyFlowPressure.UNKNOWN

    def test_partial_data_money_flow_only(self, engine):
        """Test with only money flow data"""
        mf = _make_money_flow()
        report = engine.analyze("TEST", money_flow=mf)

        assert report.money_flow_pressure != MoneyFlowPressure.UNKNOWN
        assert report.orderbook_pressure == OrderBookPressure.UNKNOWN
        assert report.spread_quality == SpreadQuality.UNKNOWN
        assert report.depth_quality == DepthQuality.UNKNOWN

    def test_fact_confidence(self, engine):
        """Test fact confidence values"""
        ob = _make_orderbook()
        report = engine.analyze("TEST", orderbook=ob)

        for fact in report.facts:
            assert 0 <= fact.confidence <= 1
            assert fact.timestamp
            assert fact.source in ("orderbook", "money_flow", "quote")

    def test_analysis_methodology_version(self, engine):
        """Test analysis has methodology version"""
        ob = _make_orderbook()
        report = engine.analyze("TEST", orderbook=ob)

        for analysis in report.analyses:
            assert analysis.methodology_version == "v1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])