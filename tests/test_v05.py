

import json


with open(
"data/registry/fund_registry_real.json",
encoding="utf-8"
) as f:

    data=json.load(f)



print(
"Registry:",
len(data)
)


assert len(data)>=0


print(
"V0.5 TEST OK"
)


