import json
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[2]


def find_report():
    candidates = [
        BASE_DIR / "reports" / "daily_ranking.json",
        BASE_DIR / "data" / "snapshots" / "daily_ranking.json",
        BASE_DIR / "reports" / "ranking.json",
    ]

    for path in candidates:
        if path.exists():
            return path

    return None


def load_ranking():
    path = find_report()

    if not path:
        return {
            "source": "offline",
            "as_of": None,
            "sane": False,
            "gap": 0,
            "top": [],
            "worst": [],
            "items": []
        }

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        data.setdefault("source", "report")
        data.setdefault("as_of", datetime.now().isoformat())
        data.setdefault("top", [])
        data.setdefault("worst", [])
        data.setdefault("items", [])

        return data

    except Exception as e:
        return {
            "source": "error",
            "error": str(e),
            "sane": False,
            "top": [],
            "worst": [],
            "items": []
        }


def get_top(limit=5):
    data = load_ranking()
    return data.get("top", [])[:limit]


def get_worst(limit=5):
    data = load_ranking()
    return data.get("worst", [])[:limit]


def get_summary():
    data = load_ranking()

    return {
        "source": data.get("source"),
        "as_of": data.get("as_of"),
        "sane": data.get("sane", False),
        "gap": data.get("gap", 0),
        "universe_size": len(data.get("items", [])),
        "top_count": len(data.get("top", [])),
        "worst_count": len(data.get("worst", []))
    }
