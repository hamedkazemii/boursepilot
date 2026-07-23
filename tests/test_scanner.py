
from core.scanner import MarketScanner

scanner = MarketScanner()


results = scanner.scan()


print()

print("="*70)

print("📊 گزارش مقایسه‌ای صندوق‌ها")

print("="*70)


for item in results:


    print()

    print(
        "📌",
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
        "روند:",
        item["analysis"]["trend"]
    )


    print(
        "نتیجه:",
        item["analysis"]["summary"]
    )

