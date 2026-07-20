
from core.scanner import MarketScanner



scanner = MarketScanner()



results = scanner.scan()



print()

print("="*70)

print(
    "📊 نتیجه اسکن بازار"
)

print("="*70)



for item in results:


    print()

    print(
        "صندوق:",
        item["name"]
    )


    print(
        "نوع:",
        item["type"]
    )


    print(
        "صف:",
        item["analysis"]["queue"]
    )


    print(
        "تقاضا:",
        item["analysis"]["demand"]
    )


    print(
        "جمع‌بندی:",
        item["analysis"]["summary"]
    )

