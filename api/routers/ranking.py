from fastapi import APIRouter

router = APIRouter(
    tags=["ranking"]
)


@router.get("/today")
def today():
    return {
        "status": "ok",
        "message": "today ranking"
    }


@router.get("/top")
def top():
    return {
        "status": "ok",
        "message": "top funds"
    }


@router.get("/worst")
def worst():
    return {
        "status": "ok",
        "message": "worst funds"
    }
