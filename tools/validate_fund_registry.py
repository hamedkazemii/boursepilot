import json

from services.tsetmc_client import TSETMCClient

FILE="data/fund_registry.json"


def is_real_fund(info):

    sector = (
        info
        .get("sector", {})
        .get("lSecVal","")
    )


    market = (
        info
        .get("cgrValCotTitle","")
    )


    desc = (
        info
        .get("faraDesc","")
    )


    if "صندوق سرمايه گذاري" in sector:
        return True


    if "صندوق" in market:
        return True


    if "نوع صندوق" in desc:
        return True


    return False



def main():

    client=TSETMCClient()


    with open(
        FILE,
        encoding="utf-8"
    ) as f:

        funds=json.load(f)



    valid=[]

    removed=[]



    for i,fund in enumerate(funds,1):

        print(
            i,
            fund["symbol"]
        )


        try:

            data=client.instrument(
                fund["ins_code"]
            )


            info=data["instrumentInfo"]


            if is_real_fund(info):

                valid.append(fund)

            else:

                removed.append(fund)



        except Exception:

            removed.append(fund)



    with open(
        FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            valid,
            f,
            ensure_ascii=False,
            indent=4
        )



    print()
    print("="*60)
    print("نتیجه")
    print("="*60)

    print("صندوق واقعی:",len(valid))
    print("حذف شده:",len(removed))


    print("\nحذف‌ها:")

    for x in removed:

        print(
            x["symbol"],
            x["name"]
        )



if __name__=="__main__":
    main()
