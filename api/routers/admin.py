from fastapi import APIRouter

router = APIRouter()


@router.post("/login")
def admin_login():
    return {
        "status": "ok",
        "message": "admin login endpoint"
    }


@router.get("/overview")
def admin_overview():
    return {
        "status": "ok",
        "overview": {}
    }


@router.post("/pipeline/run")
def run_pipeline():
    return {
        "status": "queued"
    }


@router.get("/ranking/preview")
def ranking_preview():
    return {
        "ranking": []
    }


@router.post("/telegram/publish")
def telegram_publish():
    return {
        "status": "queued"
    }


@router.get("/config/scoring")
def scoring_config():
    return {
        "weights": {}
    }
