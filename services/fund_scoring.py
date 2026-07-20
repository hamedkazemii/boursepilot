import json


INPUT="data/fund_scores.json"
OUTPUT="data/fund_ranking.json"


data=json.load(
    open(
        INPUT,
        encoding="utf-8"
    )
)


result=[]


for f in data:


    score=0


    if f["type"]=="سهامی":
        score+=50


    if f["type"]=="طلا":
        score+=55


    if f["type"]=="اهرم":
        score+=40


    if f["type"]=="درآمد ثابت":
        score+=30


    if f["nav"]>0:
        score+=10


    f["score"]=score


    result.append(f)



result.sort(
    key=lambda x:x["score"],
    reverse=True
)



json.dump(
    result,
    open(
        OUTPUT,
        "w",
        encoding="utf-8"
    ),
    ensure_ascii=False,
    indent=4
)


print(
    "Ranking generated:",
    len(result)
)
