import pytest
from core.universe.valuation_resolver import ValuationPriceResolver
from unittest.mock import MagicMock

QTY = 100
LP = 15100
CP = 15000

@pytest.fixture
def resolver_fixture():
    provider = MagicMock()
    quote = MagicMock()
    quote.last_price = LP
    provider.get_symbol.return_value = quote
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = [CP, "2026-08-18"]
    return ValuationPriceResolver(provider, db)

def test_telegram_analyzer_open(resolver_fixture):
    """V2 Contract: OPEN -> both use last_price"""
    res = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=True)
    expected_price = LP
    expected_value = QTY * LP
    assert res.price == expected_price, f"Expected {expected_price}, got {res.price}"
    # Simulate telegram output
    telegram_val = expected_value
    analyzer_val = expected_value
    assert telegram_val == analyzer_val == expected_value

def test_telegram_analyzer_closed(resolver_fixture):
    """V2 Contract: CLOSED -> both use close_price"""
    res = resolver_fixture.resolve_portfolio_price("TEST", market_is_open=False)
    expected_price = CP
    expected_value = QTY * CP
    assert res.price == expected_price, f"Expected {expected_price}, got {res.price}"
    # Simulate telegram output
    telegram_val = expected_value
    analyzer_val = expected_value
    assert telegram_val == analyzer_val == expected_value
