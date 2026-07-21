

def calculate(data):


    score=50

    reasons=[]


    if data.get("queue_buy"):

        score+=20
        reasons.append(
            "صف خرید فعال است"
        )


    if data.get("pressure",0)>300:

        score+=15
        reasons.append(
            "قدرت تقاضا بالاست"
        )


    if data.get("change_percent",0)>0:

        score+=10
        reasons.append(
            "روند قیمت مثبت است"
        )


    if score>100:
        score=100


    return {

        "score":score,
        "reasons":reasons

    }


