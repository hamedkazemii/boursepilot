import requests
import string
import time


SEARCH_URL = (
    "https://old.tsetmc.com/tsev2/data/search.aspx"
)


PERSIAN_CHARS = [
    "ا","آ","ب","پ","ت","ث","ج","چ",
    "ح","خ","د","ذ","ر","ز","ژ",
    "س","ش","ص","ض","ط","ظ","ع",
    "غ","ف","ق","ک","ك","گ",
    "ل","م","ن","و","ه","ی","ي"
]


class FundDiscoveryV2:


    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent":
                "Mozilla/5.0"
            }
        )


    def search(self, key):

        r = self.session.get(
            SEARCH_URL,
            params={
                "skey": key
            },
            timeout=20
        )

        r.raise_for_status()

        return r.text



    def parse(self, text):

        result=[]

        rows=text.split(";")

        for row in rows:

            row=row.strip()

            if not row:
                continue


            parts=row.split(",")


            if len(parts)<5:
                continue


            result.append(
                {
                    "symbol":
                        parts[0].strip(),

                    "name":
                        parts[1].strip(),

                    "ins_code":
                        parts[2].strip()
                }
            )


        return result



    def discover(self):

        universe={}


        keys=[]


        # تک حرفی
        keys.extend(
            PERSIAN_CHARS
        )


        # ترکیب دو حرفی
        for a in PERSIAN_CHARS:

            for b in PERSIAN_CHARS:

                keys.append(
                    a+b
                )



        print(
            "Total queries:",
            len(keys)
        )



        for i,key in enumerate(keys,1):

            try:

                print(
                    i,
                    "/",
                    len(keys),
                    key
                )


                raw=self.search(key)


                items=self.parse(raw)


                for item in items:

                    universe[
                        item["ins_code"]
                    ]=item


                time.sleep(
                    0.1
                )


            except Exception as e:

                print(
                    "ERROR",
                    key,
                    e
                )



        return list(
            universe.values()
        )
