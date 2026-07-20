
import requests



urls = [

    "https://cdn.tsetmc.com/api/Instrument/GetInstrument",

    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentAll",

    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch",

    "https://cdn.tsetmc.com/api/Instrument/GetInstrumentByName",

]



for url in urls:


    print()

    print("="*70)

    print(url)


    try:


        r = requests.get(

            url,

            headers={

                "User-Agent":
                "Mozilla/5.0"

            },

            timeout=15

        )


        print(
            "Status:",
            r.status_code
        )


        print(
            "Length:",
            len(r.text)
        )


        print(
            r.text[:200]
        )


    except Exception as e:


        print(
            "ERROR:",
            e
        )


