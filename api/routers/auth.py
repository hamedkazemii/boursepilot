from fastapi import APIRouter

from api.auth import create_token


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"]
)



@router.post("/login")
def login(data:dict):

    username = data.get(
        "username"
    )

    password = data.get(
        "password"
    )


    # MVP authentication
    # بعدا از DB و password hash استفاده می‌شود

    if username=="admin" and password=="admin":

        token=create_token(
            user_id=1,
            role="admin"
        )


        return {
            "access_token":token,
            "role":"admin"
        }



    token=create_token(
        user_id=2,
        role="user"
    )


    return {

        "access_token":token,

        "role":"user"

    }




@router.post("/telegram")
def telegram_login(
    payload:dict
):

    return {

        "message":
        "Telegram login endpoint ready",

        "status":
        "pending verification"

    }

