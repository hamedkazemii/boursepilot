from fastapi import APIRouter


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"]
)


@router.get("/overview")
def overview():

    return {
        "universe_size": 0,
        "source": "unknown",
        "sane": False,
        "gap": 0,
        "users_count": 0
    }


@router.get("/pipeline/status")
def pipeline_status():

    return {
        "running": False,
        "last_run": None
    }


@router.post("/pipeline/run")
def pipeline_run(payload: dict):

    return {
        "accepted": True,
        "job": payload
    }


@router.get("/ranking/preview")
def ranking_preview():

    return {
        "top": [],
        "worst": [],
        "sane": False
    }


@router.post("/telegram/publish")
def telegram_publish(payload: dict):

    return {
        "success": True,
        "mode": payload
    }


