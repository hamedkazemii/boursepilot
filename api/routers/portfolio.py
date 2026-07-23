from fastapi import APIRouter

from api.services.user_repository import (
    ensure_user,
    get_portfolio,
    add_item,
    delete_item
)


router = APIRouter(
    prefix="/api/v1",
    tags=["portfolio"]
)



@router.get("/me/portfolio")
def portfolio():

    user = ensure_user()

    return {
        "user": user,
        "items":
            get_portfolio(
                user["id"]
            )
    }



@router.post("/me/portfolio/items")
def create_item(item:dict):

    user = ensure_user()


    add_item(
        user["id"],
        item.get("symbol"),
        item.get("units",0),
        item.get("avg_price",0)
    )


    return {
        "success":True
    }



@router.delete("/me/portfolio/items/{symbol}")
def remove(symbol:str):

    user=ensure_user()


    delete_item(
        user["id"],
        symbol
    )


    return {
        "success":True
    }

