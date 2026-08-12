"""
Unit tests for FundamentalEngine
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.pipeline.fundamental import (
    FundamentalEngine,
    EquityFundamentalModule,
    FixedIncomeFundamentalModule,
    GoldFundamentalModule,
    IndexFundamentalModule,
    LeveragedFundamentalModule,
    UniversalFundamentalModule,
    FundamentalFact,
    FundamentalAnalysis,
    FundamentalModuleResult,
    FundamentalMetricType,
)
from core.pipeline.fund_identity import FundIdentity, FundType


class TestEquityFundamentalModule:
    """Tests for EquityFundamentalModule"""

    @pytest.fixture
    def module(self):
        return EquityFundamentalModule()

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze(self, module, fund_identity_equity):
        """Test equity fundamental analysis"""
        result = module.analyze("TEST", fund_identity_equity, request_id="test-001")
        
        assert result.module_name == "equity_fundamental"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1
        
        # Should indicate data unavailable
        fact = result.facts[0]
        assert fact.name == "equity_metrics_available"
        assert fact.value is False
        
        analysis = result.analyses[0]
        assert analysis.name == "valuation_assessment"
        assert analysis.value == "data_unavailable"
        assert analysis.confidence == 0.0


class TestFixedIncomeFundamentalModule:
    """Tests for FixedIncomeFundamentalModule"""

    @pytest.fixture
    def module(self):
        return FixedIncomeFundamentalModule()

    @pytest.fixture
    def fund_identity_fixed_income(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.FIXED_INCOME
        return identity

    def test_analyze(self, module, fund_identity_fixed_income):
        """Test fixed income fundamental analysis"""
        result = module.analyze("TEST", fund_identity_fixed_income, request_id="test-001")
        
        assert result.module_name == "fixed_income_fundamental"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1
        
        fact = result.facts[0]
        assert fact.name == "fixed_income_metrics_available"
        assert fact.value is False
        
        analysis = result.analyses[0]
        assert analysis.name == "yield_assessment"
        assert analysis.value == "data_unavailable"
        assert analysis.confidence == 0.0


class TestGoldFundamentalModule:
    """Tests for GoldFundamentalModule"""

    @pytest.fixture
    def module(self):
        return GoldFundamentalModule()

    @pytest.fixture
    def fund_identity_gold(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.GOLD
        return identity

    def test_analyze(self, module, fund_identity_gold):
        """Test gold fundamental analysis"""
        result = module.analyze("TEST", fund_identity_gold, request_id="test-001")
        
        assert result.module_name == "gold_fundamental"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1
        
        fact = result.facts[0]
        assert fact.name == "gold_exposure_available"
        assert fact.value is False
        
        analysis = result.analyses[0]
        assert analysis.name == "exposure_assessment"
        assert analysis.value == "data_unavailable"
        assert analysis.confidence == 0.0


class TestIndexFundamentalModule:
    """Tests for IndexFundamentalModule"""

    @pytest.fixture
    def module(self):
        return IndexFundamentalModule()

    @pytest.fixture
    def fund_identity_index(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.INDEX
        return identity

    def test_analyze(self, module, fund_identity_index):
        """Test index fundamental analysis"""
        result = module.analyze("TEST", fund_identity_index, request_id="test-001")
        
        assert result.module_name == "index_fundamental"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1
        
        fact = result.facts[0]
        assert fact.name == "tracking_metrics_available"
        assert fact.value is False
        
        analysis = result.analyses[0]
        assert analysis.name == "tracking_assessment"
        assert analysis.value == "data_unavailable"
        assert analysis.confidence == 0.0


class TestLeveragedFundamentalModule:
    """Tests for LeveragedFundamentalModule"""

    @pytest.fixture
    def module(self):
        return LeveragedFundamentalModule()

    @pytest.fixture
    def fund_identity_leveraged(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.LEVERAGED
        return identity

    def test_analyze(self, module, fund_identity_leveraged):
        """Test leveraged fundamental analysis"""
        result = module.analyze("TEST", fund_identity_leveraged, request_id="test-001")
        
        assert result.module_name == "leveraged_fundamental"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1
        
        fact = result.facts[0]
        assert fact.name == "leverage_metrics_available"
        assert fact.value is False
        
        analysis = result.analyses[0]
        assert analysis.name == "leverage_assessment"
        assert analysis.value == "data_unavailable"
        assert analysis.confidence == 0.0


class TestUniversalFundamentalModule:
    """Tests for UniversalFundamentalModule"""

    @pytest.fixture
    def module(self):
        return UniversalFundamentalModule()

    @pytest.fixture
    def fund_identity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze(self, module, fund_identity):
        """Test universal fundamental analysis"""
        result = module.analyze("TEST", fund_identity, request_id="test-001")
        
        assert result.module_name == "universal_fundamental"
        assert len(result.facts) >= 2
        assert len(result.analyses) >= 2
        
        # Check liquidity proxy
        liquidity_fact = next(f for f in result.facts if f.name == "liquidity_proxy_available")
        assert liquidity_fact.value is True
        assert liquidity_fact.metric_type == FundamentalMetricType.LIQUIDITY
        
        # Check fund size proxy
        size_fact = next(f for f in result.facts if f.name == "fund_size_proxy_available")
        assert size_fact.value is False
        
        # Check analyses
        liq_analysis = next(a for a in result.analyses if a.name == "liquidity_assessment")
        assert liq_analysis.value == "proxy_only"
        
        size_analysis = next(a for a in result.analyses if a.name == "size_assessment")
        assert size_analysis.value == "data_unavailable"


class TestFundamentalEngine:
    """Integration tests for FundamentalEngine"""

    @pytest.fixture
    def mock_provider(self):
        return Mock()

    @pytest.fixture
    def mock_repo(self):
        return Mock()

    @pytest.fixture
    def mock_dq_gate(self):
        return Mock()

    @pytest.fixture
    def fund_identity_manager(self):
        mgr = Mock()
        mgr.is_applicable.return_value = True
        return mgr

    @pytest.fixture
    def engine(self, mock_provider, mock_repo, mock_dq_gate, fund_identity_manager):
        return FundamentalEngine(
            provider=mock_provider,
            repository=mock_repo,
            data_quality_gate=mock_dq_gate,
            fund_identity_manager=fund_identity_manager,
        )

    def test_engine_initialization(self, engine):
        """Test engine initializes correctly"""
        assert engine.provider is not None
        assert engine.repository is not None
        assert engine.fund_identity_manager is not None
        assert hasattr(engine, 'equity_module')
        assert hasattr(engine, 'fixed_income_module')
        assert hasattr(engine, 'gold_module')
        assert hasattr(engine, 'index_module')
        assert hasattr(engine, 'leveraged_module')
        assert hasattr(engine, 'universal_module')

    def test_analyze_equity(self, engine):
        """Test equity fund analysis"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        
        result = engine.analyze("TEST", identity, request_id="test-001")
        
        assert result["symbol"] == "TEST"
        assert result["fund_type"] == "equity"
        assert "modules" in result
        assert "universal" in result["modules"]
        assert "equity" in result["modules"]
        assert result["total_facts"] > 0
        assert result["total_analyses"] > 0

    def test_analyze_fixed_income(self, engine):
        """Test fixed income fund analysis"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.FIXED_INCOME
        
        result = engine.analyze("TEST", identity, request_id="test-002")
        
        assert result["fund_type"] == "fixed_income"
        assert "universal" in result["modules"]
        assert "fixed_income" in result["modules"]

    def test_analyze_gold(self, engine):
        """Test gold fund analysis"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.GOLD
        
        result = engine.analyze("TEST", identity, request_id="test-003")
        
        assert result["fund_type"] == "gold"
        assert "universal" in result["modules"]
        assert "gold" in result["modules"]

    def test_analyze_index(self, engine):
        """Test index fund analysis"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.INDEX
        
        result = engine.analyze("TEST", identity, request_id="test-004")
        
        assert result["fund_type"] == "index"
        assert "universal" in result["modules"]
        assert "index" in result["modules"]

    def test_analyze_leveraged(self, engine):
        """Test leveraged fund analysis"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.LEVERAGED
        
        result = engine.analyze("TEST", identity, request_id="test-005")
        
        assert result["fund_type"] == "leveraged"
        assert "universal" in result["modules"]
        assert "leveraged" in result["modules"]

    def test_analyze_unknown(self, engine):
        """Test unknown fund type - only universal"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.UNKNOWN
        
        result = engine.analyze("TEST", identity, request_id="test-006")
        
        assert result["fund_type"] == "unknown"
        assert "universal" in result["modules"]
        # Should not have a specific module
        assert len(result["modules"]) == 1  # only universal

    def test_is_applicable_called(self, engine, fund_identity_manager):
        """Test that is_applicable is called"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        
        result = engine.analyze("TEST", identity, request_id="test-007")
        
        # Should call is_applicable for relevant metrics
        assert fund_identity_manager.is_applicable.called


class TestFundamentalMetricType:
    """Test metric type enum"""
    
    def test_metric_types(self):
        assert FundamentalMetricType.VALUATION.value == "valuation"
        assert FundamentalMetricType.YIELD.value == "yield"
        assert FundamentalMetricType.CREDIT.value == "credit"
        assert FundamentalMetricType.EXPOSURE.value == "exposure"
        assert FundamentalMetricType.TRACKING.value == "tracking"
        assert FundamentalMetricType.LEVERAGE.value == "leverage"
        assert FundamentalMetricType.LIQUIDITY.value == "liquidity"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])