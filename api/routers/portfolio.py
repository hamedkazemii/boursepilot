from fastapi import APIRouter

router=APIRouter(prefix="/me/portfolio",tags=["portfolio"])


portfolio=[]


@router.get("")
def get_portfolio():

    return {
        "items":portfolio
    }



@router.post("")
def add_item(item:dict):

    portfolio.append(item)

    return {
        "status":"ok",
        "item":item
    }



@router.delete("/{symbol}")
def delete_item(symbol:str):

    global portfolio

    portfolio=[
        x for x in portfolio
        if x.get("symbol")!=symbol
    ]

    return {
        "status":"deleted"
    }

