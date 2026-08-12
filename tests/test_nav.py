"""
Unit tests for NAVEngine
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from core.pipeline.nav import (
    NAVEngine,
    NAVModuleResult,
    NAVFact,
    NAVAnalysis,
    AlignmentStatus,
    PremiumDiscountCategory,
)
from core.pipeline.fund_identity import FundIdentity, FundType


class TestNAVEngine:
    """Tests for NAVEngine"""

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
        return NAVEngine(
            provider=mock_provider,
            repository=mock_repo,
            data_quality_gate=mock_dq_gate,
            fund_identity_manager=fund_identity_manager,
        )

    @pytest.fixture
    def fund_identity_equity(self):
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.EQUITY
        return identity

    def test_aligned_price_nav(self, engine, fund_identity_equity):
        """Test premium/discount calculation with aligned timestamps"""
        # Mock price data
        price_mock = Mock()
        price_mock.last_price = 110.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        # Mock NAV data
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-001")
        
        assert result["symbol"] == "TEST"
        assert result["alignment_status"] == AlignmentStatus.ALIGNED.value
        assert result["alignment_seconds"] == 0
        assert result["overall_confidence"] > 0
        
        # Check premium/discount calculation: (110-100)/100 * 100 = 10%
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.HIGH_PREMIUM.value
        assert "10.00%" in premium_discount["reasoning"] or "10.0%" in premium_discount["reasoning"]

    def test_misaligned_timestamps(self, engine, fund_identity_equity):
        """Test handling of misaligned timestamps (> 5 minutes)"""
        price_mock = Mock()
        price_mock.last_price = 110.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:10:00"  # 10 minutes difference
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-002")
        
        assert result["alignment_status"] == AlignmentStatus.MISALIGNED.value
        assert result["alignment_seconds"] == 600  # 10 minutes
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.UNAVAILABLE.value
        assert premium_discount["confidence"] == 0.0

    def test_missing_price(self, engine, fund_identity_equity):
        """Test handling of missing price"""
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = Mock(last_price=None)
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-003")
        
        assert result["alignment_status"] == AlignmentStatus.PRICE_MISSING.value
        assert result["alignment_seconds"] is None
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.UNAVAILABLE.value

    def test_missing_nav(self, engine, fund_identity_equity):
        """Test handling of missing NAV"""
        price_mock = Mock()
        price_mock.last_price = 110.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = Mock(redeem_nav=None)
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-004")
        
        assert result["alignment_status"] == AlignmentStatus.NAV_MISSING.value
        assert result["alignment_seconds"] is None

    def test_both_missing(self, engine, fund_identity_equity):
        """Test handling of both price and NAV missing"""
        engine.provider.get_symbol.return_value = Mock(last_price=None)
        engine.provider.get_nav.return_value = Mock(redeem_nav=None)
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-005")
        
        assert result["alignment_status"] == AlignmentStatus.BOTH_MISSING.value

    def test_discount_calculation(self, engine, fund_identity_equity):
        """Test discount calculation (price < NAV)"""
        price_mock = Mock()
        price_mock.last_price = 95.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-006")
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.DISCOUNT.value
        assert "دیسکانت" in premium_discount["reasoning"]

    def test_deep_discount(self, engine, fund_identity_equity):
        """Test deep discount (< -5%)"""
        price_mock = Mock()
        price_mock.last_price = 90.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-007")
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.DEEP_DISCOUNT.value

    def test_near_par(self, engine, fund_identity_equity):
        """Test near par (-1% to +1%)"""
        price_mock = Mock()
        price_mock.last_price = 100.5
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-008")
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.NEAR_PAR.value

    def test_extreme_premium(self, engine, fund_identity_equity):
        """Test extreme premium (> 15%)"""
        price_mock = Mock()
        price_mock.last_price = 120.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-009")
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.EXTREME_PREMIUM.value

    def test_not_applicable_fund_type(self, engine, fund_identity_manager):
        """Test not applicable fund type"""
        fund_identity_manager.is_applicable.return_value = False
        
        identity = FundIdentity(symbol="TEST")
        identity.fund_type = FundType.DERIVATIVE
        
        result = engine.analyze("TEST", identity, request_id="test-010")
        
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == "not_applicable"
        assert "قابل اجرا نیست" in premium_discount["reasoning"]

    def test_uses_issue_nav_fallback(self, engine, fund_identity_equity):
        """Test fallback to issue_nav when redeem_nav not available"""
        price_mock = Mock()
        price_mock.last_price = 110.0
        price_mock.date = "2026-08-10"
        price_mock.time = "10:00:00"
        
        nav_mock = Mock()
        nav_mock.redeem_nav = None
        nav_mock.issue_nav = 100.0
        nav_mock.date = "2026-08-10"
        nav_mock.time = "10:00:00"
        
        engine.provider.get_symbol.return_value = price_mock
        engine.provider.get_nav.return_value = nav_mock
        
        result = engine.analyze("TEST", fund_identity_equity, request_id="test-011")
        
        assert result["alignment_status"] == AlignmentStatus.ALIGNED.value
        premium_discount = next(a for a in result["analyses"] if a["name"] == "premium_discount")
        assert premium_discount["value"] == PremiumDiscountCategory.HIGH_PREMIUM.value


class TestAlignmentStatus:
    """Test alignment status enum"""
    
    def test_alignment_statuses(self):
        assert AlignmentStatus.ALIGNED.value == "aligned"
        assert AlignmentStatus.MISALIGNED.value == "misaligned"
        assert AlignmentStatus.PRICE_MISSING.value == "price_missing"
        assert AlignmentStatus.NAV_MISSING.value == "nav_missing"
        assert AlignmentStatus.BOTH_MISSING.value == "both_missing"
        assert AlignmentStatus.UNKNOWN.value == "unknown"


class TestPremiumDiscountCategory:
    """Test premium discount categories"""
    
    def test_categories(self):
        assert PremiumDiscountCategory.DEEP_DISCOUNT.value == "deep_discount"
        assert PremiumDiscountCategory.DISCOUNT.value == "discount"
        assert PremiumDiscountCategory.NEAR_PAR.value == "near_par"
        assert PremiumDiscountCategory.PREMIUM.value == "premium"
        assert PremiumDiscountCategory.HIGH_PREMIUM.value == "high_premium"
        assert PremiumDiscountCategory.EXTREME_PREMIUM.value == "extreme_premium"
        assert PremiumDiscountCategory.UNAVAILABLE.value == "unavailable"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])