import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright

OUTPUT = Path(
    "data/tsetmc_network_dump.json"
)


URL = (
    "https://old.tsetmc.com/Loader.aspx?ParTree=15131F"
)


requests = []


async def main():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=False
        )


        page = await browser.new_page()


        async def handle_response(response):

            url = response.url


            if (
                "api" in url.lower()
                or
                "ashx" in url.lower()
                or
                "json" in url.lower()
                or
                "tse" in url.lower()
            ):

                item = {

                    "url": url,

                    "status":
                    response.status

                }


                try:

                    item["text"] = (
                        await response.text()
                    )[:2000]


                except:

                    pass


                requests.append(item)


                print(
                    "\nFOUND:",
                    url
                )


        page.on(
            "response",
            handle_response
        )


        print(
            "OPENING TSETMC..."
        )


        await page.goto(
            URL,
            timeout=60000
        )


        await page.wait_for_timeout(
            10000
        )


        print()
        print(
            "================================"
        )
        print(
            "حالا دستی:"
        )
        print(
            "1- تنظیمات را باز کن"
        )
        print(
            "2- نوع -> صندوق سرمایه گذاری"
        )
        print(
            "3- تایید کن"
        )
        print(
            "4- 20 ثانیه صبر کن"
        )
        print(
            "================================"
        )


        await page.wait_for_timeout(
            60000
        )


        with open(
            OUTPUT,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                requests,
                f,
                ensure_ascii=False,
                indent=4
            )


        print()

        print(
            "Saved:",
            OUTPUT
        )

        print(
            "Requests:",
            len(requests)
        )


        await browser.close()



if __name__ == "__main__":

    asyncio.run(
        main()
    )
