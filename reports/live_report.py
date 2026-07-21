
from datetime import datetime


def generate(results):


    print()
    print("="*60)

    print("📊 گزارش صبحگاهی Sandoghchi")

    print("="*60)


    print()

    print(
        "تعداد صندوق بررسی شده:",
        len(results)
    )


    ranked=sorted(
        results,
        key=lambda x:
        x["analysis"].get(
            "pressure",
            0
        ),
        reverse=True
    )


    print()

    for i,item in enumerate(ranked[:10],1):

        print(
            f"{i}- {item['symbol']}"
        )

        print(
            "وضعیت:",
            item["analysis"]
        )

        print("-"*40)



    print()

    print(
        "زمان تولید:",
        datetime.now()
    )
