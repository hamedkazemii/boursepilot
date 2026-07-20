import json
import os
from datetime import datetime


class StorageService:


    def __init__(self):

        self.path = "data/history"


    def save(self, data):

        os.makedirs(
            self.path,
            exist_ok=True
        )


        filename = (
            datetime.now()
            .strftime("%Y-%m-%d")
            + ".json"
        )


        filepath = os.path.join(
            self.path,
            filename
        )


        history = []


        if os.path.exists(filepath):

            with open(
                filepath,
                "r",
                encoding="utf-8"
            ) as file:

                history = json.load(file)


        history.append(data)


        with open(
            filepath,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                ensure_ascii=False,
                indent=4
            )


        return filepath
