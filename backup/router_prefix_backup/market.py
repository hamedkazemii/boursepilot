from fastapi import APIRouter

router = APIRouter()


@router.get("/market/summary")
def market_summary():
    return {
        "status": "ok",
        "message": "market summary endpoint"
    }
