
from fastapi import APIRouter

router=APIRouter(
prefix="/me",
tags=["advisor"]
)


@router.post("/ask")
def ask(data:dict):

    question=data.get(
        "message",
        ""
    )


    return {

        "question":question,

        "answer":
        """
        مشاور صندوقچی:
        تحلیل بر اساس وضعیت بازار،
        رتبه صندوق‌ها و پروفایل ریسک
        انجام خواهد شد.
        """

    }

