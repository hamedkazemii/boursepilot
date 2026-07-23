from fastapi import APIRouter
from api.services.report_reader import (
    load_ranking,
    get_top,
    get_worst
)

router = APIRouter()


@router.get("/ranking/today")
def ranking_today():

    return load_ranking()


@router.get("/ranking/top")
def ranking_top(limit:int = 5):

    return {
        "items": get_top(limit)
    }


@router.get("/ranking/worst")
def ranking_worst(limit:int = 5):

    return {
        "items": get_worst(limit)
    }
