from fastapi import APIRouter
from api.services.report_reader import load_ranking

router = APIRouter()


@router.get("/funds")
def funds():

    data = load_ranking()

    return {
        "items": data.get("items", [])
    }


@router.get("/funds/{symbol}")
def fund_detail(symbol:str):

    data = load_ranking()

    for item in data.get("items", []):

        if item.get("symbol") == symbol:
            return item

    return {
        "symbol": symbol,
        "found": False
    }
