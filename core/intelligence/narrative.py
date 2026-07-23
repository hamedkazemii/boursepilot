from __future__ import annotations


def build_summary(data: dict) -> str:

    strengths = data.get("strengths", [])
    risks = data.get("risks", [])

    name = data.get("symbol")
    rank = data.get("rank")
    score = data.get("score")


    text = (
        f"صندوق {name} امروز رتبه {rank} "
        f"با امتیاز {score} را دارد. "
    )


    if strengths:
        text += (
            "نقاط قوت اصلی آن شامل "
            + "، ".join(strengths[:3])
            + " است. "
        )


    if risks:
        text += (
            "مهم‌ترین نکات احتیاطی "
            + "، ".join(risks[:3])
            + " است."
        )


    return text



def investment_view(data:dict)->str:

    risks=len(data.get("risks",[]))
    strengths=len(data.get("strengths",[]))


    if risks >= 3:
        return "فعلاً نیازمند احتیاط و بررسی بیشتر است."

    if strengths >=3 and risks==0:
        return "شرایط بنیادی و معاملاتی مناسبی دارد."

    return "برای تصمیم‌گیری نیازمند بررسی شرایط بازار است."
