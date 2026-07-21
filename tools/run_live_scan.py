

from services.live_scanner import LiveScanner


scanner = LiveScanner()


print()
print("="*60)
print("📡 دریافت اطلاعات لحظه‌ای صندوق‌ها")
print("="*60)


data = scanner.scan()


scanner.save(data)


print(
    "تعداد صندوق بررسی شده:",
    len(data)
)


for item in data[:10]:


    print()

    print(
        "صندوق:",
        item.get(
            "name"
        )
    )


    print(
        "قیمت:",
        item.get(
            "price"
        )
    )


    print(
        "حجم خرید:",
        item.get(
            "buy_volume"
        )
    )


    print(
        "وضعیت صف خرید:",
        item.get(
            "queue_buy"
        )
    )


print()
print(
    "ذخیره شد:"
    " data/live/market_snapshot.json"
)


