import json
import os


def save_report(data):

    os.makedirs(
        "reports",
        exist_ok=True
    )


    with open(
        "reports/recommendations.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=4
        )



    with open(
        "reports/recommendations.txt",
        "w",
        encoding="utf-8"
    ) as f:


        for x in data[:20]:

            f.write(
                f'{x["symbol"]} | '
                f'{x["type"]} | '
                f'{x["score"]} | '
                f'{x["decision"]}\n'
            )
