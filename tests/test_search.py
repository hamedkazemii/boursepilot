from services.tsetmc_search import TSETMCSearch

client = TSETMCSearch()

print("=" * 60)
print("جستجوی نماد")
print("=" * 60)

results = client.search("دار")

for item in results:

    print()

    print("نماد :", item["symbol"])

    print("نام :", item["title"])

    print("InsCode :", item["ins_code"])
