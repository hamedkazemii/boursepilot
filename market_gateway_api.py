"""BoursePilot Market Gateway API.

Serves market data (symbols, funds, nav) from BRS provider with caching
and pagination. Runs on the Iran collector server (port 9000).
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware

from services.providers.factory import get_market_data_provider

app = FastAPI(title="BoursePilot Market Gateway")

app.add_middleware(GZipMiddleware, minimum_size=1000)

provider = get_market_data_provider()

_SYMBOL_CACHE: list | None = None
_FUND_CACHE: list | None = None


def get_symbols_cached():
    """Return all symbols, cached after first load."""
    global _SYMBOL_CACHE
    if _SYMBOL_CACHE is None:
        print("LOADING SYMBOL CACHE...")
        _SYMBOL_CACHE = provider.get_all_symbols()
        print("CACHE SIZE:", len(_SYMBOL_CACHE))
    return _SYMBOL_CACHE


def get_funds_cached():
    """Return fund-like symbols, cached after first load."""
    global _FUND_CACHE
    if _FUND_CACHE is None:
        print("LOADING FUND CACHE...")
        _FUND_CACHE = provider.get_fund_symbols()
        print("FUND CACHE SIZE:", len(_FUND_CACHE))
    return _FUND_CACHE


@app.get("/health")
def health():
    return {"status": "ok", "service": "market-gateway"}


@app.get("/symbols")
def symbols(limit: int = 100, offset: int = 0):
    rows = get_symbols_cached()
    rows = rows[offset:offset + limit]
    return [x.to_dict() for x in rows]


@app.get("/funds")
def funds(limit: int = 0, offset: int = 0):
    rows = get_funds_cached()
    if limit and limit > 0:
        rows = rows[offset:offset + limit]
    return [x.to_dict() for x in rows]


@app.get("/symbol")
def symbol_query(l18: str):
    return symbol(l18)


@app.get("/symbol/{symbol}")
def symbol(symbol: str):
    """Return symbol from gateway market cache."""
    rows = get_symbols_cached()
    for item in rows:
        if getattr(item, "symbol", None) == symbol:
            return item.to_dict()
    raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")


@app.get("/nav")
def nav(l18: str):
    """Return NAV for a symbol, or a clear error."""
    try:
        data = provider.get_nav(l18)
        if data is None:
            return {"error": "NAV not found", "symbol": l18}
        return data.to_dict() if hasattr(data, "to_dict") else data
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "symbol": l18}


@app.get("/shareholders")
def shareholders(l18: str):
    try:
        rows = provider.get_shareholders(l18)
        return [x.to_dict() for x in rows]
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "symbol": l18}
