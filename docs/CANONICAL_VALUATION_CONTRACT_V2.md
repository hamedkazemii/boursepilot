# Canonical Valuation Contract V2

1. **Purpose**: Define deterministic portfolio valuation based on market state.
2. **SSoT**: `current_session()` from `core.market.hours`.
3. **Price Resolver**: `ValuationPriceResolver` (Only entry point).
4. **OPEN**: Valuation = quantity * last_price.
5. **CLOSED**: Valuation = quantity * close_price.
6. **Isolation**: `last_price` and `close_price` fields are independent and immutable through Sync pipeline.
7. **Rule**: Portfolio valuation MUST NOT bypass `ValuationPriceResolver`.
