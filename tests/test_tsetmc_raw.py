
import requests


url = (
    "https://www.tsetmc.com/Loader.aspx"
)


params = {

    "ParTree":
    "15131M"

}


response = requests.get(

    url,

    params=params,

    headers={

        "User-Agent":
        "Mozilla/5.0"

    },

    timeout=30

)


print()

print("="*70)

print("طول پاسخ:")

print(
    len(response.text)
)


print()

print("1000 کاراکتر اول:")

print(
    response.text[:1000]
)


