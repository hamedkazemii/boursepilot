
from services.analysis.fund_explainer import explain_fund


for s in ["یاقوت","اهرم","سیگلو"]:

    x=explain_fund(s)

    print("="*40)
    print("📊",x["symbol"])
    print("رتبه:",x["rank"])
    print("امتیاز:",x["score"])
    print(x["summary"])

    for f in x["factors"][:5]:
        print(
            "-",
            f["title"],
            ":",
            f["label"],
            f["score"]
        )

