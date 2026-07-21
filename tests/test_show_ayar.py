from services.brsapi.all_symbols import BRSClient
import json

client = BRSClient()

code = "19040514831923530"

data = client.instrument(code)

print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )
)
