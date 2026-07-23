from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1",
    tags=["users"]
)


@router.get("/me")
def get_profile():
    return {
        "id": 1,
        "display_name": "Demo User",
        "risk_profile": "medium",
        "capital": 0,
        "status": "demo"
    }


@router.patch("/me")
def update_profile(data: dict):
    return {
        "success": True,
        "updated": data
    }


@router.get("/me/watchlist")
def watchlist():
    return {
        "items": []
    }


@router.post("/me/watchlist")
def add_watch(item: dict):
    return {
        "success": True,
        "item": item
    }


@router.get("/me/chat")
def chat_history():
    return {
        "messages": []
    }


@router.post("/me/ask")
def ask_ai(payload: dict):

    return {
        "answer":
        "مشاور صندوقچی آماده تحلیل تخصصی صندوق‌ها است.",
        "source": "advisor"
    }

