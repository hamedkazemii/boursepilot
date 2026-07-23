from fastapi import APIRouter

router = APIRouter(
    tags=["admin-ai"]
)


@router.get("/status")
def status():

    return {
        "status":"active"
    }


@router.get("/lessons")
def lessons():

    return {
        "lessons":[]
    }
