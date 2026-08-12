"""
Unit tests for FundIdentityManager
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from core.pipeline.fund_identity import FundIdentityManager, FundType, AssetClass, HistoryAvailability


def _make_db_with_universe_row(row: dict):
    """ساخت یک mock Database که یک ردیف fund_universe برمی‌گرداند"""
    db = Mock()
    # Default for history count
    db.fetchone.return_value = {"cnt": 60}
    
    def make_ctx_for_query(query_result):
        ctx = MagicMock()
        ctx.__enter__.return_value = MagicMock(
            execute=MagicMock(return_value=MagicMock(fetchone=MagicMock(return_value=query_result))),
        )
        ctx.__exit__.return_value = None
        return ctx
    
    # First call returns fund_universe row, second returns history count
    call_count = [0]
    def transaction_side_effect():
        call_count[0] += 1
        if call_count[0] == 1:
            return make_ctx_for_query(row)
        else:
            return make_ctx_for_query({"cnt": 60})
    
    db.transaction.side_effect = transaction_side_effect
    return db


def _make_db_with_history_count(count: int):
    """ساخت mock Database که تعداد ردیف‌های history را برمی‌گرداند"""
    db = Mock()
    
    # Create a mock connection that returns the count
    mock_conn = Mock()
    mock_conn.execute.return_value = Mock(
        fetchone=Mock(return_value={"cnt": count})
    )
    
    # Context manager for transaction
    ctx = MagicMock()
    ctx.__enter__.return_value = mock_conn
    ctx.__exit__.return_value = None
    db.transaction.return_value = ctx
    
    # Also handle direct fetchone calls
    db.fetchone.return_value = {"cnt": count}
    return db


class TestFundIdentityManager:
    """Tests for FundIdentityManager"""

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.get_symbol.return_value = Mock(
            is_fund_like=True,
            sector="سهامی",
            board="",
            name="صندوق سهامی",
            ins_code="10001",
            symbol="FUND001",
        )
        return provider

    def test_identify_not_found(self, mock_provider):
        """Symbol not in DB, not in BRS → UNKNOWN"""
        repo = Mock()
        repo.get_fund_id.return_value = None
        repo.db = Mock()

        manager = FundIdentityManager(provider=None, repository=repo)
        result = manager.identify("UNKNOWN_SYMBOL_123")

        assert result.symbol == "UNKNOWN_SYMBOL_123"
        assert result.fund_type == FundType.UNKNOWN
        assert result.history_availability == HistoryAvailability.NONE

    def test_identify_from_universe_equity(self, mock_provider):
        """fund_universe row → EQUITY fund"""
        row = {
            "symbol": "FUND001",
            "name": "صندوق سهامی",
            "cs": "سهامی",
            "cs_id": 1,
            "cs_sub": "",
            "board": "صندوق‌های سهامی",
            "is_active": True,
            "ins_code": "10001",
        }
        db = _make_db_with_universe_row(row)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 1

        manager = FundIdentityManager(provider=mock_provider, repository=repo)
        result = manager.identify("FUND001")

        assert result.fund_type == FundType.EQUITY
        assert result.is_active == True
        assert result.history_availability == HistoryAvailability.PARTIAL

    def test_identify_from_universe_gold(self, mock_provider):
        """fund_universe row → GOLD fund"""
        row = {
            "symbol": "GOLD001",
            "name": "صندوق طلا",
            "cs": "طلا",
            "cs_id": 2,
            "cs_sub": "",
            "board": "صندوق‌های طلا",
            "is_active": True,
            "ins_code": "10002",
        }
        db = _make_db_with_universe_row(row)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 2

        manager = FundIdentityManager(provider=mock_provider, repository=repo)
        result = manager.identify("GOLD001")

        assert result.fund_type == FundType.GOLD

    def test_identify_from_universe_fixed_income(self, mock_provider):
        """fund_universe row → FIXED_INCOME fund"""
        row = {
            "symbol": "FI001",
            "name": "صندوق درآمد ثابت",
            "cs": "درآمد ثابت",
            "cs_id": 3,
            "cs_sub": "",
            "board": "صندوق‌های درآمد ثابت",
            "is_active": True,
            "ins_code": "10003",
        }
        db = _make_db_with_universe_row(row)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 3

        manager = FundIdentityManager(provider=mock_provider, repository=repo)
        result = manager.identify("FI001")

        assert result.fund_type == FundType.FIXED_INCOME

    def test_is_applicable(self, mock_provider):
        """Test is_applicable for all fund types"""
        manager = FundIdentityManager(provider=mock_provider, repository=None)

        # Equity
        assert manager.is_applicable("rsi", FundType.EQUITY) == True
        assert manager.is_applicable("yield", FundType.EQUITY) == False

        # Fixed income
        assert manager.is_applicable("yield", FundType.FIXED_INCOME) == True
        assert manager.is_applicable("rsi", FundType.FIXED_INCOME) == False

        # Gold
        assert manager.is_applicable("gold_exposure", FundType.GOLD) == True
        assert manager.is_applicable("yield", FundType.GOLD) == False

        # Commodity
        assert manager.is_applicable("commodity_exposure", FundType.COMMODITY) == True

        # Mixed
        assert manager.is_applicable("equity_exposure", FundType.MIXED) == True
        assert manager.is_applicable("sector_concentration", FundType.MIXED) == True

        # Index
        assert manager.is_applicable("index_exposure", FundType.INDEX) == True

        # Leveraged
        assert manager.is_applicable("leverage_exposure", FundType.LEVERAGED) == True

        # Derivative
        assert manager.is_applicable("path_dependency", FundType.DERIVATIVE) == True

        # Unknown — only universal
        assert manager.is_applicable("price", FundType.UNKNOWN) == True
        assert manager.is_applicable("nav", FundType.UNKNOWN) == True
        assert manager.is_applicable("rsi", FundType.UNKNOWN) == False

        # Unknown metric name
        assert manager.is_applicable("not_a_metric", FundType.EQUITY) == False

    def test_classify_from_text(self, mock_provider):
        """Test fund type classification from text"""
        manager = FundIdentityManager(provider=None, repository=None)

        assert manager._classify_from_text("اهرم صندوق") == FundType.LEVERAGED
        assert manager._classify_from_text("اهرمی") == FundType.LEVERAGED
        assert manager._classify_from_text("طلا") == FundType.GOLD
        assert manager._classify_from_text("زر") == FundType.GOLD
        assert manager._classify_from_text("درآمد ثابت") == FundType.FIXED_INCOME
        assert manager._classify_from_text("ثابت") == FundType.FIXED_INCOME
        assert manager._classify_from_text("کالایی") == FundType.COMMODITY
        assert manager._classify_from_text("نقره") == FundType.COMMODITY
        assert manager._classify_from_text("شاخصی") == FundType.INDEX
        assert manager._classify_from_text("شاخص") == FundType.INDEX
        assert manager._classify_from_text("مختلط") == FundType.MIXED
        assert manager._classify_from_text("سهامی") == FundType.EQUITY
        assert manager._classify_from_text("سهام") == FundType.EQUITY
        assert manager._classify_from_text("مشتقه") == FundType.DERIVATIVE
        assert manager._classify_from_text("چیزی دیگر") == FundType.UNKNOWN

    def test_history_availability_full(self, mock_provider):
        """Test history availability detection (full)"""
        db = _make_db_with_history_count(200)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 1

        manager = FundIdentityManager(
            provider=mock_provider,
            repository=repo,
            history_count_threshold_full=180,
            history_count_threshold_partial=45,
        )

        assert manager._check_history_availability("FUND001") == HistoryAvailability.FULL

    def test_history_availability_partial(self, mock_provider):
        """Test history availability detection (partial)"""
        db = _make_db_with_history_count(60)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 1

        manager = FundIdentityManager(
            provider=mock_provider,
            repository=repo,
            history_count_threshold_full=180,
            history_count_threshold_partial=45,
        )

        assert manager._check_history_availability("FUND001") == HistoryAvailability.PARTIAL

    def test_history_availability_insufficient(self, mock_provider):
        """Test history availability detection (insufficient)"""
        db = _make_db_with_history_count(10)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 1

        manager = FundIdentityManager(
            provider=mock_provider,
            repository=repo,
            history_count_threshold_full=180,
            history_count_threshold_partial=45,
        )

        assert manager._check_history_availability("FUND001") == HistoryAvailability.INSUFFICIENT

    def test_history_availability_none(self, mock_provider):
        """Test history availability detection (none)"""
        db = _make_db_with_history_count(0)
        repo = Mock()
        repo.db = db
        repo.get_fund_id.return_value = 1

        manager = FundIdentityManager(
            provider=mock_provider,
            repository=repo,
            history_count_threshold_full=180,
            history_count_threshold_partial=45,
        )

        assert manager._check_history_availability("FUND001") == HistoryAvailability.NONE

    def test_applicable_metrics(self, mock_provider):
        """Test applicable metrics per fund type"""
        manager = FundIdentityManager(provider=mock_provider, repository=None)

        # Equity
        equity_metrics = manager._compute_applicable_metrics(FundType.EQUITY)
        assert "rsi" in equity_metrics
        assert "macd" in equity_metrics
        assert "price" in equity_metrics
        assert "nav" in equity_metrics
        assert "yield" not in equity_metrics
        assert "gold_exposure" not in equity_metrics

        # Fixed income
        fi_metrics = manager._compute_applicable_metrics(FundType.FIXED_INCOME)
        assert "yield" in fi_metrics
        assert "duration" in fi_metrics
        assert "maturity" in fi_metrics
        assert "price" in fi_metrics
        assert "rsi" not in fi_metrics

        # Gold
        gold_metrics = manager._compute_applicable_metrics(FundType.GOLD)
        assert "gold_exposure" in gold_metrics
        assert "fx_sensitivity" in gold_metrics
        assert "price" in gold_metrics

        # Unknown
        unknown_metrics = manager._compute_applicable_metrics(FundType.UNKNOWN)
        assert "price" in unknown_metrics
        assert "nav" in unknown_metrics
        assert "rsi" not in unknown_metrics

    def test_asset_class_mapping(self, mock_provider):
        """Test asset_class mapping"""
        manager = FundIdentityManager(provider=mock_provider, repository=None)

        assert manager._asset_class_for(FundType.EQUITY) == AssetClass.EQUITY
        assert manager._asset_class_for(FundType.GOLD) == AssetClass.GOLD
        assert manager._asset_class_for(FundType.UNKNOWN) == AssetClass.UNKNOWN

    def test_strategy_description(self, mock_provider):
        """Test strategy descriptions per fund type"""
        manager = FundIdentityManager(provider=mock_provider, repository=None)

        assert "سهام" in manager._strategy_for(FundType.EQUITY)
        assert "اوراق" in manager._strategy_for(FundType.FIXED_INCOME)
        assert "طلا" in manager._strategy_for(FundType.GOLD)

    def test_to_dict(self, mock_provider):
        """Test FundIdentity.to_dict()"""
        manager = FundIdentityManager(provider=None, repository=None)
        identity = manager.identify("UNKNOWN")

        d = identity.to_dict()
        assert "symbol" in d
        assert "fund_type" in d
        assert "applicable_metrics" in d
        assert "history_availability" in d
        assert "identified_at" in d


class TestFundIdentityManagerIntegration:
    """Integration tests"""

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.get_symbol.return_value = Mock(
            is_fund_like=True,
            sector="مختلط",  # maps to MIXED
            board="",
            name="صندوق مختلط",
            ins_code="10001",
            symbol="FUND001",
        )
        return provider

    def test_identify_from_brs(self, mock_provider):
        """Identification from BRS when not in DB"""
        repo = Mock()
        repo.get_fund_id.return_value = None
        repo.db = Mock()

        manager = FundIdentityManager(provider=mock_provider, repository=repo)
        identity = manager.identify("FUND001", request_id="test-brs")

        assert identity.symbol == "FUND001"
        assert identity.fund_type == FundType.MIXED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])