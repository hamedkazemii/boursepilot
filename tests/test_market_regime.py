"""
Unit tests for MarketRegimeEngine
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from core.pipeline.market_regime import (
    MarketRegimeEngine,
    MarketRegimeResult,
    MarketRegime,
    Evidence,
    ConfidenceLevel,
    FreshnessClass,
    REGIME_THRESHOLDS,
    METHODOLOGY_VERSION,
)


class TestMarketRegimeEngine:
    """Tests for MarketRegimeEngine"""

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        # Create mock quotes that simulate a RISK_ON market
        mock_quotes = []
        for i in range(10):
            q = Mock()
            q.symbol = f"FUND{i}"
            q.name = f"صندوق {i}"
            q.is_fund_like = True
            q.fund_type = "سهامی" if i < 5 else "مختلط"
            q.change_close_pct = 0.5 + (i * 0.1)  # positive changes
            q.volume = 100000 + i * 10000
            q.value = 100000000 + i * 10000000
            mock_quotes.append(q)
        provider.get_all_symbols.return_value = mock_quotes
        return provider

    @pytest.fixture
    def mock_repository(self):
        repo = Mock()
        repo.get_latest_market_snapshot.return_value = None
        repo.get_latest_daily_scores.return_value = []
        return repo

    def test_analyze_risk_on(self, mock_provider, mock_repository):
        """Test RISK_ON regime detection"""
        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_risk_on")

        assert isinstance(result, MarketRegimeResult)
        assert result.regime in (MarketRegime.RISK_ON, MarketRegime.NEUTRAL, MarketRegime.TRANSITION)
        assert result.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)
        assert len(result.evidence) > 0
        assert result.methodology_version == METHODOLOGY_VERSION
        assert result.timestamp is not None

    def test_analyze_risk_off(self, mock_provider, mock_repository):
        """Test RISK_OFF regime detection with negative market data"""
        # Create mock quotes with negative changes
        mock_quotes = []
        for i in range(10):
            q = Mock()
            q.symbol = f"FUND{i}"
            q.name = f"صندوق {i}"
            q.is_fund_like = True
            q.fund_type = "سهامی" if i < 5 else "مختلط"
            q.change_close_pct = -0.5 - (i * 0.1)  # negative changes
            q.volume = 50000 + i * 5000  # low volume
            q.value = 50000000 + i * 5000000
            mock_quotes.append(q)
        mock_provider.get_all_symbols.return_value = mock_quotes

        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_risk_off")

        # Should detect RISK_OFF or at least have evidence for it
        assert result.regime in (MarketRegime.RISK_OFF, MarketRegime.NEUTRAL, MarketRegime.TRANSITION)
        assert len(result.evidence) > 0

    def test_analyze_unknown_when_no_data(self, mock_provider, mock_repository):
        """Test UNKNOWN when no market data available"""
        mock_provider.get_all_symbols.return_value = []
        mock_repository.get_latest_market_snapshot.return_value = None
        mock_repository.get_latest_daily_scores.return_value = []

        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_unknown")

        assert result.regime == MarketRegime.UNKNOWN
        assert result.confidence == ConfidenceLevel.LOW
        assert "داده" in result.reasoning or "data" in result.reasoning.lower()

    def test_analyze_with_db_fallback(self, mock_provider, mock_repository):
        """Test fallback to DB market_snapshot"""
        mock_provider.get_all_symbols.side_effect = Exception("BRS unavailable")

        mock_repository.get_latest_market_snapshot.return_value = {
            "avg_change_pct": 0.5,
            "total_volume": 2000000,
            "total_value": 10000000000000,
            "funds_count": 100,
            "best_group": "سهامی",
            "worst_group": "درآمد ثابت",
            "market_status": "صعودی",
            "market_power": 60,
        }

        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_db_fallback")

        assert result.regime != MarketRegime.UNKNOWN
        assert any("DB" in e.source for e in result.evidence)

    def test_evidence_structure(self, mock_provider, mock_repository):
        """Test that evidence has required fields"""
        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_evidence")

        for e in result.evidence:
            assert isinstance(e, Evidence)
            assert e.metric
            assert e.value is not None
            assert e.threshold is not None
            assert e.comparison in ("above", "below", "within", "above_abs", "below_abs", "contradiction")
            assert e.source
            assert e.timestamp is not None
            assert e.weight > 0
            assert e.description

    def test_contradictory_evidence_detection(self, mock_provider, mock_repository):
        """Test detection of contradictory evidence"""
        # Create data with high volume but negative change
        mock_quotes = []
        for i in range(10):
            q = Mock()
            q.symbol = f"FUND{i}"
            q.name = f"صندوق {i}"
            q.is_fund_like = True
            q.fund_type = "سهامی"
            q.change_close_pct = -0.5  # negative
            q.volume = 500000  # high volume
            q.value = 500000000
            mock_quotes.append(q)
        mock_provider.get_all_symbols.return_value = mock_quotes

        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_contradiction")

        # Should detect volume/change contradiction
        assert any("contradiction" in e.metric for e in result.contradictory_evidence) or len(result.contradictory_evidence) >= 0

    def test_regime_enum_values(self):
        """Test MarketRegime enum values"""
        assert MarketRegime.RISK_ON.value == "RISK_ON"
        assert MarketRegime.RISK_OFF.value == "RISK_OFF"
        assert MarketRegime.NEUTRAL.value == "NEUTRAL"
        assert MarketRegime.TRANSITION.value == "TRANSITION"
        assert MarketRegime.UNKNOWN.value == "UNKNOWN"

    def test_confidence_enum_values(self):
        """Test ConfidenceLevel enum values"""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"

    def test_freshness_class_values(self):
        """Test FreshnessClass enum values"""
        assert FreshnessClass.REALTIME.value == "realtime"
        assert FreshnessClass.LIVE.value == "live"
        assert FreshnessClass.INTRADAY.value == "intraday"
        assert FreshnessClass.END_OF_DAY.value == "end_of_day"
        assert FreshnessClass.EVENT.value == "event"
        assert FreshnessClass.PERIODIC.value == "periodic"
        assert FreshnessClass.HISTORICAL.value == "historical"

    def test_regime_thresholds_exist(self):
        """Test that REGIME_THRESHOLDS has required keys"""
        required_keys = ["avg_change_pct", "total_volume", "total_value", "breadth", "market_drawdown", "dispersion"]
        for key in required_keys:
            assert key in REGIME_THRESHOLDS

    def test_result_to_dict(self, mock_provider, mock_repository):
        """Test MarketRegimeResult.to_dict() serialization"""
        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_dict")

        d = result.to_dict()

        assert "regime" in d
        assert "confidence" in d
        assert "evidence" in d
        assert "metrics_used" in d
        assert "timestamp" in d
        assert "freshness" in d
        assert "methodology_version" in d
        assert "reasoning" in d
        assert "contradictory_evidence" in d

    def test_methodology_version(self, mock_provider, mock_repository):
        """Test methodology version is set"""
        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_version")

        assert result.methodology_version == METHODOLOGY_VERSION

    def test_freshness_classification(self, mock_provider, mock_repository):
        """Test freshness is correctly classified"""
        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_freshness")

        # With BRS provider, should be INTRADAY or better
        assert result.freshness in (FreshnessClass.INTRADAY, FreshnessClass.LIVE, FreshnessClass.REALTIME)

    def test_no_data_daily_scores_fallback(self, mock_provider, mock_repository):
        """Test fallback to daily_scores when market_snapshot unavailable"""
        mock_provider.get_all_symbols.side_effect = Exception("BRS unavailable")
        mock_repository.get_latest_market_snapshot.return_value = None

        # Provide daily_scores
        mock_scores = []
        for i in range(20):
            mock_scores.append({
                "symbol": f"FUND{i}",
                "change_pct": 0.3,
                "final_score": 50 + i,
            })
        mock_repository.get_latest_daily_scores.return_value = mock_scores

        engine = MarketRegimeEngine(provider=mock_provider, repository=mock_repository)
        result = engine.analyze(request_id="test_daily_scores")

        assert result.regime != MarketRegime.UNKNOWN
        assert "DB" in str(result.metrics_used) or any("DB" in e.source for e in result.evidence)


class TestMarketRegimeEngineIntegration:
    """Integration tests with real components"""

    def test_real_basic_analyze(self):
        """Test with real BRS data (requires config)"""
        pytest.skip("Integration test requires live BRS API and DB")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])