import json

from services.tsetmc_client import TSETMCClient

INPUT = "data/fund_registry.json"


client = TSETMCClient()


def detect(info):

    text = " ".join([
        str(info.get("lVal18AFC","")),
        str(info.get("lVal30","")),
        str(info.get("faraDesc","")),
    ])


    if any(x in text for x in [
        "طلا",
        "زر",
        "گلد",
        "عیار",
        "ناب",
        "رزگلد"
    ]):
        return "طلا"


    if any(x in text for x in [
        "اهرم",
        "اهرمی"
    ]):
        return "اهرم"


    if any(x in text for x in [
        "ثابت",
        "درآمد"
    ]):
        return "درآمد ثابت"


    if any(x in text for x in [
        "سهام",
        "سهامی",
        "بخشی"
    ]):
        return "سهامی"


    return "UNKNOWN"



with open(
    INPUT,
    encoding="utf-8"
) as f:

    funds=json.load(f)



result=[]


for i,fund in enumerate(funds,1):

    print(
        i,
        "/",
        len(funds),
        fund["symbol"]
    )

    try:

        data=client.instrument(
            fund["ins_code"]
        )

        info=data["instrumentInfo"]


        if info.get("cgrValCotTitle") != "بازار صندوق های قابل معامله":
            continue


        fund["type"]=detect(info)

        fund["description"]=info.get(
            "faraDesc",
            ""
        )

        result.append(fund)


    except Exception as e:

        print(
            "ERROR",
            fund["symbol"],
            e
        )



with open(
    INPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=4
    )


print()
print("DONE")
print("COUNT:",len(result))
