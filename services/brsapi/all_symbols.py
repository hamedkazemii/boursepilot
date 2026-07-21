import requests
from config.settings import *

HEADERS={
"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/138.0 Safari/537.36"
}

def get_all():
    r=requests.get(
        f"{BASE_URL}/AllSymbols.php",
        params={
            "key":BRS_API_KEY,
            "type":1
        },
        headers=HEADERS,
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()
