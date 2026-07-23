from fastapi import APIRouter

from api.services.data_reader import db_status


router = APIRouter(
    prefix="/api/v1",
    tags=["health"]
)


@router.get("/health")
def health():

    return {

        "status": "ok",

        "database":
            db_status()

    }

