from fastapi import APIRouter

router = APIRouter()


@router.get("/market/summary")
def market_summary():

    return {
        "source": "pending",
        "message": "Connected to pipeline in next stage"
    }
