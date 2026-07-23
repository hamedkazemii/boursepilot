from __future__ import annotations

import json
from pathlib import Path

DB = Path("data/telegram_users.json")


def _load():
    if DB.exists():
        return json.loads(DB.read_text(encoding="utf-8"))
    return {}


def _save(data):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def register(chat_id, username="", first_name=""):
    data = _load()
    cid = str(chat_id)

    if cid not in data:
        data[cid] = {
            "chat_id": chat_id,
            "username": username,
            "first_name": first_name,
        }
        _save(data)

    return data[cid]


def all_users():
    return list(_load().values())
