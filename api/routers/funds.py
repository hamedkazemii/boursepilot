from fastapi import APIRouter


router = APIRouter()


@router.get("/funds")
def funds():

    return {
        "items": []
    }


@router.get("/funds/{symbol}")
def fund_detail(symbol: str):

    return {
        "symbol": symbol,
        "message": "Fund adapter pending"
    }
