import pytest
from unittest.mock import MagicMock
from core.universe.valuation_resolver import ValuationPriceResolver, PriceSource

# Fixture: 100 units, last=15100, close=15000
QTY = 100
LP = 15100
CP = 15000

@pytest.fixture
def resolver_fixture():
    provider = MagicMock()
    # Mock live market last_price
    quote = MagicMock()
    quote.last_price = LP
    provider.get_symbol.return_value = quote
    
    # Mock DB history for close_price
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = [CP, "2026-08-18"]
    
    return ValuationPriceResolver(provider, db)

def test_market_open_valuation(resolver_fixture):
    """Test V2 Contract: OPEN MARKET -> last_price"""
    res = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=True)
    assert res.price == LP
    assert res.source == PriceSource.LAST
    assert QTY * res.price == 1510000

def test_market_closed_valuation(resolver_fixture):
    """Test V2 Contract: CLOSED MARKET -> close_price"""
    res = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=False)
    assert res.price == CP
    assert res.source == PriceSource.CLOSE
    assert QTY * res.price == 1500000

def test_field_isolation(resolver_fixture):
    """Verify last_price and close_price are distinct sources."""
    open_p = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=True)
    closed_p = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=False)
    
    assert open_p.price == LP
    assert closed_p.price == CP
    assert open_p.price != closed_p.price
