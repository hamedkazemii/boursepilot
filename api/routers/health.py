from fastapi import APIRouter
from api.services.database_reader import health_check
from api.services.report_reader import get_summary

router = APIRouter()


@router.get("/health")
def health():

    db = health_check()
    summary = get_summary()

    return {
        "status": "ok",
        "database": db,
        "analysis": summary
    }
