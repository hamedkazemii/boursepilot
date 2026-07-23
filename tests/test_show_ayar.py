import json

from services.tsetmc_client import TSETMCClient

client = TSETMCClient()

code = "19040514831923530"

data = client.instrument(code)

print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )
)
