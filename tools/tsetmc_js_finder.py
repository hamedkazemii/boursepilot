import requests
import re


URL = "https://old.tsetmc.com/Loader.aspx?ParTree=15131F"


headers = {
    "User-Agent": "Mozilla/5.0"
}


print("=" * 70)
print("TSETMC JS Finder")
print("=" * 70)


r = requests.get(
    URL,
    headers=headers,
    timeout=20
)


print("Status:", r.status_code)
print("Length:", len(r.text))


scripts = re.findall(
    r'<script[^>]+src=["\'](.*?)["\']',
    r.text
)


print()
print("JavaScript Files:")
print("-"*70)


for s in scripts:

    print(s)
