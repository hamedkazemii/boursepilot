

def generate(items):

    print()

    print("="*60)

    print("📊 گزارش صبحگاهی Sandoghchi")

    print("="*60)


    for i,item in enumerate(items,1):

        print()

        print(
            f"{i}) {item['name']}"
        )

        print(
            "امتیاز:",
            item["score"]
        )

        print(
            "وضعیت:",
            item["decision"]["status"]
        )

        print(
            "تصمیم:",
            item["decision"]["action"]
        )


        print(
            "دلایل:"
        )

        for r in item["reasons"]:

            print(
                "✓",
                r
            )


        print("-"*40)


