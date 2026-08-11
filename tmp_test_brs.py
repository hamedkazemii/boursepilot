import sys
sys.path.insert(0, ".")
from services.providers.brs_client import BrsClient
from config import settings
client = BrsClient(api_key=settings.BRS_API_KEY, base_url=settings.BRS_BASE_URL)
data = client.get_json("Tsetmc/AllSymbols.php", {"type": 1})
print(f"Type: {type(data)}")
print(f"Length: {len(data) if data else None}")
print(f"First: {data[0] if data else None}")