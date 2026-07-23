import json
import time

from services.tsetmc_client import TSETMCClient

FILE = "data/fund_registry.json"

client = TSETMCClient()


with open(FILE, encoding="utf-8") as f:
    funds = json.load(f)


def is_fund(text):
    text = text.replace("‌", " ")

    keys = [
        "صندوق",
        "fund",
        "etf",
        "سرمایه گذاری",
        "سرمايه گذاري",
    ]

    return any(k in text.lower() for k in keys)


def classify(text):
    t = text.replace("‌", " ").lower()

    # ---------- GOLD ----------
    if (
        "طلا" in t
        or "پشتوانه طلا" in t
        or "کالای" in t
        or "كالاي" in t
    ):
        return "طلا"

    # ---------- LEVERAGED ----------
    if "اهرم" in t or "اهرمي" in t:
        return "اهرم"

    # ---------- FIXED INCOME ----------
    if (
        "درآمد ثابت" in t
        or "درآمدثابت" in t
        or "ثابت" in t
    ):
        return "درآمد ثابت"

    # ---------- MIXED ----------
    if "مختلط" in t:
        return "مختلط"

    # ---------- INDEX ----------
    if "شاخص" in t:
        return "شاخصی"

    # ---------- SECTOR ----------
    if (
        "بخشی" in t
        or "بخشي" in t
        or "صنایع" in t
        or "صنايع" in t
    ):
        return "بخشی"

    # ---------- STOCK ----------
    if (
        "سهامی" in t
        or "سهام" in t
    ):
        return "سهامی"

    return "UNKNOWN"


result = []

total = len(funds)

for i, fund in enumerate(funds, 1):

    print(f"{i} / {total}", fund["symbol"])

    try:

        data = client.instrument(fund["ins_code"])

        info = data["instrumentInfo"]

        text = " ".join(
            [
                info.get("faraDesc", ""),
                fund.get("name", ""),
                info.get("sector", {}).get("lSecVal", ""),
            ]
        )

        if not is_fund(text):
            continue

        fund["type"] = classify(text)

        fund["description"] = info.get("faraDesc", "")

        result.append(fund)

        time.sleep(0.15)

    except Exception as e:

        print("ERROR:", fund["symbol"], e)


with open(FILE, "w", encoding="utf-8") as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=4,
    )

print()
print("=" * 30)
print("FINISHED")
print("COUNT:", len(result))
