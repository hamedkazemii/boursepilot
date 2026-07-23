from fastapi import APIRouter

from api.auth import create_token

router = APIRouter(
    tags=["auth"]
)


@router.post("/login")
def login():
    return {
        "token": create_token({"user":"demo"})
    }


@router.post("/telegram")
def telegram_login():
    return {
        "status":"telegram login"
    }
