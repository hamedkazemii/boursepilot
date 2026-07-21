from services.brsapi.all_symbols import get_all

rows=get_all()

funds=[x for x in rows if "صندوق" in x.get("l30","")]

funds=sorted(
    funds,
    key=lambda x:x["tval"],
    reverse=True
)

print()
print("="*70)
print("          صندوق چی - گزارش صبحگاهی")
print("="*70)
print()

for f in funds[:15]:
    print(
        f'{f["l18"]:10}',
        f'{f["pcp"]:>6}%',
        f'{f["tval"]:,}'
    )

print()
