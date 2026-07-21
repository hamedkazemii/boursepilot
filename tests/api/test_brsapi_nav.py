import requests

API_KEY = "BaaCeH3hnZ8Shst9atGKzGZ2vLMDUBJA"

url = "https://Api.BrsApi.ir/Tsetmc/Nav.php"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Connection": "keep-alive",
}

params = {
    "key": API_KEY,
    "l18": "اهرم",
}

print("=" * 60)
print("BRS API TEST")
print("=" * 60)

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
)

print("Status:", response.status_code)
print("Headers:", response.headers)
print()
print(response.text)
