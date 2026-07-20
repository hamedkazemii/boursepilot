import requests


urls = [

"https://old.tsetmc.com/Loader.aspx?ParTree=15131",

"https://old.tsetmc.com/tsev2/data/MarketWatchInit.aspx",

"https://cdn.tsetmc.com/api/Instrument/GetInstrumentInfo/123456789"

]


for url in urls:

    print("="*80)
    print(url)

    try:

        r=requests.get(
            url,
            timeout=20,
            headers={
                "User-Agent":"Mozilla/5.0"
            }
        )

        print("STATUS:",r.status_code)

        print(
            r.text[:500]
        )


    except Exception as e:

        print(
            "ERROR:",
            e
        )
