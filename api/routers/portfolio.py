from fastapi import APIRouter


router = APIRouter(
    prefix="/api/v1",
    tags=["portfolio"]
)


@router.get("/me/portfolio")
def portfolio():

    return {
        "total_value": 0,
        "profit_loss": 0,
        "items": []
    }


@router.post("/me/portfolio/items")
def add_item(item: dict):

    return {
        "success": True,
        "item": item
    }


@router.delete("/me/portfolio/items/{symbol}")
def delete_item(symbol: str):

    return {
        "success": True,
        "deleted": symbol
    }

