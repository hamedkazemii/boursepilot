
from fastapi import APIRouter


router=APIRouter(
prefix="/admin/ai",
tags=["admin-ai"]
)



@router.get("/status")

def status():

    return {

        "provider":"configured",

        "memory":"enabled"

    }



@router.get("/lessons")

def lessons():

    return {

        "items":[]

    }


