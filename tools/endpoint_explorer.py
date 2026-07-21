import json
import requests

BASE = "https://cdn.tsetmc.com/api"

INS_CODE = "34074071043606558"

ENDPOINTS = {
    "InstrumentInfo":
        f"{BASE}/Instrument/GetInstrumentInfo/{INS_CODE}",

    "ClosingPrice":
        f"{BASE}/ClosingPrice/GetClosingPriceInfo/{INS_CODE}",

    "BestLimits":
        f"{BASE}/BestLimits/{INS_CODE}",

    "Trade":
        f"{BASE}/Trade/GetTrade/{INS_CODE}",

    "ClosingPriceHistory":
        f"{BASE}/ClosingPrice/GetClosingPriceDailyList/{INS_CODE}/0",

    "MarketWatch":
        f"{BASE}/MarketWatch/GetMarketWatch",

    "InstrumentSearch":
        f"{BASE}/Instrument/GetInstrumentSearch/دارونو"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

print("=" * 80)
print("Sandoghchi Endpoint Explorer")
print("=" * 80)

for name, url in ENDPOINTS.items():

    print()
    print("=" * 80)
    print(name)
    print(url)

    try:

        r = requests.get(url, headers=HEADERS, timeout=15)

        print("Status:", r.status_code)

        if "application/json" in r.headers.get("content-type", ""):

            obj = r.json()

            print(json.dumps(obj, ensure_ascii=False, indent=2)[:2500])

        else:

            print(r.text[:800])

    except Exception as ex:

        print(ex)
