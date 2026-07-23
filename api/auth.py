
from datetime import datetime,timedelta
import jwt


SECRET="change-this-secret"


def create_token(user_id):

    payload={
        "sub":user_id,
        "exp":
        datetime.utcnow()
        +
        timedelta(days=7)
    }

    return jwt.encode(
        payload,
        SECRET,
        algorithm="HS256"
    )

