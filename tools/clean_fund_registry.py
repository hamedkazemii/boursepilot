import json


FILE = "data/fund_registry.json"


def is_invalid(f):

    symbol = f.get("symbol","")
    name = f.get("name","")


    bad_prefix = [

        "ضدار",
        "طدار",
        "ضهرم",
        "طهرم",
        "زعف",
        "ذرت",
        "پست",
    ]


    for x in bad_prefix:

        if symbol.startswith(x):

            return True



    if symbol.endswith("ح"):

        return True



    keywords = [

        "اختیار",
        "اوراق",
        "گواهی",
        "حق تقدم"

    ]


    text = symbol + name


    for k in keywords:

        if k in text:

            return True



    return False



def main():


    with open(
        FILE,
        encoding="utf-8"
    ) as f:

        funds=json.load(f)



    before=len(funds)


    cleaned=[]

    removed=[]


    for f in funds:

        if is_invalid(f):

            removed.append(f)

        else:

            cleaned.append(f)



    with open(
        FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cleaned,
            f,
            ensure_ascii=False,
            indent=4
        )



    print("="*60)
    print("پاکسازی Registry")
    print("="*60)

    print(
        "قبل:",
        before
    )

    print(
        "بعد:",
        len(cleaned)
    )

    print(
        "حذف شده:",
        len(removed)
    )


    print("\nنمونه حذف‌ها:")

    for x in removed[:20]:

        print(
            x["symbol"],
            "-",
            x["name"]
        )


if __name__=="__main__":
    main()
