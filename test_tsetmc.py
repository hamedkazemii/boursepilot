import json
import requests

INS_CODE = "34074071043606558"

ENDPOINTS = {
    "اطلاعات نماد": f"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/{INS_CODE}",
    "اطلاعات قیمت": f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/{INS_CODE}",
    "بهترین سفارش‌ها": f"https://cdn.tsetmc.com/api/BestLimits/{INS_CODE}",
    "خرید/فروش حقیقی و حقوقی": f"https://cdn.tsetmc.com/api/ClientType/GetClientType/{INS_CODE}",
    "معاملات روز": f"https://cdn.tsetmc.com/api/Trade/GetTrade/{INS_CODE}",
}

headers = {
    "User-Agent": "Mozilla/5.0"
}

for title, url in ENDPOINTS.items():
    print("=" * 80)
    print(title)
    print(url)
    try:
        r = requests.get(url, headers=headers, timeout=15)
        print("HTTP:", r.status_code)

        if "application/json" in r.headers.get("content-type", ""):
            data = r.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
        else:
            print(r.text[:1000])

    except Exception as e:
        print("ERROR:", e)

    print()
