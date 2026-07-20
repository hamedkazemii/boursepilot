import json
from pathlib import Path
from datetime import datetime


class HistoryStorage:

    def __init__(self):
        self.file = Path("data/history/funds_history.json")

    def save(self, data: dict):
        history = self.load()

        data["saved_at"] = datetime.now().isoformat()

        history.append(data)

        self.file.write_text(
            json.dumps(
                history,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    def load(self):
        if not self.file.exists():
            return []

        return json.loads(
            self.file.read_text(encoding="utf-8")
        )
