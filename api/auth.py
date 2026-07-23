from datetime import datetime, timedelta

import jwt
from fastapi import HTTPException, Header


SECRET_KEY = "CHANGE_ME_IN_ENV"

ALGORITHM = "HS256"



def create_token(
    user_id,
    role="user"
):

    payload = {

        "user_id": user_id,

        "role": role,

        "exp":
            datetime.utcnow()
            +
            timedelta(hours=24)

    }


    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )




def verify_token(
    token
):

    try:

        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[
                ALGORITHM
            ]
        )


    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )




def get_current_user(
    authorization: str | None = Header(None)
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )


    token = authorization.replace(
        "Bearer ",
        ""
    )


    return verify_token(token)




def require_admin(
    authorization: str | None = Header(None)
):

    user = get_current_user(
        authorization
    )


    if user.get("role") != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


    return user

