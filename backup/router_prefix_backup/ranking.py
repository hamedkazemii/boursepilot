from fastapi import APIRouter

from api.services.ranking_reader import (
    get_all,
    get_top,
    get_worst
)


router = APIRouter(
    prefix="/api/v1/ranking",
    tags=["ranking"]
)


@router.get("/today")
def today():

    return {
        "items": get_all()
    }


@router.get("/top")
def top(limit:int = 10):

    return {
        "items":
            get_top(limit)
    }



@router.get("/worst")
def worst(limit:int = 10):

    return {
        "items":
            get_worst(limit)
    }

