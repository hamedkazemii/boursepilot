from fastapi import APIRouter
from api.services.report_reader import get_summary

router = APIRouter()


@router.get("/market/summary")
def market_summary():

    return get_summary()
