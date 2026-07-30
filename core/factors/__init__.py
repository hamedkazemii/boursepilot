"""فاکتورهای تحلیلی صندوقچی."""

__all__ = [
    "score_liquidity",
    "score_orderbook_pressure",
    "score_money_flow",
    "score_momentum",
    "score_volume_value",
    "score_nav_premium",
]


def __getattr__(name: str):
    if name == "score_liquidity":
        from core.factors.liquidity import score_liquidity

        return score_liquidity
    if name == "score_orderbook_pressure":
        from core.factors.orderbook_pressure import score_orderbook_pressure

        return score_orderbook_pressure
    if name == "score_money_flow":
        from core.factors.money_flow import score_money_flow

        return score_money_flow
    if name == "score_momentum":
        from core.factors.momentum import score_momentum

        return score_momentum
    if name == "score_volume_value":
        from core.factors.volume_value import score_volume_value

        return score_volume_value
    if name == "score_nav_premium":
        from core.factors.nav_premium import score_nav_premium

        return score_nav_premium
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
