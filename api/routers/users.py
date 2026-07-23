from fastapi import APIRouter

router = APIRouter()


@router.get("/me")
def get_user():
    return {
        "user": None,
        "message": "user profile endpoint"
    }


@router.get("/me/watchlist")
def watchlist():
    return {
        "items": []
    }
