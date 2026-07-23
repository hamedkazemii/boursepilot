from fastapi import APIRouter

router = APIRouter()


@router.get("/advisor")
def advisor_status():
    return {
        "status": "ready",
        "engine": "sandoghchi-ai"
    }
