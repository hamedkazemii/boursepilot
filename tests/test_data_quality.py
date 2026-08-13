"""
Unit tests for DataQualityGate
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

from core.pipeline.data_quality import (
    DataQualityGate,
    DataQualityReport,
    MetricQuality,
    FreshnessClass,
    DataQuality,
    ConfidenceLevel,
    OverallQuality,
    FRESHNESS_POLICY,
)


class TestDataQualityGate:
    """Tests for DataQualityGate"""

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.get_symbol.return_value = Mock(
            last_price=1000.0,
            volume=100000,
            value=100000000,
            change_close_pct=1.5,
            change_last_pct=1.2,
        )
        provider.get_nav.return_value = Mock(redeem_nav=990.0)
        provider.get_transactions.return_value = []
        provider.get_shareholders.return_value = []
        provider.get_candlestick.return_value = []
        provider.get_codal_announcements.return_value = []
        return provider

    @pytest.fixture
    def mock_repository(self):
        repo = Mock()
        repo.get_fund_id.return_value = 1
        repo.get_history.return_value = [
            {"trade_date": "2026-08-10", "close": 1000},
            {"trade_date": "2026-08-09", "close": 990},
        ]
        repo.cache_get.return_value = None
        repo.db = Mock()
        repo.db.transaction.return_value.__enter__ = Mock(return_value=Mock(
            execute=Mock(return_value=Mock(fetchone=Mock(return_value=None)))
        ))
        repo.db.transaction.return_value.__exit__ = Mock(return_value=None)
        return repo

    def test_check_fresh_metrics(self, mock_provider, mock_repository):
        """Test that fresh metrics are marked as FRESH with HIGH confidence"""
        gate = DataQualityGate(provider=mock_provider, repository=mock_repository)
        report = gate.check("فولاد", ["price", "nav", "volume"])

        assert report.overall_quality == OverallQuality.COMPLETE
        assert report.overall_confidence == ConfidenceLevel.HIGH
        assert "price" not in report.missing_metrics
        assert "nav" not in report.missing_metrics
        assert "volume" not in report.missing_metrics

        price_mq = report.metrics["price"]
        assert price_mq.quality == DataQuality.FRESH
        assert price_mq.confidence == ConfidenceLevel.HIGH
        assert price_mq.source == "BRS_API"
        assert not price_mq.fallback_used

        nav_mq = report.metrics["nav"]
        assert nav_mq.quality == DataQuality.FRESH
        assert nav_mq.confidence == ConfidenceLevel.HIGH

    def test_check_stale_metrics_fallback(self, mock_provider, mock_repository):
        """Test that stale metrics use fallback with reduced confidence"""
        # Make provider fail to force fallback to DB
        mock_provider.get_symbol.side_effect = Exception("BRS unavailable")
        mock_provider.get_nav.side_effect = Exception("BRS unavailable")

        # Provide cached data for price only, not for nav
        def cache_get_side_effect(key):
            if "price" in key:
                return '{"last_price": 990}'
            return None
        
        mock_repository.cache_get.side_effect = cache_get_side_effect

        gate = DataQualityGate(provider=mock_provider, repository=mock_repository)
        report = gate.check("فولاد", ["price", "nav"])

        # price should use fallback, nav should be missing
        assert "nav" in report.missing_metrics
        assert "price" not in report.missing_metrics
        assert report.metrics["price"].fallback_used == True
        assert report.metrics["price"].fallback_source == "DB_cache"
        assert report.metrics["nav"].quality == DataQuality.MISSING

    def test_check_missing_symbol(self, mock_provider, mock_repository):
        """Test handling of unknown symbol"""
        mock_repository.get_fund_id.return_value = None

        gate = DataQualityGate(provider=mock_provider, repository=mock_repository)
        report = gate.check("UNKNOWN", ["price", "nav"])

        assert report.overall_quality == OverallQuality.UNAVAILABLE
        assert "Symbol UNKNOWN not in valid fund universe" in report.warnings

    def test_check_price_nav_alignment(self, mock_provider, mock_repository):
        """Test price/NAV timestamp alignment check"""
        # Create provider that returns data with different timestamps
        mock_provider.get_symbol.return_value = Mock(last_price=1000.0)
        mock_provider.get_nav.return_value = Mock(redeem_nav=990.0)

        gate = DataQualityGate(provider=mock_provider, repository=mock_repository)
        report = gate.check("فولاد", ["price", "nav"])

        # Should not have alignment conflict for same-time fetches
        assert "price_nav_alignment" not in report.conflicts

    def test_freshness_policy_contains_required_metrics(self):
        """Test that FRESHNESS_POLICY has all required metric definitions"""
        required = ["price", "nav", "volume", "orderbook", "change_pct"]
        for metric in required:
            assert metric in FRESHNESS_POLICY
            assert "freshness_class" in FRESHNESS_POLICY[metric]
            assert "ttl_seconds" in FRESHNESS_POLICY[metric]
            assert "source_endpoint" in FRESHNESS_POLICY[metric]

    def test_freshness_class_values(self):
        """Test FreshnessClass enum values"""
        assert FreshnessClass.REALTIME.value == "realtime"
        assert FreshnessClass.LIVE.value == "live"
        assert FreshnessClass.INTRADAY.value == "intraday"
        assert FreshnessClass.END_OF_DAY.value == "end_of_day"
        assert FreshnessClass.EVENT.value == "event"
        assert FreshnessClass.PERIODIC.value == "periodic"
        assert FreshnessClass.HISTORICAL.value == "historical"

    def test_data_quality_values(self):
        """Test DataQuality enum values"""
        assert DataQuality.FRESH.value == "fresh"
        assert DataQuality.STALE.value == "stale"
        assert DataQuality.MISSING.value == "missing"
        assert DataQuality.CONFLICT.value == "conflict"
        assert DataQuality.PARTIAL.value == "partial"
        assert DataQuality.UNAVAILABLE.value == "unavailable"

    def test_confidence_levels(self):
        """Test ConfidenceLevel enum values"""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_overall_quality_levels(self):
        """Test OverallQuality enum values"""
        assert OverallQuality.COMPLETE.value == "complete"
        assert OverallQuality.PARTIAL.value == "partial"
        assert OverallQuality.INSUFFICIENT.value == "insufficient"
        assert OverallQuality.STALE.value == "stale"
        assert OverallQuality.UNAVAILABLE.value == "unavailable"

    def test_metric_quality_creation(self):
        """Test MetricQuality dataclass creation"""
        mq = MetricQuality(
            metric_name="price",
            source="BRS_API",
            freshness_class=FreshnessClass.REALTIME,
            ttl_seconds=300,
        )
        assert mq.metric_name == "price"
        assert mq.source == "BRS_API"
        assert mq.freshness_class == FreshnessClass.REALTIME
        assert mq.ttl_seconds == 300
        assert mq.quality == DataQuality.UNAVAILABLE
        assert mq.confidence == ConfidenceLevel.LOW

    def test_data_quality_report_finalize(self):
        """Test DataQualityReport.finalize() calculation"""
        report = DataQualityReport(symbol="TEST", requested_at=datetime.now())
        now = datetime.now()

        # Add fresh metrics (age < ttl)
        for i in range(7):
            mq = MetricQuality(
                metric_name=f"metric_{i}",
                source="BRS_API",
                freshness_class=FreshnessClass.REALTIME,
                ttl_seconds=300,
            )
            mq.fetched_at = now
            mq.age_seconds = 100  # fresh
            mq.quality = DataQuality.FRESH
            mq.confidence = ConfidenceLevel.HIGH
            report.add_metric(mq)

        # Add stale metrics (age > ttl)
        for i in range(3):
            mq = MetricQuality(
                metric_name=f"stale_{i}",
                source="DB",
                freshness_class=FreshnessClass.END_OF_DAY,
                ttl_seconds=86400,
            )
            mq.fetched_at = now - timedelta(hours=25)
            mq.age_seconds = 90000  # stale
            mq.quality = DataQuality.STALE
            mq.confidence = ConfidenceLevel.LOW
            mq.fallback_used = True
            report.add_metric(mq)

        report.finalize()

        assert report.overall_quality == OverallQuality.STALE
        assert report.overall_confidence == ConfidenceLevel.MEDIUM  # 7/10 = 0.7 (threshold is > 0.7)

    def test_report_to_dict(self, mock_provider, mock_repository):
        """Test DataQualityReport.to_dict() serialization"""
        gate = DataQualityGate(provider=mock_provider, repository=mock_repository)
        report = gate.check("فولاد", ["price"])

        d = report.to_dict()

        assert d["symbol"] == "فولاد"
        assert "overall_quality" in d
        assert "overall_confidence" in d
        assert "metrics" in d
        assert "price" in d["metrics"]


class TestDataQualityGateIntegration:
    """Integration tests with real components"""

    @pytest.fixture
    def gate_with_real_components(self):
        """Create gate with real provider/repository (requires config)"""
        # This test requires actual BRS credentials and DB
        # Skip if not configured
        pytest.skip("Integration test requires live BRS API and DB")

    def test_real_basic_check(self, gate_with_real_components):
        """Test with real BRS data"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])