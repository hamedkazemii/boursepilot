
from fastapi import APIRouter

from core.ai.advisor_engine import AdvisorEngine


router=APIRouter(
prefix="/ai",
tags=["ai"]
)



engine=AdvisorEngine()



@router.post("/advisor")

def advisor(data:dict):


    return engine.answer(

        data.get(
            "message",
            ""
        ),

        data.get(
            "context",
            {}
        )

    )

