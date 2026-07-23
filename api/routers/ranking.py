from fastapi import APIRouter

router = APIRouter()


@router.get("/ranking/today")
def ranking_today():

    return {
        "items": [],
        "message": "Ranking adapter pending"
    }


@router.get("/ranking/top")
def ranking_top(limit: int = 5):

    return {
        "limit": limit,
        "items": []
    }


@router.get("/ranking/worst")
def ranking_worst(limit: int = 5):

    return {
        "limit": limit,
        "items": []
    }
