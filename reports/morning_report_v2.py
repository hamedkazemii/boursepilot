

from datetime import datetime



def generate(items):


    print()
    print("="*60)
    print("📊 گزارش صبحگاهی Sandoghchi")
    print("="*60)


    print(
        "تعداد صندوق بررسی شده:",
        len(items)
    )


    print()


    for i,x in enumerate(items,1):

        print(
            f"{i}- {x['symbol']}"
        )

        print(
            "امتیاز:",
            x.get("score")
        )

        print(
            "تصمیم:",
            x.get("decision")
        )

        print("-"*40)



    print()

    print(
        "زمان تولید:",
        datetime.now()
    )



