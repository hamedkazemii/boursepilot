from services.brsapi.all_symbols import get_all

data=get_all()

funds=[]

for x in data:
    if "صندوق" in x.get("l30",""):
        funds.append(x)

print("="*60)
print("Funds:",len(funds))
print("="*60)

for f in funds[:20]:
    print(
        f["l18"],
        f["pcp"],
        "%",
        f["tval"]
    )
