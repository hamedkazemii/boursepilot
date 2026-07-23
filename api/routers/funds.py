from fastapi import APIRouter

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get("/{symbol}")
def fund_detail(symbol: str):

    return {
        "symbol": symbol,
        "name": symbol,
        "score": 0,
        "recommendation": "neutral",
        "reasons": [],
        "explain_fa":
        "تحلیل تفصیلی پس از اتصال موتور رتبه بندی نمایش داده می‌شود.",
        "indicators": {
            "rsi14": None,
            "ema20": None,
            "sharpe": None
        }
    }


@router.get("/{symbol}/history")
def fund_history(symbol: str, days:int=120):

    return {
        "symbol": symbol,
        "days": days,
        "series": []
    }


@router.get("/{symbol}/indicators")
def fund_indicators(symbol:str):

    return {
        "symbol":symbol,
        "indicators":{}
    }

