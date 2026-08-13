"""
Unit tests for TechnicalEngine
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.pipeline.technical import (
    TechnicalEngine,
    TrendModule,
    MomentumModule,
    VolatilityModule,
    VolumeModule,
    PriceStructureModule,
    TechnicalFact,
    TechnicalAnalysis,
    TechnicalModuleResult,
    TrendDirection,
    MomentumState,
    VolatilityRegime,
)
from core.pipeline.fund_identity import FundIdentity, FundType, HistoryAvailability


class TestTrendModule:
    """Tests for TrendModule"""

    @pytest.fixture
    def mock_repo(self):
        return Mock()

    @pytest.fixture
    def module(self, mock_repo):
        return TrendModule(history_repo=mock_repo)

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    @pytest.fixture
    def fund_identity_fixed_income(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.FIXED_INCOME
        return identity

    def test_analyze_sufficient_data(self, module, fund_identity_equity):
        """Test trend with sufficient price data"""
        prices = [100 + i * 0.5 for i in range(50)]  # upward trend
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-001")

        assert result.module_name == "trend"
        assert len(result.facts) >= 3  # sma_20, sma_50, current_price
        assert len(result.analyses) >= 2  # trend_direction, price_sma_distance
        assert result.overall_confidence > 0

        # Check trend direction is UP or STRONG_UP
        trend_analysis = next(a for a in result.analyses if a.name == "trend_direction")
        assert trend_analysis.value in [TrendDirection.UP.value, TrendDirection.STRONG_UP.value]

    def test_analyze_downward_trend(self, module, fund_identity_equity):
        """Test trend with downward prices"""
        prices = [150 - i * 0.5 for i in range(50)]  # downward trend
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-002")

        trend_analysis = next(a for a in result.analyses if a.name == "trend_direction")
        assert trend_analysis.value in [TrendDirection.DOWN.value, TrendDirection.STRONG_DOWN.value]

    def test_analyze_neutral_trend(self, module, fund_identity_equity):
        """Test trend with flat prices"""
        prices = [100.0 for _ in range(50)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-003")

        trend_analysis = next(a for a in result.analyses if a.name == "trend_direction")
        assert trend_analysis.value == TrendDirection.NEUTRAL.value

    def test_analyze_insufficient_data(self, module, fund_identity_equity):
        """Test trend with insufficient data (< 20 points)"""
        prices = [100 + i * 0.5 for i in range(10)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-004")

        trend_analysis = next(a for a in result.analyses if a.name == "trend_direction")
        assert trend_analysis.value == TrendDirection.UNKNOWN.value
        assert trend_analysis.confidence == 0.0

    def test_not_applicable_fund_type(self, module, fund_identity_fixed_income):
        """Test trend for fixed income fund (not applicable)"""
        # Fixed income doesn't have 'trend' in applicable metrics
        prices = [100 + i * 0.5 for i in range(50)]
        result = module.analyze("TEST", prices, FundType.FIXED_INCOME, fund_identity_fixed_income, "test-005")

        # Should still run (module doesn't check is_applicable internally)
        # The orchestrator handles is_applicable check
        assert result.module_name == "trend"


class TestMomentumModule:
    """Tests for MomentumModule"""

    @pytest.fixture
    def module(self):
        return MomentumModule()

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze_rsi(self, module, fund_identity_equity):
        """Test RSI calculation"""
        prices = [100 + i for i in range(30)]  # steadily increasing
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-001")

        assert result.module_name == "momentum"
        assert len(result.facts) >= 1
        assert len(result.analyses) >= 1

        rsi_fact = next(f for f in result.facts if f.name == "rsi_14")
        assert rsi_fact.value is not None
        assert 0 <= rsi_fact.value <= 100

        rsi_analysis = next(a for a in result.analyses if a.name == "rsi_state")
        assert rsi_analysis.value in [s.value for s in MomentumState]

    def test_analyze_insufficient_data(self, module, fund_identity_equity):
        """Test with insufficient data"""
        prices = [100 + i for i in range(10)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-002")

        rsi_analysis = next(a for a in result.analyses if a.name == "rsi_state")
        assert rsi_analysis.value == MomentumState.UNKNOWN.value
        assert rsi_analysis.confidence == 0.0

    def test_macd_calculation(self, module, fund_identity_equity):
        """Test MACD calculation"""
        prices = [100 + i * 0.5 for i in range(40)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-003")

        macd_fact = next((f for f in result.facts if f.name == "macd_line"), None)
        if macd_fact:
            assert macd_fact.value is not None
            macd_analysis = next((a for a in result.analyses if a.name == "macd_signal"), None)
            if macd_analysis:
                assert macd_analysis.value in ["bullish", "bearish"]


class TestVolatilityModule:
    """Tests for VolatilityModule"""

    @pytest.fixture
    def module(self):
        return VolatilityModule()

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze_volatility(self, module, fund_identity_equity):
        """Test volatility calculation"""
        prices = [100 + (i % 5 - 2) * 0.5 for i in range(50)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-001")

        assert result.module_name == "volatility"
        assert len(result.facts) >= 2
        assert len(result.analyses) >= 1

        vol_fact = next(f for f in result.facts if f.name == "volatility_20")
        assert vol_fact.value is not None
        assert vol_fact.value >= 0

        ann_vol_fact = next(f for f in result.facts if f.name == "annualized_volatility")
        assert ann_vol_fact.value is not None
        assert ann_vol_fact.value >= 0

        vol_analysis = next(a for a in result.analyses if a.name == "volatility_regime")
        assert vol_analysis.value in [r.value for r in VolatilityRegime]

    def test_max_drawdown(self, module, fund_identity_equity):
        """Test max drawdown calculation"""
        # Create a price series with a drawdown
        prices = [100] * 10 + [90] * 10 + [95] * 10 + [85] * 10 + [88] * 10
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-002")

        mdd_fact = next((f for f in result.facts if f.name == "max_drawdown_90"), None)
        if mdd_fact:
            assert mdd_fact.value is not None
            assert mdd_fact.value >= 0
            assert mdd_fact.value <= 100  # percentage

    def test_analyze_insufficient_data(self, module, fund_identity_equity):
        """Test with insufficient data"""
        prices = [100 + i for i in range(10)]
        result = module.analyze("TEST", prices, FundType.EQUITY, fund_identity_equity, "test-003")

        vol_analysis = next(a for a in result.analyses if a.name == "volatility_regime")
        assert vol_analysis.value == VolatilityRegime.UNKNOWN.value
        assert vol_analysis.confidence == 0.0


class TestVolumeModule:
    """Tests for VolumeModule"""

    @pytest.fixture
    def module(self):
        return VolumeModule()

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze_volume(self, module, fund_identity_equity):
        """Test volume analysis"""
        volumes = [10000 + i * 100 for i in range(30)]
        prices = [100 + i * 0.1 for i in range(30)]
        result = module.analyze("TEST", volumes, prices, FundType.EQUITY, fund_identity_equity, "test-001")

        assert result.module_name == "volume"
        assert len(result.facts) >= 2
        assert len(result.analyses) >= 1

        avg_vol_fact = next(f for f in result.facts if f.name == "avg_volume_20")
        assert avg_vol_fact.value is not None

        vol_ratio_fact = next(f for f in result.facts if f.name == "volume_ratio")
        assert vol_ratio_fact.value is not None

        vol_analysis = next(a for a in result.analyses if a.name == "volume_trend")
        assert vol_analysis.value in ["high", "normal", "low"]


class TestPriceStructureModule:
    """Tests for PriceStructureModule"""

    @pytest.fixture
    def module(self):
        return PriceStructureModule()

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_analyze_position_in_range(self, module, fund_identity_equity):
        """Test position in range analysis"""
        prices = [95 + i * 0.2 for i in range(60)]
        result = module.analyze("TEST", prices, fund_type=FundType.EQUITY, identity=fund_identity_equity, request_id="test-001")

        assert result.module_name == "price_structure"
        assert len(result.facts) >= 4
        assert len(result.analyses) >= 1

        pos_analysis = next(a for a in result.analyses if a.name == "position_in_range")
        assert pos_analysis.value in ["near_high", "near_low", "upper_half", "lower_half"]

    def test_analyze_insufficient_data(self, module, fund_identity_equity):
        """Test with insufficient data"""
        prices = [100 + i * 0.1 for i in range(30)]
        result = module.analyze("TEST", prices, fund_type=FundType.EQUITY, identity=fund_identity_equity, request_id="test-002")

        pos_analysis = next(a for a in result.analyses if a.name == "position_in_range")
        assert pos_analysis.value == "insufficient_data"
        assert pos_analysis.confidence == 0.0


class TestTechnicalEngine:
    """Integration tests for TechnicalEngine"""

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
        return TechnicalEngine(
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
        assert hasattr(engine, 'trend_module')
        assert hasattr(engine, 'momentum_module')
        assert hasattr(engine, 'volatility_module')
        assert hasattr(engine, 'volume_module')
        assert hasattr(engine, 'price_structure_module')

    def test_is_applicable_called(self, engine, fund_identity_manager):
        """Test that is_applicable is called for each module"""
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        
        # Mock repository to return empty history
        engine.repository = Mock()
        engine.repository.get_fund_id.return_value = None
        
        result = engine.analyze("TEST", identity, request_id="test-001")
        
        # Should call is_applicable for each metric
        assert fund_identity_manager.is_applicable.call_count >= 5
        assert result["symbol"] == "TEST"
        assert result["fund_type"] == "equity"
        assert "modules" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])