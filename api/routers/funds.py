from fastapi import APIRouter, HTTPException

from api.services.ranking_reader import find_symbol


router = APIRouter(
    prefix="/api/v1/funds",
    tags=["funds"]
)



@router.get("/{symbol}")
def fund(symbol:str):

    item = find_symbol(symbol)

    if not item:

        raise HTTPException(
            status_code=404,
            detail="Fund not found"
        )


    return {

        "fund":
            item,

        "explain_fa":
            "اطلاعات تحلیلی صندوق از موتور صندوقچی"

    }

