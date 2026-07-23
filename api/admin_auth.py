from datetime import datetime,timedelta
import jwt

ADMIN_SECRET="change-admin-secret"


def create_admin_token(username):

    payload={
        "sub":username,
        "role":"admin",
        "exp":
        datetime.utcnow()
        +
        timedelta(hours=8)
    }

    return jwt.encode(
        payload,
        ADMIN_SECRET,
        algorithm="HS256"
    )

