from fastapi.middleware.gzip import GZipMiddleware
from fastapi import FastAPI
from services.providers.factory import get_market_data_provider

app=FastAPI(
    title="BoursePilot Market Gateway"
)



app.add_middleware(
    GZipMiddleware,
    minimum_size=1000
)


provider=get_market_data_provider()

_SYMBOL_CACHE = None

def get_symbols_cached():

    global _SYMBOL_CACHE

    if _SYMBOL_CACHE is None:
        print("LOADING SYMBOL CACHE...")
        _SYMBOL_CACHE = provider.get_all_symbols()
        print("CACHE SIZE:", len(_SYMBOL_CACHE))

    return _SYMBOL_CACHE



@app.get("/health")
def health():
    return {
        "status":"ok",
        "service":"market-gateway"
    }


@app.get("/symbols")
def symbols(limit: int = 100, offset: int = 0):

    rows = get_symbols_cached()

    rows = rows[offset:offset+limit]

    return [
        x.to_dict()
        for x in rows
    ]



@app.get("/symbol")
def symbol_query(l18: str):
    return symbol(l18)

@app.get("/funds")
def funds():

    rows = provider.get_fund_symbols()

    return [
        x.to_dict()
        for x in rows
    ]



@app.get("/symbol/{symbol}")
def symbol(symbol: str):
    """
    Return symbol from gateway market cache.
    Avoid direct BRS Symbol.php call.
    """

    rows = get_symbols_cached()

    for item in rows:
        if getattr(item, "symbol", None) == symbol:
            return item.to_dict()

    from fastapi import HTTPException

    raise HTTPException(
        status_code=404,
        detail=f"Symbol {symbol} not found"
    )


@app.get("/nav")
def nav(l18: str):
    return {"error":"NAV endpoint not implemented"}

@app.get("/shareholders")
def shareholders(l18: str):
    return {"error":"shareholders endpoint not implemented"}

