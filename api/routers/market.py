from fastapi import APIRouter

from api.services.data_reader import market_summary


router = APIRouter(
    prefix="/api/v1",
    tags=["market"]
)


@router.get("/market/summary")
def summary():

    return market_summary()

