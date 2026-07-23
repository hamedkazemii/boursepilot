
from fastapi import APIRouter

router=APIRouter(
prefix="/admin",
tags=["admin"]
)


@router.post("/login")
def login(data:dict):

    return {
        "token":
        "admin-demo-token",
        "role":"admin"
    }



@router.get("/overview")
def overview():

    return {

        "universe_size":0,
        "last_run_at":None,
        "source":"offline",
        "sane":False,
        "gap":0,
        "users_count":0

    }



@router.post("/pipeline/run")
def run_pipeline(data:dict):

    return {

        "status":"queued",
        "type":
        data.get("type","analysis")

    }



@router.get("/ranking/preview")
def ranking_preview():

    return {

        "top":[],
        "worst":[]

    }



@router.post("/telegram/publish")
def publish(data:dict):

    return {

        "status":"dry-run",
        "type":
        data.get("type")

    }



@router.get("/config/scoring")
def scoring():

    return {

        "weights":{

            "liquidity":0.18,
            "momentum":0.16,
            "risk":0.20

        }

    }



@router.put("/config/scoring")
def update_scoring(data:dict):

    return {

        "status":"updated",
        "config":data

    }


